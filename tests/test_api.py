"""
P2 - High: API endpoint tests
"""
from datetime import datetime
from types import SimpleNamespace

from bson import ObjectId

import app as app_module
from tests.helpers import CollectionStub


class TestSearchAPI:
    """Search API tests."""

    def test_search_returns_200(self, client):
        """Search API returns 200."""
        rv = client.get("/api/search?q=book&limit=10")
        assert rv.status_code == 200

    def test_search_returns_json_array(self, client):
        """Search returns JSON array of books."""
        rv = client.get("/api/search?q=book&limit=5")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)

    def test_search_empty_query(self, client):
        """Search with empty query returns books or empty list."""
        rv = client.get("/api/search?q=&limit=5")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)

    def test_search_passes_blank_category_as_none(self, client, monkeypatch):
        """Blank category filters are normalized before model lookup."""
        captured = {}

        def fake_search_books(db, text, category=None, limit=30):
            captured["text"] = text
            captured["category"] = category
            captured["limit"] = limit
            return []

        monkeypatch.setattr(app_module, "search_books", fake_search_books)

        rv = client.get("/api/search?q=clean%20code&category=%20%20&limit=7")

        assert rv.status_code == 200
        assert captured == {"text": "clean code", "category": None, "limit": 7}

    def test_search_returns_500_when_backend_search_fails(self, client, monkeypatch):
        """Search reports backend failures instead of crashing the route."""
        monkeypatch.setattr(app_module, "search_books", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("search backend failed")))

        rv = client.get("/api/search?q=python")

        assert rv.status_code == 500
        assert rv.get_json()["error"] == "search backend failed"


class TestRateAPI:
    """Rating API tests - requires authentication."""

    def test_rate_without_auth_returns_401(self, client):
        """Rate API requires authentication."""
        rv = client.post("/api/rate", json={"book_id": 1, "rating": 4})
        assert rv.status_code == 401

    def test_rate_requires_book_id(self, client):
        """Rate API validates book_id when authenticated."""
        # Without session - should get 401
        rv = client.post("/api/rate", json={"rating": 4})
        assert rv.status_code == 401

    def test_rate_rejects_invalid_rating_value(self, client):
        """Rate API validates rating range and type."""
        with client.session_transaction() as session:
            session["user_id"] = "user-1"

        rv = client.post("/api/rate", json={"book_id": 1, "rating": 6})

        assert rv.status_code == 400
        assert rv.get_json()["error"] == "Rating must be between 1 and 5"

    def test_rate_updates_existing_rating(self, client, monkeypatch):
        """Existing ratings are updated instead of duplicated."""
        interactions = CollectionStub(
            [{"_id": ObjectId(), "user_id": "user-1", "book_id": 1, "interaction": "rating", "rating": 3.0}]
        )
        monkeypatch.setattr(app_module, "db", SimpleNamespace(interactions=interactions))

        with client.session_transaction() as session:
            session["user_id"] = "user-1"

        rv = client.post("/api/rate", json={"book_id": 1, "rating": 4.5})

        assert rv.status_code == 200
        assert interactions.docs[0]["rating"] == 4.5
        assert isinstance(interactions.docs[0]["timestamp"], datetime)

    def test_rate_creates_new_rating_when_missing(self, client, monkeypatch):
        """New ratings are stored through insert_interaction."""
        inserted = {}
        monkeypatch.setattr(app_module, "db", SimpleNamespace(interactions=CollectionStub()))

        def fake_insert_interaction(db, user_id, book_id, interaction, rating=None):
            inserted.update(
                {
                    "user_id": user_id,
                    "book_id": book_id,
                    "interaction": interaction,
                    "rating": rating,
                }
            )

        monkeypatch.setattr(app_module, "insert_interaction", fake_insert_interaction)

        with client.session_transaction() as session:
            session["user_id"] = "user-9"

        rv = client.post("/api/rate", json={"book_id": 42, "rating": 5})

        assert rv.status_code == 200
        assert inserted == {
            "user_id": "user-9",
            "book_id": 42,
            "interaction": "rating",
            "rating": 5.0,
        }

    def test_rate_rejects_non_numeric_rating(self, client):
        """Rating rejects injection-like or non-numeric payloads."""
        with client.session_transaction() as session:
            session["user_id"] = "user-7"

        rv = client.post("/api/rate", json={"book_id": 3, "rating": "five<script>"})

        assert rv.status_code == 400
        assert rv.get_json()["error"] == "Invalid rating"


