from types import SimpleNamespace
from pathlib import Path

import neural_recommend
from tests.helpers import CollectionStub

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _sample_db():
    books = CollectionStub(
        [
            {
                "book_id": 1,
                "title": "Deep Learning with Python",
                "authors": "Francois Chollet",
                "category": "AI",
                "description": "Neural networks, embeddings, and deep learning practice.",
                "average_rating": 4.8,
            },
            {
                "book_id": 2,
                "title": "Neural Recommender Systems",
                "authors": "Jane Data",
                "category": "AI",
                "description": "Personalized recommendation with user and item embeddings.",
                "average_rating": 4.7,
            },
            {
                "book_id": 3,
                "title": "Medieval History",
                "authors": "Arthur Stone",
                "category": "History",
                "description": "Castles, kingdoms, and medieval political systems.",
                "average_rating": 4.2,
            },
        ]
    )
    interactions = CollectionStub(
        [
            {"user_id": "u-1", "book_id": 1, "interaction": "rating", "rating": 5.0},
            {"user_id": "u-2", "book_id": 1, "interaction": "rating", "rating": 4.0},
            {"user_id": "u-2", "book_id": 2, "interaction": "rating", "rating": 5.0},
            {"user_id": "u-3", "book_id": 3, "interaction": "rating", "rating": 5.0},
        ]
    )
    return SimpleNamespace(books=books, interactions=interactions)


def _use_test_models(monkeypatch):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(neural_recommend, "BOOK_EMBEDDINGS_FILE", str(DATA_DIR / "test_neural_book_embeddings.pkl"))
    monkeypatch.setattr(neural_recommend, "USER_ITEM_MODEL_FILE", str(DATA_DIR / "test_neural_user_item_model.pkl"))


def test_build_book_text_embeddings_creates_vectors(monkeypatch):
    _use_test_models(monkeypatch)
    model = neural_recommend.build_book_text_embeddings(_sample_db(), force_rebuild=True)

    assert model["book_ids"] == [1, 2, 3]
    assert model["embeddings"].shape[0] == 3
    assert model["method"].startswith(("tfidf", "identity"))


def test_build_user_item_embedding_model_trains_latent_vectors(monkeypatch):
    _use_test_models(monkeypatch)
    model = neural_recommend.build_user_item_embedding_model(_sample_db(), force_rebuild=True, epochs=10)

    assert model["training_events"] == 4
    assert model["user_factors"].shape[0] == 3
    assert model["item_factors"].shape[0] == 3
    assert model["hidden_weights"].shape[0] == model["user_factors"].shape[1] * 2
    assert model["model_type"] == "neural_collaborative_filtering"
    assert model["training_history"]
    assert "validation_rmse" in model


def test_neural_recommendations_rank_content_and_exclude_seen(monkeypatch):
    _use_test_models(monkeypatch)
    recs = neural_recommend.get_neural_recommendations("u-1", _sample_db(), limit=2, force_rebuild=True)

    assert recs
    assert recs[0]["book_id"] == 2
    assert recs[0]["book_id"] != 1
    assert "score_components" in recs[0]
    assert "nlp_content_embedding" in recs[0]["score_components"]


def test_preference_analysis_returns_categories_authors_and_keywords(monkeypatch):
    _use_test_models(monkeypatch)
    profile = neural_recommend.analyze_user_preferences("u-1", _sample_db())

    assert profile["signals_count"] == 1
    assert profile["top_categories"][0]["name"] == "AI"
    assert profile["top_authors"][0]["name"] == "Francois Chollet"
    assert profile["top_keywords"]


def test_cold_start_neural_recommendations_use_popularity(monkeypatch):
    _use_test_models(monkeypatch)
    recs = neural_recommend.get_neural_recommendations("new-user", _sample_db(), limit=2, force_rebuild=True)

    assert [book["book_id"] for book in recs] == [1, 2]
    assert recs[0]["reason"] == "Popular fallback with acceptable quality prior"


def test_model_card_exposes_architecture_training_and_alignment(monkeypatch):
    _use_test_models(monkeypatch)
    card = neural_recommend.get_neural_model_card(_sample_db(), force_rebuild=True)

    assert card["project_topic"] == "Recommendation System"
    assert "embeddings" in card["course_alignment"]
    assert card["architecture"]["model_type"] == "neural_collaborative_filtering"
    assert card["training"]["epochs"] > 0
    assert "validation_rmse" in card["training"]
    assert "ranking_metrics" in card["training"]
    assert "artifact" in card


def test_preference_analysis_matches_numeric_dataset_user_ids(monkeypatch):
    _use_test_models(monkeypatch)
    db = SimpleNamespace(
        books=CollectionStub(
            [
                {
                    "book_id": 10,
                    "title": "Graph Neural Networks",
                    "authors": "Data Author",
                    "category": "AI",
                    "description": "Embeddings and neural networks.",
                    "average_rating": 4.5,
                }
            ]
        ),
        interactions=CollectionStub(
            [{"user_id": 12874, "book_id": 10, "interaction": "rating", "rating": 5.0}]
        ),
    )

    profile = neural_recommend.analyze_user_preferences("12874", db)

    assert profile["signals_count"] == 1
    assert profile["top_categories"][0]["name"] == "AI"


