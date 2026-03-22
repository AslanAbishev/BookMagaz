"""
P3 - Medium: Route and page load tests
"""
import pytest


class TestPublicRoutes:
    """Public route tests."""

    def test_index_loads(self, client):
        """Home page loads."""
        rv = client.get("/")
        assert rv.status_code == 200
        assert b"GoodBooks" in rv.data or b"book" in rv.data.lower()

    def test_login_loads(self, client):
        """Login page loads."""
        rv = client.get("/login")
        assert rv.status_code == 200

    def test_register_loads(self, client):
        """Register page loads."""
        rv = client.get("/register")
        assert rv.status_code == 200

    def test_product_page_loads(self, client):
        """Product page loads for valid book_id."""
        rv = client.get("/product/1")
        # May be 200 (book exists) or redirect (book not found)
        assert rv.status_code in [200, 302]

    def test_category_page_loads(self, client):
        """Category page loads."""
        rv = client.get("/category/Fiction")
        assert rv.status_code == 200


class TestProtectedRoutes:
    """Routes requiring authentication."""

    def test_profile_redirects_to_login(self, client):
        """Profile requires login."""
        rv = client.get("/profile", follow_redirects=False)
        assert rv.status_code == 302
        assert "login" in rv.headers.get("Location", "").lower()

    def test_history_redirects_to_login(self, client):
        """Purchase history requires login."""
        rv = client.get("/history", follow_redirects=False)
        assert rv.status_code == 302
        assert "login" in rv.headers.get("Location", "").lower()
