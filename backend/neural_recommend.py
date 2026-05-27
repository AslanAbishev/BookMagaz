"""
Neural/NLP hybrid recommender for the GoodBooks application.

The existing recommender is a classic item-item collaborative filter. This
module adds a neural-network-course oriented layer:
- trainable user/book latent embeddings from explicit ratings;
- a small Neural Collaborative Filtering scoring layer;
- NLP text embeddings from book metadata;
- a hybrid ranking score with human-readable recommendation reasons;
- preference analysis for categories, authors, and keywords.

The implementation intentionally uses NumPy and scikit-learn only, because
those packages are already part of the project stack and keep the assignment
easy to run on a student laptop.
"""
from __future__ import annotations

import math
import os
import pickle
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


BOOK_EMBEDDINGS_FILE = "data/neural_book_embeddings.pkl"
USER_ITEM_MODEL_FILE = "data/neural_user_item_model.pkl"

TEXT_EMBEDDING_DIM = 64
LATENT_DIM = 24
DEFAULT_EPOCHS = 20
DEFAULT_HIDDEN_DIM = 24
DEFAULT_BATCH_SIZE = 2048
DEFAULT_MAX_TRAINING_EVENTS = 5000
RANDOM_SEED = 42
VALIDATION_RATIO = 0.2

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "with", "book", "novel", "story",
}

INTEREST_TAG_KEYWORDS = {
    "science_fiction": {
        "alien", "apes", "clarke", "cyberpunk", "dune", "empire", "future",
        "galactic", "planet", "robot", "robots", "sci", "science", "space",
        "star", "thrawn", "wars", "worlds",
    },
    "space_opera": {
        "academy", "empire", "force", "galactic", "heir", "jedi", "odyssey",
        "search", "space", "star", "thrawn", "wars",
    },
    "robot_ai": {
        "android", "artificial", "intelligence", "machine", "robot", "robots",
    },
    "alien_worlds": {
        "alien", "aliens", "apes", "creature", "planet", "world", "worlds",
    },
    "horror": {
        "blood", "bloodcurdling", "dark", "ghost", "horror", "king", "lovecraft",
        "macabre", "monster", "night", "shining", "stephen", "terror", "vampire",
    },
    "crime_thriller": {
        "crime", "darkly", "detective", "dexter", "killer", "murder", "murderer",
        "mystery", "psychological", "serial", "suspense", "thriller",
    },
    "dark_fiction": {
        "dark", "death", "dreaming", "macabre", "murderer", "perfume", "strange",
        "tales", "twisted",
    },
    "fantasy": {
        "dragon", "fantasy", "magic", "magical", "potter", "wizard",
    },
}


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _load_pickle(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "rb") as handle:
            return pickle.load(handle)
    except (EOFError, pickle.PickleError, OSError):
        return default


def _save_pickle(path: str, payload: Any) -> None:
    _ensure_parent(path)
    with open(path, "wb") as handle:
        pickle.dump(payload, handle)


def _model_file_info(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {"exists": False, "path": path}

    stat = os.stat(path)
    return {
        "exists": True,
        "path": path,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _book_id(value: Any) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _rating_to_unit(value: Any) -> float:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, (rating - 1.0) / 4.0))


def _interaction_weight(interaction: dict[str, Any]) -> float:
    if interaction.get("rating") is not None:
        return max(0.15, _rating_to_unit(interaction.get("rating")))

    kind = interaction.get("interaction")
    if kind == "purchase":
        return 0.95
    if kind == "like":
        return 0.85
    if kind == "view":
        return 0.35
    return 0.25


def _book_text(book: dict[str, Any]) -> str:
    parts = [
        book.get("title", ""),
        book.get("authors", ""),
        book.get("category", ""),
        book.get("description", ""),
    ]
    text = " ".join(str(part) for part in parts if part)
    return text.strip() or f"book {book.get('book_id', '')}"


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z]{3,}", text.lower())
        if token not in STOP_WORDS
    ]


