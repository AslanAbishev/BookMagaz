"""
P1/P2 - Data layer and models tests
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestModels:
    """Model/data layer tests - require DB connection."""

    def test_get_all_categories_returns_list(self, client):
        """Categories API uses get_all_categories - returns list."""
        rv = client.get("/api/categories")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)

    def test_search_books_integration(self, client):
        """Search endpoint returns valid structure."""
        rv = client.get("/api/search?q=test&limit=5")
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, dict)
