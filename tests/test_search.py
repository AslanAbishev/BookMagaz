"""
P2 - High: Search functionality tests
"""
import pytest


class TestSearch:
    """Search tests."""

    def test_search_by_text(self, client):
        """Search with text query returns results."""
        rv = client.get("/api/search?q=Harry&limit=10")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)

    def test_search_by_category(self, client):
        """Search with category filter."""
        rv = client.get("/api/search?q=&category=Fiction&limit=10")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)

    def test_search_combined(self, client):
        """Search with both text and category."""
        rv = client.get("/api/search?q=book&category=Fiction&limit=5")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)

    def test_search_result_structure(self, client):
        """Search results have expected fields."""
        rv = client.get("/api/search?q=the&limit=1")
        assert rv.status_code == 200
        data = rv.get_json()
        if len(data) > 0:
            book = data[0]
            assert "book_id" in book or "title" in book
            assert "title" in book or "authors" in book