def _interest_tags_for_text(text: str) -> set[str]:
    tokens = set(_tokens(text))
    return {
        tag
        for tag, keywords in INTEREST_TAG_KEYWORDS.items()
        if tokens & keywords
    }


def _public_book(book: dict[str, Any], score: float, reason: str, components: dict[str, float]) -> dict[str, Any]:
    return {
        "book_id": _book_id(book.get("book_id")),
        "title": book.get("title", ""),
        "authors": book.get("authors", ""),
        "category": book.get("category", ""),
        "average_rating": book.get("average_rating"),
        "price": book.get("price", 0),
        "image_url": book.get("image_url", ""),
        "neural_score": round(float(score), 4),
        "reason": reason,
        "score_components": {key: round(float(value), 4) for key, value in components.items()},
    }


def _recommendation_model_info(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_type": model.get("model_type"),
        "trained_at": model.get("trained_at"),
        "training_run_id": model.get("training_run_id"),
        "device": model.get("device", "cpu"),
        "training_events": model.get("training_events", 0),
        "validation_events": model.get("validation_events", 0),
        "validation_rmse": model.get("validation_rmse", 0.0),
        "validation_mae": model.get("validation_mae", 0.0),
        "ranking_metrics": model.get("ranking_metrics", {}),
        "artifact": _model_file_info(USER_ITEM_MODEL_FILE),
    }


def _all_books(db: Any) -> list[dict[str, Any]]:
    return list(db.books.find())


def _all_rating_events(db: Any, limit: int | None = None) -> list[dict[str, Any]]:
    events = []
    cursor = db.interactions.find({"rating": {"$ne": None}})
    if limit and limit > 0:
        cursor = cursor.limit(limit)

    for row in cursor:
        if row.get("book_id") is None or row.get("user_id") is None:
            continue
        try:
            float(row.get("rating"))
        except (TypeError, ValueError):
            continue
        events.append(row)
    return events


def _user_interactions(db: Any, user_id: str) -> list[dict[str, Any]]:
    user_id_text = str(user_id)
    try:
        user_id_number = int(user_id_text)
    except (TypeError, ValueError):
        return list(db.interactions.find({"user_id": user_id_text}))

    return list(db.interactions.find({"$or": [{"user_id": user_id_text}, {"user_id": user_id_number}]}))


def _predict_from_arrays(
    user_pos: int,
    item_pos: int,
    global_mean: float,
    user_factors: np.ndarray,
    item_factors: np.ndarray,
    user_bias: np.ndarray,
    item_bias: np.ndarray,
    hidden_weights: np.ndarray,
    hidden_bias: np.ndarray,
    output_weights: np.ndarray,
    output_bias: float,
) -> float:
    user_vec = user_factors[user_pos]
    item_vec = item_factors[item_pos]
    x = np.concatenate([user_vec, item_vec])
    hidden = np.tanh(x @ hidden_weights + hidden_bias)
    learned_score = float(hidden @ output_weights + output_bias)
    return float(global_mean + user_bias[user_pos] + item_bias[item_pos] + learned_score)


def _regression_metrics(rows: list[tuple[int, int, float]], model: dict[str, Any], batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, float]:
    if not rows:
        return {"rmse": 0.0, "mae": 0.0}

    user_pos = np.asarray([row[0] for row in rows], dtype=np.int64)
    item_pos = np.asarray([row[1] for row in rows], dtype=np.int64)
    targets = np.asarray([row[2] for row in rows], dtype=np.float64)
    errors = []

    for start in range(0, len(targets), batch_size):
        end = start + batch_size
        users = user_pos[start:end]
        items = item_pos[start:end]
        x = np.concatenate([model["user_factors"][users], model["item_factors"][items]], axis=1)
        hidden = np.tanh(x @ model["hidden_weights"] + model["hidden_bias"])
        preds = (
            float(model.get("global_mean", 0.5))
            + model["user_bias"][users]
            + model["item_bias"][items]
            + hidden @ model["output_weights"]
            + float(model.get("output_bias", 0.0))
        )
        errors.append(targets[start:end] - preds)

    errors_array = np.concatenate(errors)
    return {
        "rmse": round(float(np.sqrt(np.mean(errors_array**2))), 4),
        "mae": round(float(np.mean(np.abs(errors_array))), 4),
    }


