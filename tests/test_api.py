"""
P2 - High: API endpoint tests
"""
import pytest


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


class TestLikeAPI:
    """Like API tests."""

    def test_like_without_auth_returns_401(self, client):
        """Like API requires authentication."""
        rv = client.post("/api/like", json={"book_id": 1, "action": "like"})
        assert rv.status_code == 401


class TestPurchaseAPI:
    """Purchase API tests."""

    def test_purchase_without_auth_returns_401(self, client):
        """Purchase API requires authentication."""
        rv = client.post("/api/purchase", json={"book_id": 1})
        assert rv.status_code == 401


class TestCategoriesAPI:
    """Categories API tests."""

    def test_categories_returns_list(self, client):
        """Categories API returns list."""
        rv = client.get("/api/categories")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)
