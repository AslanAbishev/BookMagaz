"""
Train the GoodBooks neural recommender with PyTorch/CUDA when available.

This script is optional. The application can still use the NumPy trainer, but
this version is better for full-scale training because it uses mini-batches,
Adam, and GPU acceleration through PyTorch.

Usage:
    $env:NEURAL_EPOCHS="10"
    $env:NEURAL_MAX_EVENTS="500000"
    $env:NEURAL_BATCH_SIZE="8192"
    venv\\Scripts\\python.exe scripts\\train_neural_recommender_torch.py
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from neural_recommend import (  # noqa: E402
    BOOK_EMBEDDINGS_FILE,
    LATENT_DIM,
    RANDOM_SEED,
    USER_ITEM_MODEL_FILE,
    VALIDATION_RATIO,
    build_book_text_embeddings,
    get_neural_model_card,
)


def _load_torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as exc:
        raise SystemExit(
            "PyTorch is not installed in this venv. Install a CUDA build first, for example:\n"
            "venv\\Scripts\\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu128"
        ) from exc
    return torch, nn, DataLoader, TensorDataset


def _rating_to_unit(value):
    rating = float(value)
    return min(1.0, max(0.0, (rating - 1.0) / 4.0))


def _load_rating_events(db, max_events):
    cursor = db.interactions.find(
        {"rating": {"$ne": None}},
        {"_id": 0, "user_id": 1, "book_id": 1, "rating": 1},
    )
    if max_events and max_events > 0:
        cursor = cursor.limit(max_events)

    events = []
    for row in cursor:
        if row.get("user_id") is None or row.get("book_id") is None:
            continue
        try:
            events.append((str(row["user_id"]), int(row["book_id"]), _rating_to_unit(row["rating"])))
        except (TypeError, ValueError):
            continue
    return events


def _metrics(preds, targets):
    errors = targets - preds
    return {
        "rmse": round(float(np.sqrt(np.mean(errors**2))), 4),
        "mae": round(float(np.mean(np.abs(errors))), 4),
    }


def _ranking_metrics(
    model,
    validation_rows,
    train_rows,
    items_count,
    device,
    torch,
    k=10,
    users_limit=1000,
    negatives_per_positive=99,
    seed=RANDOM_SEED,
):
    """Evaluate top-k ranking with sampled negatives.

    For each validation positive, the model ranks the held-out item against
    random unseen items. This is a standard practical approximation for
    recommender evaluation when scoring every item for every user is expensive.
    """
    positives_by_user = {}
    train_items_by_user = {}
    for user_pos, item_pos, _rating in train_rows.astype(np.int64):
        train_items_by_user.setdefault(int(user_pos), set()).add(int(item_pos))

    for user_pos, item_pos, rating in validation_rows:
        if rating < 0.75:
            continue
        positives_by_user.setdefault(int(user_pos), []).append(int(item_pos))

    rng = np.random.default_rng(seed)
    users = list(positives_by_user.keys())
    if users_limit and len(users) > users_limit:
        users = list(rng.choice(users, size=users_limit, replace=False))

    if not users:
        return {
            "precision_at_10": 0.0,
            "recall_at_10": 0.0,
            "hit_rate_at_10": 0.0,
            "ndcg_at_10": 0.0,
            "evaluated_users": 0,
            "negatives_per_positive": negatives_per_positive,
        }

    precision_values = []
    recall_values = []
    hit_values = []
    ndcg_values = []
    all_items = np.arange(items_count)

    model.eval()
    with torch.no_grad():
        for user_pos in users:
            positives = positives_by_user[user_pos]
            positive = int(rng.choice(positives))
            blocked = set(train_items_by_user.get(user_pos, set()))
            blocked.update(positives)
            candidates_pool = np.setdiff1d(all_items, np.fromiter(blocked, dtype=np.int64), assume_unique=False)
            if len(candidates_pool) == 0:
                continue

            sample_size = min(negatives_per_positive, len(candidates_pool))
            negatives = rng.choice(candidates_pool, size=sample_size, replace=False)
            candidates = np.concatenate([[positive], negatives])
            users_tensor = torch.full((len(candidates),), user_pos, dtype=torch.long, device=device)
            items_tensor = torch.as_tensor(candidates, dtype=torch.long, device=device)
            scores = model(users_tensor, items_tensor).detach().cpu().numpy()
            ranked = candidates[np.argsort(-scores)]
            top_k = ranked[:k]

            hit = int(positive in top_k)
            hit_values.append(hit)
            precision_values.append(hit / k)
            recall_values.append(hit)
            if hit:
                rank = int(np.where(ranked == positive)[0][0]) + 1
                ndcg_values.append(1.0 / np.log2(rank + 1))
            else:
                ndcg_values.append(0.0)

    return {
        "precision_at_10": round(float(np.mean(precision_values)) if precision_values else 0.0, 4),
        "recall_at_10": round(float(np.mean(recall_values)) if recall_values else 0.0, 4),
        "hit_rate_at_10": round(float(np.mean(hit_values)) if hit_values else 0.0, 4),
        "ndcg_at_10": round(float(np.mean(ndcg_values)) if ndcg_values else 0.0, 4),
        "evaluated_users": len(hit_values),
        "negatives_per_positive": negatives_per_positive,
    }


def main() -> int:
    torch, nn, DataLoader, TensorDataset = _load_torch()

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    database_name = os.getenv("MONGO_DB", "goodbooks")
    epochs = int(os.getenv("NEURAL_EPOCHS", "10"))
    max_events = int(os.getenv("NEURAL_MAX_EVENTS", "500000"))
    batch_size = int(os.getenv("NEURAL_BATCH_SIZE", "8192"))
    hidden_dim = int(os.getenv("NEURAL_HIDDEN_DIM", "64"))
    latent_dim = int(os.getenv("NEURAL_LATENT_DIM", str(LATENT_DIM)))
    learning_rate = float(os.getenv("NEURAL_LR", "0.001"))
    ranking_users_limit = int(os.getenv("NEURAL_RANKING_USERS", "1000"))
    ranking_negatives = int(os.getenv("NEURAL_RANKING_NEGATIVES", "99"))

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"PyTorch device: {device}", flush=True)
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)

    client = MongoClient(mongo_uri)
    db = client[database_name]

    print("Building NLP book embeddings...", flush=True)
    text_model = build_book_text_embeddings(db, force_rebuild=True)
    print(f"Book embeddings: {len(text_model.get('book_ids', []))} saved to {BOOK_EMBEDDINGS_FILE}", flush=True)

    print(f"Loading rating events: max_events={max_events}", flush=True)
    events = _load_rating_events(db, max_events)
    if not events:
        raise SystemExit("No rating events found. Add ratings/interactions before training.")

    user_ids = sorted({row[0] for row in events})
    book_ids = sorted({row[1] for row in events})
    user_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
    item_index = {book_id: idx for idx, book_id in enumerate(book_ids)}

    rows = np.asarray(
        [(user_index[user_id], item_index[book_id], rating) for user_id, book_id, rating in events],
        dtype=np.float32,
    )
    rng = np.random.default_rng(RANDOM_SEED)
    order = rng.permutation(len(rows))
    validation_size = max(1, int(len(rows) * VALIDATION_RATIO)) if len(rows) >= 5 else len(rows)
    validation_rows = rows[order[:validation_size]]
    train_rows = rows[order[validation_size:]] if len(rows) >= 5 else rows

    train_dataset = TensorDataset(
        torch.as_tensor(train_rows[:, 0], dtype=torch.long),
        torch.as_tensor(train_rows[:, 1], dtype=torch.long),
        torch.as_tensor(train_rows[:, 2], dtype=torch.float32),
    )
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    class NeuralCollaborativeFiltering(nn.Module):
        def __init__(self, users_count, items_count):
            super().__init__()
            self.user_embedding = nn.Embedding(users_count, latent_dim)
            self.item_embedding = nn.Embedding(items_count, latent_dim)
            self.user_bias = nn.Embedding(users_count, 1)
            self.item_bias = nn.Embedding(items_count, 1)
            self.hidden = nn.Linear(latent_dim * 2, hidden_dim)
            self.output = nn.Linear(hidden_dim, 1)
            self.global_mean = float(np.mean(train_rows[:, 2]))

            nn.init.normal_(self.user_embedding.weight, mean=0.0, std=0.08)
            nn.init.normal_(self.item_embedding.weight, mean=0.0, std=0.08)
            nn.init.zeros_(self.user_bias.weight)
            nn.init.zeros_(self.item_bias.weight)

        def forward(self, users, items):
            user_vec = self.user_embedding(users)
            item_vec = self.item_embedding(items)
            x = torch.cat([user_vec, item_vec], dim=1)
            hidden = torch.tanh(self.hidden(x))
            score = (
                self.global_mean
                + self.user_bias(users).squeeze(1)
                + self.item_bias(items).squeeze(1)
                + self.output(hidden).squeeze(1)
            )
            return score

    model = NeuralCollaborativeFiltering(len(user_ids), len(book_ids)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.MSELoss()
    history = []

    print(
        f"Training NCF: events={len(events)}, train={len(train_rows)}, validation={len(validation_rows)}, "
        f"epochs={epochs}, batch_size={batch_size}, latent_dim={latent_dim}, hidden_dim={hidden_dim}",
        flush=True,
    )

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        total_count = 0
        for users, items, targets in train_loader:
            users = users.to(device)
            items = items.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            preds = model(users, items)
            loss = loss_fn(preds, targets)
            loss.backward()
            optimizer.step()

            total_loss += float(loss.item()) * len(targets)
            total_count += len(targets)

        train_mse = total_loss / max(1, total_count)
        history.append({"epoch": epoch + 1, "train_mse": round(train_mse, 6)})
        print(f"epoch={epoch + 1}/{epochs} train_mse={train_mse:.6f}", flush=True)

    def predict(rows_subset):
        model.eval()
        preds_all = []
        with torch.no_grad():
            for start in range(0, len(rows_subset), batch_size):
                batch = rows_subset[start:start + batch_size]
                users = torch.as_tensor(batch[:, 0], dtype=torch.long, device=device)
                items = torch.as_tensor(batch[:, 1], dtype=torch.long, device=device)
                preds_all.append(model(users, items).detach().cpu().numpy())
        return np.concatenate(preds_all)

    train_preds = predict(train_rows)
    validation_preds = predict(validation_rows)
    train_metrics = _metrics(train_preds, train_rows[:, 2])
    validation_metrics = _metrics(validation_preds, validation_rows[:, 2])
    ranking_metrics = _ranking_metrics(
        model,
        validation_rows,
        train_rows,
        len(book_ids),
        device,
        torch,
        users_limit=ranking_users_limit,
        negatives_per_positive=ranking_negatives,
    )

    cpu_model = model.cpu()
    payload = {
        "user_ids": user_ids,
        "book_ids": book_ids,
        "user_factors": cpu_model.user_embedding.weight.detach().numpy(),
        "item_factors": cpu_model.item_embedding.weight.detach().numpy(),
        "user_bias": cpu_model.user_bias.weight.detach().numpy().reshape(-1),
        "item_bias": cpu_model.item_bias.weight.detach().numpy().reshape(-1),
        "hidden_weights": cpu_model.hidden.weight.detach().numpy().T,
        "hidden_bias": cpu_model.hidden.bias.detach().numpy(),
        "output_weights": cpu_model.output.weight.detach().numpy().reshape(-1),
        "output_bias": float(cpu_model.output.bias.detach().numpy()[0]),
        "global_mean": float(cpu_model.global_mean),
        "model_type": "neural_collaborative_filtering_pytorch",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_run_id": f"torch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "device": str(device),
        "embedding_dim": latent_dim,
        "hidden_dim": hidden_dim,
        "epochs": epochs,
        "batch_size": batch_size,
        "max_training_events": max_events,
        "learning_rate": learning_rate,
        "training_events": len(train_rows),
        "validation_events": len(validation_rows),
        "validation_strategy": "deterministic_holdout",
        "training_history": history,
        "final_train_mse": history[-1]["train_mse"] if history else 0.0,
        "train_rmse": train_metrics["rmse"],
        "train_mae": train_metrics["mae"],
        "validation_rmse": validation_metrics["rmse"],
        "validation_mae": validation_metrics["mae"],
        "ranking_metrics": ranking_metrics,
    }

    Path(USER_ITEM_MODEL_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(USER_ITEM_MODEL_FILE, "wb") as handle:
        pickle.dump(payload, handle)

    print(f"Saved neural model to {USER_ITEM_MODEL_FILE}", flush=True)
    print(json.dumps(get_neural_model_card(db), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