def build_book_text_embeddings(db: Any, force_rebuild: bool = False) -> dict[str, Any]:
    """Build NLP embeddings from book title, author, category, and description."""
    cached = _load_pickle(BOOK_EMBEDDINGS_FILE, None)
    if cached is not None and not force_rebuild:
        return cached

    books = _all_books(db)
    book_ids = [_book_id(book.get("book_id")) for book in books]
    texts = [_book_text(book) for book in books]

    if not books:
        payload = {"book_ids": [], "embeddings": np.empty((0, 0)), "method": "empty"}
        _save_pickle(BOOK_EMBEDDINGS_FILE, payload)
        return payload

    try:
        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words="english")
        tfidf = vectorizer.fit_transform(texts)
    except ValueError:
        identity_dim = min(len(books), TEXT_EMBEDDING_DIM)
        embeddings = np.eye(len(books), identity_dim)
        payload = {"book_ids": book_ids, "embeddings": embeddings, "method": "identity_fallback"}
        _save_pickle(BOOK_EMBEDDINGS_FILE, payload)
        return payload

    max_dim = min(TEXT_EMBEDDING_DIM, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
    if max_dim >= 2:
        svd = TruncatedSVD(n_components=max_dim, random_state=RANDOM_SEED)
        embeddings = svd.fit_transform(tfidf)
        method = f"tfidf_svd_{max_dim}"
    else:
        embeddings = tfidf.toarray()
        method = "tfidf_dense"

    embeddings = normalize(embeddings)
    payload = {"book_ids": book_ids, "embeddings": embeddings, "method": method}
    _save_pickle(BOOK_EMBEDDINGS_FILE, payload)
    return payload


def build_user_item_embedding_model(
    db: Any,
    force_rebuild: bool = False,
    latent_dim: int = LATENT_DIM,
    hidden_dim: int = DEFAULT_HIDDEN_DIM,
    epochs: int = DEFAULT_EPOCHS,
    max_training_events: int = DEFAULT_MAX_TRAINING_EVENTS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    learning_rate: float = 0.035,
    regularization: float = 0.01,
) -> dict[str, Any]:
    """Train a small Neural Collaborative Filtering model using SGD.

    This is the deep-learning part of the project: users and books are
    represented by trainable dense vectors, then a small hidden layer learns a
    non-linear affinity score for each user-book pair.
    """
    cached = _load_pickle(USER_ITEM_MODEL_FILE, None)
    if cached is not None and not force_rebuild:
        return cached

    events = _all_rating_events(db, limit=max_training_events)
    if not events:
        payload = {
            "user_ids": [],
            "book_ids": [],
            "user_factors": np.empty((0, latent_dim)),
            "item_factors": np.empty((0, latent_dim)),
            "user_bias": np.empty(0),
            "item_bias": np.empty(0),
            "hidden_weights": np.empty((latent_dim * 2, hidden_dim)),
            "hidden_bias": np.empty(hidden_dim),
            "output_weights": np.empty(hidden_dim),
            "output_bias": 0.0,
            "global_mean": 0.5,
            "model_type": "neural_collaborative_filtering",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_run_id": "empty-model",
            "embedding_dim": latent_dim,
            "hidden_dim": hidden_dim,
            "epochs": epochs,
            "max_training_events": max_training_events,
            "batch_size": batch_size,
            "training_events": 0,
            "validation_events": 0,
            "training_history": [],
            "validation_rmse": 0.0,
            "validation_mae": 0.0,
        }
        _save_pickle(USER_ITEM_MODEL_FILE, payload)
        return payload

    user_ids = sorted({str(event["user_id"]) for event in events})
    book_ids = sorted({_book_id(event["book_id"]) for event in events})
    user_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
    item_index = {book_id: idx for idx, book_id in enumerate(book_ids)}

    training = [
        (user_index[str(event["user_id"])], item_index[_book_id(event["book_id"])], _rating_to_unit(event["rating"]))
        for event in events
    ]

    rng = np.random.default_rng(RANDOM_SEED)
    shuffled = list(rng.permutation(len(training)))
    if len(training) >= 5:
        validation_size = max(1, int(len(training) * VALIDATION_RATIO))
        validation_rows = [training[index] for index in shuffled[:validation_size]]
        train_rows = [training[index] for index in shuffled[validation_size:]]
        validation_strategy = "deterministic_holdout"
    else:
        train_rows = training
        validation_rows = training
        validation_strategy = "training_reuse_small_dataset"

    user_factors = rng.normal(0, 0.08, size=(len(user_ids), latent_dim))
    item_factors = rng.normal(0, 0.08, size=(len(book_ids), latent_dim))
    user_bias = np.zeros(len(user_ids))
    item_bias = np.zeros(len(book_ids))
    hidden_weights = rng.normal(0, 0.08, size=(latent_dim * 2, hidden_dim))
    hidden_bias = np.zeros(hidden_dim)
    output_weights = rng.normal(0, 0.08, size=hidden_dim)
    output_bias = 0.0
    global_mean = float(np.mean([row[2] for row in train_rows]))
    training_history = []

    train_users = np.asarray([row[0] for row in train_rows], dtype=np.int64)
    train_items = np.asarray([row[1] for row in train_rows], dtype=np.int64)
    train_targets = np.asarray([row[2] for row in train_rows], dtype=np.float64)

    for epoch in range(epochs):
        squared_error_sum = 0.0
        seen_count = 0
        order = rng.permutation(len(train_targets))
        for start in range(0, len(train_targets), batch_size):
            batch_idx = order[start:start + batch_size]
            users = train_users[batch_idx]
            items = train_items[batch_idx]
            targets = train_targets[batch_idx]

            user_vecs = user_factors[users].copy()
            item_vecs = item_factors[items].copy()
            x = np.concatenate([user_vecs, item_vecs], axis=1)
            hidden = np.tanh(x @ hidden_weights + hidden_bias)
            preds = global_mean + user_bias[users] + item_bias[items] + hidden @ output_weights + output_bias
            errors = targets - preds

            squared_error_sum += float(np.sum(errors**2))
            seen_count += len(targets)

            old_hidden_weights = hidden_weights.copy()
            old_output_weights = output_weights.copy()
            scale = 1.0 / max(1, len(targets))

            output_weights += learning_rate * (hidden.T @ errors * scale - regularization * output_weights)
            output_bias += learning_rate * float(np.mean(errors))

            hidden_grad = errors[:, None] * old_output_weights * (1.0 - hidden**2)
            hidden_weights += learning_rate * (x.T @ hidden_grad * scale - regularization * hidden_weights)
            hidden_bias += learning_rate * np.mean(hidden_grad, axis=0)

            x_grad = hidden_grad @ old_hidden_weights.T
            user_update = learning_rate * (x_grad[:, :latent_dim] * scale - regularization * user_vecs * scale)
            item_update = learning_rate * (x_grad[:, latent_dim:] * scale - regularization * item_vecs * scale)

            np.add.at(user_factors, users, user_update)
            np.add.at(item_factors, items, item_update)
            np.add.at(user_bias, users, learning_rate * (errors * scale - regularization * user_bias[users] * scale))
            np.add.at(item_bias, items, learning_rate * (errors * scale - regularization * item_bias[items] * scale))

        training_history.append(
            {
                "epoch": epoch + 1,
                "train_mse": round(squared_error_sum / max(1, seen_count), 6),
            }
        )

    payload = {
        "user_ids": user_ids,
        "book_ids": book_ids,
        "user_factors": user_factors,
        "item_factors": item_factors,
        "user_bias": user_bias,
        "item_bias": item_bias,
        "hidden_weights": hidden_weights,
        "hidden_bias": hidden_bias,
        "output_weights": output_weights,
        "output_bias": output_bias,
        "global_mean": global_mean,
        "model_type": "neural_collaborative_filtering",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_run_id": f"numpy-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "embedding_dim": latent_dim,
        "hidden_dim": hidden_dim,
        "epochs": epochs,
        "max_training_events": max_training_events,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "regularization": regularization,
        "training_events": len(train_rows),
        "validation_events": len(validation_rows),
        "validation_strategy": validation_strategy,
        "training_history": training_history,
    }
    train_metrics = _regression_metrics(train_rows, payload)
    validation_metrics = _regression_metrics(validation_rows, payload)
    payload["final_train_mse"] = training_history[-1]["train_mse"] if training_history else 0.0
    payload["train_rmse"] = train_metrics["rmse"]
    payload["train_mae"] = train_metrics["mae"]
    payload["validation_rmse"] = validation_metrics["rmse"]
    payload["validation_mae"] = validation_metrics["mae"]
    _save_pickle(USER_ITEM_MODEL_FILE, payload)
    return payload


def build_neural_recommender(
    db: Any,
    force_rebuild: bool = False,
    epochs: int = DEFAULT_EPOCHS,
    max_training_events: int = DEFAULT_MAX_TRAINING_EVENTS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Build all artifacts required by the neural hybrid recommender."""
    text_model = build_book_text_embeddings(db, force_rebuild=force_rebuild)
    user_item_model = build_user_item_embedding_model(
        db,
        force_rebuild=force_rebuild,
        epochs=epochs,
        max_training_events=max_training_events,
        batch_size=batch_size,
    )
    return {
        "text_embedding_method": text_model.get("method"),
        "book_embeddings": len(text_model.get("book_ids", [])),
        "model_type": user_item_model.get("model_type", "neural_collaborative_filtering"),
        "trained_at": user_item_model.get("trained_at"),
        "training_run_id": user_item_model.get("training_run_id"),
        "device": user_item_model.get("device", "cpu"),
        "embedding_dim": user_item_model.get("embedding_dim", LATENT_DIM),
        "hidden_dim": user_item_model.get("hidden_dim", DEFAULT_HIDDEN_DIM),
        "epochs": user_item_model.get("epochs", 0),
        "max_training_events": user_item_model.get("max_training_events", max_training_events),
        "batch_size": user_item_model.get("batch_size", batch_size),
        "latent_users": len(user_item_model.get("user_ids", [])),
        "latent_books": len(user_item_model.get("book_ids", [])),
        "training_events": user_item_model.get("training_events", 0),
        "validation_events": user_item_model.get("validation_events", 0),
        "validation_rmse": user_item_model.get("validation_rmse", 0.0),
        "validation_mae": user_item_model.get("validation_mae", 0.0),
        "artifact": _model_file_info(USER_ITEM_MODEL_FILE),
    }


def get_neural_model_card(
    db: Any,
    force_rebuild: bool = False,
    epochs: int = DEFAULT_EPOCHS,
    max_training_events: int = DEFAULT_MAX_TRAINING_EVENTS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Return a JSON-safe model card for defense and reporting."""
    summary = build_neural_recommender(
        db,
        force_rebuild=force_rebuild,
        epochs=epochs,
        max_training_events=max_training_events,
        batch_size=batch_size,
    )
    model = build_user_item_embedding_model(db, force_rebuild=False)
    history = model.get("training_history", [])

    return {
        "project_topic": "Recommendation System",
        "course_alignment": ["embeddings", "deep learning", "NLP"],
        "architecture": {
            "model_type": summary["model_type"],
            "trained_at": summary["trained_at"],
            "training_run_id": summary["training_run_id"],
            "device": summary["device"],
            "input_signals": ["ratings", "likes", "purchases", "views", "book metadata"],
            "user_embedding_dim": summary["embedding_dim"],
            "book_embedding_dim": summary["embedding_dim"],
            "hidden_layer_units": summary["hidden_dim"],
            "nlp_embedding_method": summary["text_embedding_method"],
            "hybrid_score": "0.55 * neural_affinity + 0.35 * nlp_similarity + 0.10 * popularity_prior",
        },
        "artifact": summary["artifact"],
        "training": {
            "epochs": summary["epochs"],
            "max_training_events": summary["max_training_events"],
            "batch_size": summary["batch_size"],
            "training_events": summary["training_events"],
            "validation_events": summary["validation_events"],
            "validation_strategy": model.get("validation_strategy"),
            "final_train_mse": model.get("final_train_mse", 0.0),
            "train_rmse": model.get("train_rmse", 0.0),
            "train_mae": model.get("train_mae", 0.0),
            "validation_rmse": summary["validation_rmse"],
            "validation_mae": summary["validation_mae"],
            "loss_curve": history,
            "ranking_metrics": model.get("ranking_metrics", {}),
        },
        "capabilities": [
            "personalized recommendations",
            "preference analysis",
            "explainable recommendation reasons",
            "cold-start fallback",
        ],
    }


def get_neural_status(db: Any) -> dict[str, Any]:
    """Return runtime status proving which neural artifacts the app loads."""
    model = build_user_item_embedding_model(db, force_rebuild=False)
    text_model = build_book_text_embeddings(db, force_rebuild=False)
    return {
        "status": "ready" if model.get("training_events", 0) > 0 else "cold_start_only",
        "model": _recommendation_model_info(model),
        "text_embeddings": {
            "method": text_model.get("method"),
            "book_embeddings": len(text_model.get("book_ids", [])),
            "artifact": _model_file_info(BOOK_EMBEDDINGS_FILE),
        },
    }


def _keyword_counts(books: list[dict[str, Any]], weights: dict[Any, float]) -> Counter:
    counts: Counter = Counter()
    for book in books:
        weight = weights.get(_book_id(book.get("book_id")), 0.0)
        if weight <= 0:
            continue
        for token in _tokens(_book_text(book)):
            counts[token] += weight
    return counts


def analyze_user_preferences(user_id: str, db: Any, limit: int = 5) -> dict[str, Any]:
    """Summarize a user's preferences from ratings, likes, purchases, and views."""
    interactions = _user_interactions(db, user_id)
    weights: defaultdict[Any, float] = defaultdict(float)
    for interaction in interactions:
        if interaction.get("book_id") is not None:
            weights[_book_id(interaction["book_id"])] += _interaction_weight(interaction)

    if not weights:
        return {
            "user_id": str(user_id),
            "signals_count": 0,
            "top_categories": [],
            "top_authors": [],
            "top_keywords": [],
            "top_interest_tags": [],
            "summary": "No preference signals yet; recommendations use popularity and content priors.",
        }

    books = [book for book in _all_books(db) if _book_id(book.get("book_id")) in weights]
    categories: Counter = Counter()
    authors: Counter = Counter()
    interest_tags: Counter = Counter()

    for book in books:
        weight = weights[_book_id(book.get("book_id"))]
        if book.get("category"):
            categories[str(book["category"])] += weight
        if book.get("authors"):
            authors[str(book["authors"])] += weight
        for tag in _interest_tags_for_text(_book_text(book)):
            interest_tags[tag] += weight

    keywords = _keyword_counts(books, weights)
    top_categories = [{"name": name, "weight": round(float(score), 3)} for name, score in categories.most_common(limit)]
    top_authors = [{"name": name, "weight": round(float(score), 3)} for name, score in authors.most_common(limit)]
    top_keywords = [{"name": name, "weight": round(float(score), 3)} for name, score in keywords.most_common(limit)]
    top_interest_tags = [{"name": name, "weight": round(float(score), 3)} for name, score in interest_tags.most_common(limit)]

    lead = top_categories[0]["name"] if top_categories else "mixed genres"
    return {
        "user_id": str(user_id),
        "signals_count": len(interactions),
        "top_categories": top_categories,
        "top_authors": top_authors,
        "top_keywords": top_keywords,
        "top_interest_tags": top_interest_tags,
        "summary": f"Preference profile is mainly driven by {lead} and {len(weights)} interacted books.",
    }


def _content_profile_vector(interactions: list[dict[str, Any]], text_model: dict[str, Any]) -> np.ndarray | None:
    book_ids = text_model.get("book_ids", [])
    embeddings = text_model.get("embeddings", np.empty((0, 0)))
    if len(book_ids) == 0 or getattr(embeddings, "size", 0) == 0:
        return None

    id_to_pos = {book_id: idx for idx, book_id in enumerate(book_ids)}
    vectors = []
    weights = []
    for interaction in interactions:
        book_id = _book_id(interaction.get("book_id"))
        if book_id in id_to_pos:
            vectors.append(embeddings[id_to_pos[book_id]])
            weights.append(_interaction_weight(interaction))

    if not vectors:
        return None

    profile = np.average(np.asarray(vectors), axis=0, weights=np.asarray(weights))
    norm = np.linalg.norm(profile)
    if norm == 0 or math.isnan(norm):
        return None
    return profile / norm


def _neural_affinity(user_id: str, book_id: Any, model: dict[str, Any]) -> float:
    user_ids = model.get("user_ids", [])
    book_ids = model.get("book_ids", [])
    if str(user_id) not in user_ids or book_id not in book_ids:
        return 0.0

    user_pos = user_ids.index(str(user_id))
    item_pos = book_ids.index(book_id)
    user_vec = model["user_factors"][user_pos]
    item_vec = model["item_factors"][item_pos]

    if "hidden_weights" in model:
        pred = _predict_from_arrays(
            user_pos,
            item_pos,
            float(model.get("global_mean", 0.5)),
            model["user_factors"],
            model["item_factors"],
            model["user_bias"],
            model["item_bias"],
            model["hidden_weights"],
            model["hidden_bias"],
            model["output_weights"],
            float(model.get("output_bias", 0.0)),
        )
    else:
        learned_score = float(np.dot(user_vec, item_vec))
        pred = float(model.get("global_mean", 0.5)) + float(model["user_bias"][user_pos]) + float(model["item_bias"][item_pos]) + learned_score
    return min(1.0, max(0.0, pred))


def _content_similarity(book_id: Any, profile_vector: np.ndarray | None, text_model: dict[str, Any]) -> float:
    if profile_vector is None:
        return 0.0

    book_ids = text_model.get("book_ids", [])
    if book_id not in book_ids:
        return 0.0

    embeddings = text_model.get("embeddings", np.empty((0, 0)))
    candidate = embeddings[book_ids.index(book_id)]
    score = float(np.dot(profile_vector, candidate))
    return min(1.0, max(0.0, score))


def _popularity_score(book: dict[str, Any]) -> float:
    try:
        rating = float(book.get("average_rating", 0))
    except (TypeError, ValueError):
        rating = 0.0
    return min(1.0, max(0.0, rating / 5.0))


def _preference_match_score(book: dict[str, Any], preferences: dict[str, Any]) -> float:
    text = _book_text(book).lower()
    candidate_tokens = set(_tokens(text))
    candidate_tags = _interest_tags_for_text(text)
    score = 0.0

    preferred_authors = [item["name"].lower() for item in preferences.get("top_authors", [])]
    book_authors = str(book.get("authors", "")).lower()
    if any(author and (author in book_authors or book_authors in author) for author in preferred_authors):
        score = max(score, 0.75)

    preferred_categories = {item["name"] for item in preferences.get("top_categories", [])}
    if book.get("category") in preferred_categories:
        score = max(score, 0.65)

    preferred_tags = {item["name"] for item in preferences.get("top_interest_tags", [])}
    if preferred_tags and candidate_tags:
        overlap = len(preferred_tags & candidate_tags)
        score = max(score, min(0.85, 0.45 + 0.20 * overlap))

    preferred_keywords = {item["name"].lower() for item in preferences.get("top_keywords", [])}
    keyword_overlap = len(preferred_keywords & candidate_tokens)
    if keyword_overlap:
        score = max(score, min(0.75, 0.25 + 0.15 * keyword_overlap))

    return min(1.0, max(0.0, score))


def _reason(book: dict[str, Any], preferences: dict[str, Any], content_score: float, neural_score: float, preference_score: float) -> str:
    preferred_categories = {item["name"] for item in preferences.get("top_categories", [])}
    preferred_authors = {item["name"] for item in preferences.get("top_authors", [])}
    preferred_tags = {item["name"] for item in preferences.get("top_interest_tags", [])}
    candidate_tags = _interest_tags_for_text(_book_text(book))

    if preferred_tags and candidate_tags and preference_score >= 0.45:
        tags = ", ".join(sorted(preferred_tags & candidate_tags))
        if book.get("authors") in preferred_authors:
            return f"Matches your {tags} interest and an author you liked"
        return f"Matches your inferred interest tags: {tags}"
    if book.get("authors") in preferred_authors:
        return f"Same author as books you liked: {book.get('authors')}"
    if book.get("category") in preferred_categories:
        return f"Matches your strongest category signal: {book.get('category')}"
    if neural_score >= 0.55:
        return "High latent user-book embedding affinity"
    if content_score >= 0.35:
        return "NLP metadata embedding is close to your reading profile"
    return "Popular fallback with acceptable quality prior"


def _primary_author(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return text.split(",")[0].strip()


def _diversify_ranked(ranked: list[dict[str, Any]], limit: int, max_per_author: int = 3) -> list[dict[str, Any]]:
    """Keep recommendations relevant while avoiding one-author domination."""
    selected = []
    author_counts: Counter = Counter()

    for item in ranked:
        author = _primary_author(item.get("authors"))
        if author and author_counts[author] >= max_per_author:
            continue
        selected.append(item)
        if author:
            author_counts[author] += 1
        if len(selected) == limit:
            return selected

    seen = {item.get("book_id") for item in selected}
    for item in ranked:
        if item.get("book_id") not in seen:
            selected.append(item)
        if len(selected) == limit:
            break

    return selected


def get_neural_recommendations(
    user_id: str,
    db: Any,
    limit: int = 10,
    force_rebuild: bool = False,
    include_model_info: bool = False,
) -> list[dict[str, Any]]:
    """Return personalized hybrid neural/NLP recommendations for a user."""
    text_model = build_book_text_embeddings(db, force_rebuild=force_rebuild)
    embedding_model = build_user_item_embedding_model(db, force_rebuild=force_rebuild)
    interactions = _user_interactions(db, user_id)
    preferences = analyze_user_preferences(user_id, db)
    profile_vector = _content_profile_vector(interactions, text_model)
    has_trained_user_embedding = str(user_id) in embedding_model.get("user_ids", [])

    seen = {_book_id(interaction.get("book_id")) for interaction in interactions if interaction.get("book_id") is not None}
    candidates = [book for book in _all_books(db) if _book_id(book.get("book_id")) not in seen]

    ranked = []
    for book in candidates:
        book_id = _book_id(book.get("book_id"))
        neural_score = _neural_affinity(user_id, book_id, embedding_model)
        content_score = _content_similarity(book_id, profile_vector, text_model)
        preference_score = _preference_match_score(book, preferences)
        popularity = _popularity_score(book)

        if interactions and has_trained_user_embedding:
            total = 0.50 * neural_score + 0.25 * content_score + 0.15 * preference_score + 0.10 * popularity
        elif interactions:
            total = 0.65 * content_score + 0.25 * preference_score + 0.10 * popularity
        else:
            total = 0.75 * popularity + 0.25 * content_score

        components = {
            "user_item_embedding": neural_score,
            "nlp_content_embedding": content_score,
            "preference_match": preference_score,
            "popularity_prior": popularity,
        }
        ranked.append(_public_book(book, total, _reason(book, preferences, content_score, neural_score, preference_score), components))

    ranked.sort(key=lambda row: row["neural_score"], reverse=True)
    if interactions:
        results = _diversify_ranked(ranked, limit=limit, max_per_author=3)
    else:
        results = ranked[:limit]
    if include_model_info:
        model_info = _recommendation_model_info(embedding_model)
        for row in results:
            row["model_info"] = model_info
    return results
