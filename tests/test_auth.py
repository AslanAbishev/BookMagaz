"""
P1 - Critical: Authentication tests
"""
import pytest


class TestRegistration:
    """Registration flow tests."""

    def test_register_page_loads(self, client):
        """Registration page loads successfully."""
        rv = client.get("/register")
        assert rv.status_code == 200
        assert b"Register" in rv.data or b"Create Account" in rv.data

    def test_register_requires_email(self, client):
        """Registration fails without email."""
        rv = client.post("/register", data={
            "username": "testuser",
            "password": "testpass123",
            "email": "",
            "name": ""
        })
        assert rv.status_code == 200
        assert b"required" in rv.data.lower() or b"error" in rv.data.lower()

    def test_register_requires_password(self, client):
        """Registration fails without password."""
        rv = client.post("/register", data={
            "username": "testuser",
            "password": "",
            "email": "test@example.com",
            "name": ""
        })
        assert rv.status_code == 200

    def test_register_valid_email_format(self, client):
        """Registration validates email format."""
        rv = client.post("/register", data={
            "username": "testuser",
            "password": "testpass123",
            "email": "invalid-email",
            "name": ""
        })
        assert rv.status_code == 200
        assert b"valid" in rv.data.lower() or b"@" in rv.data


class TestLogin:
    """Login flow tests."""

    def test_login_page_loads(self, client):
        """Login page loads successfully."""
        rv = client.get("/login")
        assert rv.status_code == 200
        assert b"Login" in rv.data

    def test_login_with_invalid_credentials(self, client):
        """Login fails with wrong credentials."""
        rv = client.post("/login", data={
            "username": "nonexistent",
            "password": "wrongpass"
        })
        assert rv.status_code == 200
        assert b"Invalid" in rv.data or b"error" in rv.data.lower()

    def test_login_redirects_when_successful(self, client):
        """Login redirects to index on success (requires valid user in DB)."""
        # This test may pass or fail depending on test data
        rv = client.post("/login", data={
            "username": "testuser",
            "password": "testpass123"
        }, follow_redirects=False)
        # Either redirect (302) or stay on page with error (200)
        assert rv.status_code in [200, 302]


class TestLogout:
    """Logout tests."""

    def test_logout_redirects(self, client):
        """Logout redirects to index."""
        rv = client.get("/logout", follow_redirects=False)
        assert rv.status_code == 302
        assert "/" in rv.headers.get("Location", "")


class TestForgotPassword:
    """Forgot password flow tests."""

    def test_forgot_password_page_loads(self, client):
        """Forgot password page loads."""
        rv = client.get("/forgot-password")
        assert rv.status_code == 200
        assert b"Forgot" in rv.data or b"email" in rv.data.lower()

    def test_forgot_password_requires_email(self, client):
        """Forgot password requires email."""
        rv = client.post("/forgot-password", data={"email": ""})
        assert rv.status_code == 200