class TestLikeAPI:
    """Like API tests."""

    def test_like_without_auth_returns_401(self, client):
        """Like API requires authentication."""
        rv = client.post("/api/like", json={"book_id": 1, "action": "like"})
        assert rv.status_code == 401

    def test_like_inserts_only_when_not_already_liked(self, client, monkeypatch):
        """Like endpoint avoids duplicate like entries."""
        inserted = []
        monkeypatch.setattr(app_module, "check_user_interaction", lambda *args: None)
        monkeypatch.setattr(
            app_module,
            "insert_interaction",
            lambda db, user_id, book_id, interaction, rating=None: inserted.append(
                (user_id, book_id, interaction, rating)
            ),
        )

        with client.session_transaction() as session:
            session["user_id"] = "user-1"

        rv = client.post("/api/like", json={"book_id": 5, "action": "like"})

        assert rv.status_code == 200
        assert inserted == [("user-1", 5, "like", None)]

    def test_unlike_deletes_existing_like(self, client, monkeypatch):
        """Unlike removes the stored like interaction."""
        interactions = CollectionStub(
            [{"user_id": "user-1", "book_id": 5, "interaction": "like"}]
        )
        monkeypatch.setattr(app_module, "db", SimpleNamespace(interactions=interactions))

        with client.session_transaction() as session:
            session["user_id"] = "user-1"

        rv = client.post("/api/like", json={"book_id": 5, "action": "unlike"})

        assert rv.status_code == 200
        assert interactions.docs == []

    def test_like_repeated_submission_records_only_once(self, client, monkeypatch):
        """Repeated like requests do not duplicate the same like interaction."""
        stored_likes = []

        def fake_check(db, user_id, book_id, interaction_type):
            return {"user_id": user_id, "book_id": book_id, "interaction": interaction_type} if stored_likes else None

        def fake_insert(db, user_id, book_id, interaction, rating=None):
            stored_likes.append((user_id, book_id, interaction))

        monkeypatch.setattr(app_module, "check_user_interaction", fake_check)
        monkeypatch.setattr(app_module, "insert_interaction", fake_insert)

        with client.session_transaction() as session:
            session["user_id"] = "user-1"

        first = client.post("/api/like", json={"book_id": 5, "action": "like"})
        second = client.post("/api/like", json={"book_id": 5, "action": "like"})

        assert first.status_code == 200
        assert second.status_code == 200
        assert stored_likes == [("user-1", 5, "like")]


class TestPurchaseAPI:
    """Purchase API tests."""

    def test_purchase_without_auth_returns_401(self, client):
        """Purchase API requires authentication."""
        rv = client.post("/api/purchase", json={"book_id": 1})
        assert rv.status_code == 401

    def test_purchase_requires_book_id(self, client):
        """Purchase API validates required fields."""
        with client.session_transaction() as session:
            session["user_id"] = "buyer-1"

        rv = client.post("/api/purchase", json={})

        assert rv.status_code == 400
        assert rv.get_json()["error"] == "book_id required"

    def test_purchase_records_purchase(self, client, monkeypatch):
        """Purchase endpoint stores the interaction."""
        recorded = {}
        monkeypatch.setattr(
            app_module,
            "insert_interaction",
            lambda db, user_id, book_id, interaction, rating=None: recorded.update(
                {
                    "user_id": user_id,
                    "book_id": book_id,
                    "interaction": interaction,
                }
            ),
        )

        with client.session_transaction() as session:
            session["user_id"] = "buyer-1"

        rv = client.post("/api/purchase", json={"book_id": 8})

        assert rv.status_code == 200
        assert recorded == {"user_id": "buyer-1", "book_id": 8, "interaction": "purchase"}


class TestCategoriesAPI:
    """Categories API tests."""

    def test_categories_returns_list(self, client):
        """Categories API returns list."""
        rv = client.get("/api/categories")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)


class TestNeuralRecommendationAPI:
    """Neural recommender and preference analysis API tests."""

    def test_neural_recommend_endpoint_returns_payload(self, client, monkeypatch):
        """Neural recommendation endpoint exposes the hybrid model output."""
        captured = {}

        def fake_neural_recommendations(user_id, db, limit=10, include_model_info=False):
            captured["user_id"] = user_id
            captured["limit"] = limit
            captured["include_model_info"] = include_model_info
            return [{"book_id": 2, "title": "Neural Recommender Systems", "neural_score": 0.91}]

        monkeypatch.setattr(app_module, "get_neural_recommendations", fake_neural_recommendations)

        rv = client.get("/api/neural/recommend/u-1?limit=3")

        assert rv.status_code == 200
        assert captured == {"user_id": "u-1", "limit": 3, "include_model_info": False}
        assert rv.get_json()[0]["neural_score"] == 0.91

    def test_neural_preferences_requires_authentication(self, client):
        """Preference profiles are protected because they expose personal signals."""
        rv = client.get("/api/neural/preferences/u-1")

        assert rv.status_code == 401
        assert rv.get_json()["error"] == "Not authenticated"

    def test_neural_preferences_rejects_other_user(self, client):
        """Users cannot fetch another user's neural preference profile."""
        with client.session_transaction() as session:
            session["user_id"] = "u-1"

        rv = client.get("/api/neural/preferences/u-2")

        assert rv.status_code == 403
        assert rv.get_json()["error"] == "Forbidden"

    def test_neural_preferences_returns_authenticated_profile(self, client, monkeypatch):
        """Authenticated users can fetch their own preference analysis."""
        monkeypatch.setattr(
            app_module,
            "analyze_user_preferences",
            lambda user_id, db: {
                "user_id": user_id,
                "signals_count": 2,
                "top_categories": [{"name": "AI", "weight": 1.0}],
            },
        )

        with client.session_transaction() as session:
            session["user_id"] = "u-1"

        rv = client.get("/api/neural/preferences/u-1")

        assert rv.status_code == 200
        assert rv.get_json()["top_categories"][0]["name"] == "AI"

    def test_neural_model_card_returns_training_metadata(self, client, monkeypatch):
        """Model card endpoint explains architecture and evaluation metrics."""
        monkeypatch.setattr(
            app_module,
            "get_neural_model_card",
            lambda db: {
                "project_topic": "Recommendation System",
                "architecture": {"model_type": "neural_collaborative_filtering"},
                "training": {"validation_rmse": 0.18},
            },
        )

        rv = client.get("/api/neural/model-card")

        assert rv.status_code == 200
        assert rv.get_json()["architecture"]["model_type"] == "neural_collaborative_filtering"

    def test_neural_status_returns_runtime_artifacts(self, client, monkeypatch):
        """Status endpoint proves which neural artifacts the app is using."""
        monkeypatch.setattr(
            app_module,
            "get_neural_status",
            lambda db: {
                "status": "ready",
                "model": {"model_type": "neural_collaborative_filtering_pytorch"},
                "text_embeddings": {"book_embeddings": 10000},
            },
        )

        rv = client.get("/api/neural/status")

        assert rv.status_code == 200
        assert rv.get_json()["status"] == "ready"


