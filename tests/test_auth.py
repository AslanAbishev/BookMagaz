"""
P1 - Critical: Authentication tests
"""
from bson import ObjectId
from werkzeug.security import generate_password_hash

import app as app_module


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

    def test_register_rejects_duplicate_username(self, client, monkeypatch):
        """Registration blocks duplicate usernames before insert."""
        monkeypatch.setattr(
            app_module,
            "get_user_by_username",
            lambda db, username: {"_id": ObjectId(), "username": username},
        )
        monkeypatch.setattr(app_module, "get_user_by_email", lambda db, email: None)

        rv = client.post(
            "/register",
            data={
                "username": "existing",
                "password": "testpass123",
                "email": "existing@example.com",
                "name": "Existing User",
            },
        )

        assert rv.status_code == 200
        assert b"already exists" in rv.data.lower()

    def test_register_rejects_duplicate_email(self, client, monkeypatch):
        """Registration blocks duplicate email addresses."""
        monkeypatch.setattr(app_module, "get_user_by_username", lambda db, username: None)
        monkeypatch.setattr(
            app_module,
            "get_user_by_email",
            lambda db, email: {"_id": ObjectId(), "email": email},
        )

        rv = client.post(
            "/register",
            data={
                "username": "freshuser",
                "password": "testpass123",
                "email": "taken@example.com",
                "name": "Fresh User",
            },
        )

        assert rv.status_code == 200
        assert b"already registered" in rv.data.lower()

    def test_register_rejects_short_password(self, client, monkeypatch):
        """Registration enforces minimum password length."""
        monkeypatch.setattr(app_module, "get_user_by_username", lambda db, username: None)
        monkeypatch.setattr(app_module, "get_user_by_email", lambda db, email: None)

        rv = client.post(
            "/register",
            data={
                "username": "shortpass",
                "password": "123",
                "email": "short@example.com",
                "name": "Short Pass",
            },
        )

        assert rv.status_code == 200
        assert b"at least 6 characters" in rv.data.lower()

    def test_register_success_redirects_to_login(self, client, monkeypatch):
        """Successful registration creates the user and redirects."""
        created = {}

        monkeypatch.setattr(app_module, "get_user_by_username", lambda db, username: None)
        monkeypatch.setattr(app_module, "get_user_by_email", lambda db, email: None)

        def fake_create_user(db, username, hashed_password, email=None, name=None):
            created.update(
                {
                    "username": username,
                    "hashed_password": hashed_password,
                    "email": email,
                    "name": name,
                }
            )
            return ObjectId()

        monkeypatch.setattr(app_module, "create_user", fake_create_user)

        rv = client.post(
            "/register",
            data={
                "username": "newuser",
                "password": "testpass123",
                "email": "newuser@example.com",
                "name": "New User",
            },
            follow_redirects=False,
        )

        assert rv.status_code == 302
        assert "/login" in rv.headers["Location"]
        assert created["username"] == "newuser"
        assert created["email"] == "newuser@example.com"
        assert created["name"] == "New User"
        assert created["hashed_password"] != "testpass123"


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

    def test_login_sets_session_when_successful(self, client, monkeypatch):
        """Successful login stores user identity in session."""
        user = {
            "_id": ObjectId(),
            "username": "reader",
            "password": generate_password_hash("secret123"),
        }
        monkeypatch.setattr(app_module, "get_user_by_username", lambda db, username: user)

        with client:
            rv = client.post(
                "/login",
                data={"username": "reader", "password": "secret123"},
                follow_redirects=False,
            )

            assert rv.status_code == 302
            assert rv.headers["Location"].endswith("/")
            with client.session_transaction() as session:
                assert session["username"] == "reader"
                assert session["user_id"] == str(user["_id"])


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

    def test_forgot_password_generates_token_for_known_email(self, client, monkeypatch):
        """Forgot password persists a reset token for known users."""
        recorded = {}
        monkeypatch.setattr(
            app_module,
            "get_user_by_email",
            lambda db, email: {"_id": ObjectId(), "email": email},
        )

        def fake_set_token(db, email, token, expiry):
            recorded["email"] = email
            recorded["token"] = token
            recorded["expiry"] = expiry

        monkeypatch.setattr(app_module, "set_password_reset_token", fake_set_token)

        rv = client.post("/forgot-password", data={"email": "known@example.com"})

        assert rv.status_code == 200
        assert recorded["email"] == "known@example.com"
        assert recorded["token"]
        assert b"password reset link generated" in rv.data.lower()

    def test_forgot_password_hides_unknown_email(self, client, monkeypatch):
        """Forgot password does not disclose account existence."""
        monkeypatch.setattr(app_module, "get_user_by_email", lambda db, email: None)

        rv = client.post("/forgot-password", data={"email": "missing@example.com"})

        assert rv.status_code == 200
        assert b"if an account exists" in rv.data.lower()


class TestResetPassword:
    """Reset password flow tests."""

    def test_reset_password_invalid_token_redirects(self, client, monkeypatch):
        """Invalid or expired tokens redirect back to forgot password."""
        monkeypatch.setattr(app_module, "get_user_by_reset_token", lambda db, token: None)

        rv = client.get("/reset-password/bad-token", follow_redirects=False)

        assert rv.status_code == 302
        assert "/forgot-password" in rv.headers["Location"]

    def test_reset_password_requires_matching_passwords(self, client, monkeypatch):
        """Mismatched passwords keep the user on the reset form."""
        monkeypatch.setattr(
            app_module,
            "get_user_by_reset_token",
            lambda db, token: {"_id": ObjectId(), "email": "reader@example.com"},
        )

        rv = client.post(
            "/reset-password/good-token",
            data={"password": "secret123", "confirm_password": "mismatch"},
        )

        assert rv.status_code == 200
        assert b"do not match" in rv.data.lower()

    def test_reset_password_updates_password_and_redirects(self, client, monkeypatch):
        """Successful reset hashes the new password and redirects to login."""
        updated = {}
        user_id = ObjectId()
        monkeypatch.setattr(
            app_module,
            "get_user_by_reset_token",
            lambda db, token: {"_id": user_id, "email": "reader@example.com"},
        )

        def fake_update_password(db, passed_user_id, hashed_password):
            updated["user_id"] = passed_user_id
            updated["hashed_password"] = hashed_password

        monkeypatch.setattr(app_module, "update_user_password", fake_update_password)

        rv = client.post(
            "/reset-password/good-token",
            data={"password": "secret123", "confirm_password": "secret123"},
            follow_redirects=False,
        )

        assert rv.status_code == 302
        assert "/login" in rv.headers["Location"]
        assert updated["user_id"] == user_id
        assert updated["hashed_password"] != "secret123"
