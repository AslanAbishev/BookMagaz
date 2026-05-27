"""
Build and sample the neural/NLP recommender artifacts.

Usage:
    venv\\Scripts\\python.exe scripts\\build_neural_recommender.py

The script rebuilds:
- NLP book text embeddings;
- trainable user/book latent embeddings;
- a small sample of recommendations and preference analysis.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from neural_recommend import (  # noqa: E402
    analyze_user_preferences,
    build_neural_recommender,
    get_neural_model_card,
    get_neural_recommendations,
)


def main() -> int:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    database_name = os.getenv("MONGO_DB", "goodbooks")
    sample_user = os.getenv("SAMPLE_USER_ID", "u-1")
    epochs = int(os.getenv("NEURAL_EPOCHS", "20"))
    max_events = int(os.getenv("NEURAL_MAX_EVENTS", "5000"))
    batch_size = int(os.getenv("NEURAL_BATCH_SIZE", "2048"))

    client = MongoClient(mongo_uri)
    db = client[database_name]

    print(
        f"Building neural recommender: database={database_name}, "
        f"epochs={epochs}, max_events={max_events}, batch_size={batch_size}",
        flush=True,
    )
    summary = build_neural_recommender(
        db,
        force_rebuild=True,
        epochs=epochs,
        max_training_events=max_events,
        batch_size=batch_size,
    )
    model_card = get_neural_model_card(db, epochs=epochs, max_training_events=max_events, batch_size=batch_size)
    preferences = analyze_user_preferences(sample_user, db)
    recommendations = get_neural_recommendations(sample_user, db, limit=5)

    print("Neural recommender artifacts rebuilt")
    print(json.dumps(summary, indent=2))
    print("\nModel card")
    print(json.dumps(model_card, indent=2, default=str))
    print("\nSample preference profile")
    print(json.dumps(preferences, indent=2, default=str))
    print("\nSample recommendations")
    print(json.dumps(recommendations, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