class TestInteractionAPI:
    """Interaction and user-state endpoints."""

    def test_interact_requires_book_id(self, client):
        """Interact endpoint validates the payload after auth."""
        with client.session_transaction() as session:
            session["user_id"] = "user-1"

        rv = client.post("/api/interact", json={"interaction": "view"})

        assert rv.status_code == 400
        assert rv.get_json()["error"] == "book_id required"

    def test_interact_records_interaction(self, client, monkeypatch):
        """Interact endpoint forwards the requested interaction type."""
        captured = {}
        monkeypatch.setattr(
            app_module,
            "insert_interaction",
            lambda db, user_id, book_id, interaction, rating=None: captured.update(
                {
                    "user_id": user_id,
                    "book_id": book_id,
                    "interaction": interaction,
                    "rating": rating,
                }
            ),
        )

        with client.session_transaction() as session:
            session["user_id"] = "user-5"

        rv = client.post(
            "/api/interact",
            json={"book_id": 12, "interaction": "rating", "rating": 4},
        )

        assert rv.status_code == 200
        assert captured == {
            "user_id": "user-5",
            "book_id": 12,
            "interaction": "rating",
            "rating": 4,
        }

    def test_interact_defaults_missing_interaction_to_view(self, client, monkeypatch):
        """Missing interaction type defaults to a view event."""
        captured = {}
        monkeypatch.setattr(
            app_module,
            "insert_interaction",
            lambda db, user_id, book_id, interaction, rating=None: captured.update(
                {"user_id": user_id, "book_id": book_id, "interaction": interaction, "rating": rating}
            ),
        )

        with client.session_transaction() as session:
            session["user_id"] = "user-12"

        rv = client.post("/api/interact", json={"book_id": 99})

        assert rv.status_code == 200
        assert captured == {"user_id": "user-12", "book_id": 99, "interaction": "view", "rating": None}

    def test_user_interactions_serializes_object_ids_and_dates(self, client, monkeypatch):
        """User interactions endpoint returns JSON-safe values."""
        monkeypatch.setattr(
            app_module,
            "get_user_interactions",
            lambda db, user_id, interaction_type=None: [
                {
                    "_id": ObjectId("507f1f77bcf86cd799439011"),
                    "book_id": 1,
                    "interaction": "like",
                    "timestamp": datetime(2026, 4, 4, 9, 30, 0),
                }
            ],
        )

        with client.session_transaction() as session:
            session["user_id"] = "user-2"

        rv = client.get("/api/user/interactions?type=like")

        assert rv.status_code == 200
        payload = rv.get_json()
        assert payload[0]["_id"] == "507f1f77bcf86cd799439011"
        assert payload[0]["timestamp"] == "2026-04-04T09:30:00"

    def test_user_interactions_requires_authentication(self, client):
        """Restricted interaction history cannot be fetched anonymously."""
        rv = client.get("/api/user/interactions")

        assert rv.status_code == 401
        assert rv.get_json()["error"] == "Not authenticated"


class TestBooksAPI:
    """Books API tests."""

    def test_books_endpoint_returns_collection_payload(self, client, monkeypatch):
        """Books endpoint returns the stored books as JSON."""
        monkeypatch.setattr(
            app_module,
            "books_collection",
            CollectionStub(
                [
                    {"book_id": 1, "title": "Clean Code", "_id": ObjectId()},
                    {"book_id": 2, "title": "Refactoring", "_id": ObjectId()},
                ]
            ),
        )

        rv = client.get("/api/books")

        assert rv.status_code == 200
        payload = rv.get_json()
        assert payload == [
            {"book_id": 1, "title": "Clean Code"},
            {"book_id": 2, "title": "Refactoring"},
        ]
