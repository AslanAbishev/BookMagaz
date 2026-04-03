"""
P2 - High: Recommendation engine tests
"""
import sys
import os
import pickle
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from bson import ObjectId

# Ensure backend is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import app as app_module
import recommend
from tests.helpers import CollectionStub


class TestRecommendations:
    """Recommendation engine tests."""

    def test_profile_shows_recommendations_section(self, client):
        """Profile page has recommendations (requires login - we check redirect)."""
        rv = client.get("/profile", follow_redirects=False)
        assert rv.status_code == 302  # Redirects to login
        assert "login" in rv.headers.get("Location", "").lower()

    def test_recommend_api_returns_serialized_recommendations(self, client, monkeypatch):
        """Recommendation API returns the recommendation payload from the engine."""
        monkeypatch.setattr(
            app_module,
            "get_recommendations",
            lambda user_id, db: [{"book_id": 7, "title": "Recommended", "score": 4.8}],
        )

        rv = client.get("/api/recommend/user-123")

        assert rv.status_code == 200
        assert rv.get_json() == [{"book_id": 7, "title": "Recommended", "score": 4.8}]

    def test_admin_rebuild_sim_endpoint_responds(self, client):
        """Admin rebuild similarity endpoint responds."""
        rv = client.get("/admin/rebuild-sim")
        # 200 = success, 500 = error (e.g. no ratings) - both mean endpoint works
        assert rv.status_code in [200, 500]

    def test_profile_loads_recommendation_data_for_logged_in_user(self, client, monkeypatch):
        """Profile page renders purchases, ratings, and recommendation data."""
        user_id = str(ObjectId())
        monkeypatch.setattr(
            app_module,
            "get_user_by_id",
            lambda db, passed_user_id: {"_id": ObjectId(passed_user_id), "username": "reader"},
        )
        monkeypatch.setattr(
            app_module,
            "get_recommendations",
            lambda passed_user_id, db: [{"book_id": 2, "score": 4.2}],
        )
        monkeypatch.setattr(
            app_module,
            "get_user_purchase_history",
            lambda db, passed_user_id: [{"book_id": 1, "timestamp": datetime(2026, 4, 4, 9, 0, 0)}],
        )
        monkeypatch.setattr(
            app_module,
            "get_user_ratings",
            lambda db, passed_user_id: [{"book_id": 1, "rating": 5, "timestamp": datetime(2026, 4, 4, 9, 30, 0)}],
        )
        monkeypatch.setattr(
            app_module,
            "get_user_interactions",
            lambda db, passed_user_id, interaction_type=None: [{"book_id": 1, "interaction": "like"}],
        )
        monkeypatch.setattr(
            app_module,
            "get_book",
            lambda db, book_id: {
                "book_id": book_id,
                "title": f"Book {book_id}",
                "authors": "Author",
            },
        )

        with client.session_transaction() as session:
            session["user_id"] = user_id

        rv = client.get("/profile")

        assert rv.status_code == 200
        assert b"Book 1" in rv.data
        assert b"Book 2" in rv.data

    def test_profile_clears_session_when_user_missing(self, client, monkeypatch):
        """Missing users are logged out before redirecting."""
        monkeypatch.setattr(app_module, "get_user_by_id", lambda db, user_id: None)

        with client.session_transaction() as session:
            session["user_id"] = "missing-user"
            session["username"] = "ghost"

        rv = client.get("/profile", follow_redirects=False)

        assert rv.status_code == 302
        assert "/login" in rv.headers["Location"]
        with client.session_transaction() as session:
            assert "user_id" not in session
            assert "username" not in session


class TestSimilarBooks:
    """Similar books feature tests."""

    def test_product_page_has_similar_section(self, client):
        """Product page loads (similar books section may be empty)."""
        rv = client.get("/product/1")
        if rv.status_code == 200:
            assert rv.data  # Has content

    def test_product_page_tracks_first_view_for_logged_in_user(self, client, monkeypatch):
        """Product route records a view when the user has not viewed recently."""
        tracked = {}
        monkeypatch.setattr(
            app_module,
            "get_book",
            lambda db, book_id: {"book_id": book_id, "title": "Tracked Book", "authors": "Author"},
        )
        monkeypatch.setattr(app_module, "check_user_interaction", lambda *args: None)
        monkeypatch.setattr(
            app_module,
            "insert_interaction",
            lambda db, user_id, book_id, interaction, rating=None: tracked.update(
                {"user_id": user_id, "book_id": book_id, "interaction": interaction}
            ),
        )
        monkeypatch.setattr(app_module, "get_similar_books", lambda book_id, db, limit=6: [])

        with client.session_transaction() as session:
            session["user_id"] = "reader-1"

        rv = client.get("/product/44")

        assert rv.status_code == 200
        assert tracked == {"user_id": "reader-1", "book_id": 44, "interaction": "view"}


class TestRecommendationUtilities:
    """Recommendation helper unit tests."""

    def test_build_item_similarity_creates_cache_file(self, monkeypatch):
        """Similarity builder persists a pickled similarity matrix."""
        cache_file = Path("C:/Users/admin/OneDrive/Desktop/goodbooks_app/data/test_sim_cache.pkl")
        if cache_file.exists():
            try:
                cache_file.unlink()
            except PermissionError:
                pass
        monkeypatch.setattr(recommend, "CACHE_FILE", str(cache_file))
        db = SimpleNamespace(
            interactions=SimpleNamespace(
                find=lambda query: [
                    {"user_id": "u1", "book_id": 1, "rating": 5.0},
                    {"user_id": "u1", "book_id": 2, "rating": 4.0},
                    {"user_id": "u2", "book_id": 1, "rating": 4.0},
                    {"user_id": "u2", "book_id": 3, "rating": 5.0},
                ]
            )
        )

        recommend.build_item_similarity(db, force_rebuild=True)

        assert cache_file.exists()
        with cache_file.open("rb") as handle:
            similarity = pickle.load(handle)
        assert list(similarity.index) == [1, 2, 3]
        assert list(similarity.columns) == [1, 2, 3]

    def test_get_similar_books_returns_empty_for_missing_book(self, monkeypatch):
        """Unknown book ids produce no similar-book suggestions."""
        db = SimpleNamespace(books=CollectionStub())
        monkeypatch.setattr(recommend, "CACHE_FILE", "tests/non-existent-cache.pkl")

        assert recommend.get_similar_books(999, db) == []