def test_recommendations_can_include_model_debug_info(monkeypatch):
    _use_test_models(monkeypatch)
    recs = neural_recommend.get_neural_recommendations(
        "u-1",
        _sample_db(),
        limit=1,
        force_rebuild=True,
        include_model_info=True,
    )

    assert "model_info" in recs[0]
    assert recs[0]["model_info"]["model_type"] == "neural_collaborative_filtering"


def test_neural_status_reports_loaded_artifacts(monkeypatch):
    _use_test_models(monkeypatch)
    status = neural_recommend.get_neural_status(_sample_db())

    assert status["status"] == "ready"
    assert status["model"]["artifact"]["exists"] is True
    assert status["text_embeddings"]["book_embeddings"] == 3


def test_new_user_horror_preferences_use_content_cold_start(monkeypatch):
    _use_test_models(monkeypatch)
    db = SimpleNamespace(
        books=CollectionStub(
            [
                {
                    "book_id": 1,
                    "title": "The Shining",
                    "authors": "Stephen King",
                    "category": "",
                    "description": "horror hotel terror",
                    "average_rating": 4.4,
                },
                {
                    "book_id": 2,
                    "title": "The Best of H.P. Lovecraft: Bloodcurdling Tales of Horror and the Macabre",
                    "authors": "H.P. Lovecraft",
                    "category": "",
                    "description": "horror macabre strange tales",
                    "average_rating": 4.2,
                },
                {
                    "book_id": 3,
                    "title": "It",
                    "authors": "Stephen King",
                    "category": "",
                    "description": "horror monster terror",
                    "average_rating": 4.3,
                },
                {
                    "book_id": 4,
                    "title": "Romantic Summer",
                    "authors": "Sunny Writer",
                    "category": "",
                    "description": "romance beach vacation",
                    "average_rating": 4.9,
                },
            ]
        ),
        interactions=CollectionStub(
            [
                {"user_id": "new-horror-user", "book_id": 1, "interaction": "purchase", "rating": None},
                {"user_id": "new-horror-user", "book_id": 2, "interaction": "rating", "rating": 5.0},
            ]
        ),
    )

    recs = neural_recommend.get_neural_recommendations("new-horror-user", db, limit=2, force_rebuild=True)

    assert recs[0]["book_id"] == 3
    assert recs[0]["score_components"]["preference_match"] > 0
    assert recs[0]["neural_score"] > recs[1]["neural_score"]


def test_new_user_scifi_profile_gets_tag_matches_and_author_diversity(monkeypatch):
    _use_test_models(monkeypatch)
    db = SimpleNamespace(
        books=CollectionStub(
            [
                {"book_id": 1, "title": "I, Robot", "authors": "Isaac Asimov", "description": "robot science fiction", "average_rating": 4.2},
                {"book_id": 2, "title": "2001: A Space Odyssey", "authors": "Arthur C. Clarke", "description": "space science fiction", "average_rating": 4.1},
                {"book_id": 3, "title": "Jedi Search", "authors": "Kevin J. Anderson", "description": "star wars jedi academy", "average_rating": 3.8},
                {"book_id": 4, "title": "Foundation", "authors": "Isaac Asimov", "description": "galactic empire science fiction", "average_rating": 4.4},
                {"book_id": 5, "title": "Foundation and Empire", "authors": "Isaac Asimov", "description": "galactic empire science fiction", "average_rating": 4.3},
                {"book_id": 6, "title": "Robots and Empire", "authors": "Isaac Asimov", "description": "robots galactic empire", "average_rating": 4.2},
                {"book_id": 7, "title": "Dune", "authors": "Frank Herbert", "description": "planet space empire science fiction", "average_rating": 4.5},
                {"book_id": 8, "title": "Childhood's End", "authors": "Arthur C. Clarke", "description": "alien worlds science fiction", "average_rating": 4.0},
                {"book_id": 9, "title": "Beach Romance", "authors": "Sunny Writer", "description": "romance beach summer", "average_rating": 5.0},
            ]
        ),
        interactions=CollectionStub(
            [
                {"user_id": "new-scifi-user", "book_id": 1, "interaction": "purchase", "rating": None},
                {"user_id": "new-scifi-user", "book_id": 2, "interaction": "purchase", "rating": None},
                {"user_id": "new-scifi-user", "book_id": 3, "interaction": "purchase", "rating": None},
            ]
        ),
    )

    recs = neural_recommend.get_neural_recommendations("new-scifi-user", db, limit=5, force_rebuild=True)
    authors = [rec["authors"] for rec in recs]

    assert recs[0]["score_components"]["preference_match"] > 0
    assert "interest" in recs[0]["reason"]
    assert authors.count("Isaac Asimov") <= 3
    assert any(rec["authors"] == "Frank Herbert" for rec in recs)
