"""
Smoke-check that Flask/runtime artifacts use the latest neural model.

Usage:
    venv\\Scripts\\python.exe scripts\\check_neural_runtime.py 1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from pymongo import MongoClient  # noqa: E402
from neural_recommend import get_neural_recommendations, get_neural_status  # noqa: E402


def main() -> int:
    user_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    db = MongoClient("mongodb://localhost:27017/")["goodbooks"]

    status = get_neural_status(db)
    recs = get_neural_recommendations(user_id, db, limit=3, include_model_info=True)

    print("Neural runtime status")
    print(json.dumps(status, indent=2, default=str))
    print(f"\nTop recommendations for user_id={user_id}")
    print(json.dumps(recs, indent=2, default=str))

    has_neural_signal = any(item["score_components"]["user_item_embedding"] > 0 for item in recs)
    if not has_neural_signal:
        print("\nWARNING: recommendations are falling back without user-item neural signal.")
        print("Use a trained dataset user id, for example /api/neural/recommend/1?limit=10&debug=1")
        return 1

    print("\nOK: recommendations include non-zero neural user-item embedding scores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
