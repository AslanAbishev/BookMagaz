"""
P1/P2 - Data layer and models tests
"""
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock

from bson import ObjectId

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import models


class TestModels:
    """Model/data layer tests."""

    def test_create_user_requires_email(self):
        """User creation rejects missing email addresses."""
        db = MagicMock()

        try:
            models.create_user(db, "reader", "hashed-password")
        except ValueError as exc:
            assert str(exc) == "Email is required"
        else:
            raise AssertionError("create_user should reject missing email")

    def test_create_user_normalizes_email_and_defaults(self):
        """User documents normalize email and add expected defaults."""
        db = MagicMock()
        inserted_id = ObjectId()
        db.users.insert_one.return_value.inserted_id = inserted_id

        result = models.create_user(
            db,
            "reader",
            "hashed-password",
            email=" Reader@Example.COM ",
            name="Reader Name",
        )

        inserted = db.users.insert_one.call_args.args[0]
        assert result == inserted_id
        assert inserted["email"] == "reader@example.com"
        assert inserted["name"] == "Reader Name"
        assert inserted["preferences"] == {
            "categories": [],
            "favorite_authors": [],
        }
        assert inserted["reset_token"] is None

    def test_update_user_profile_only_sets_passed_fields(self):
        """Profile updates only include provided fields."""
        db = MagicMock()
        user_id = str(ObjectId())

        models.update_user_profile(db, user_id, email="reader@example.com", name="Reader")

        db.users.update_one.assert_called_once()
        query, update = db.users.update_one.call_args.args
        assert query == {"_id": ObjectId(user_id)}
        assert update == {"$set": {"email": "reader@example.com", "name": "Reader"}}

    def test_insert_interaction_converts_types(self):
        """Interactions store normalized user, book, and rating values."""
        db = MagicMock()

        models.insert_interaction(db, 99, "12", "rating", "4.5")

        inserted = db.interactions.insert_one.call_args.args[0]
        assert inserted["user_id"] == "99"
        assert inserted["book_id"] == 12
        assert inserted["interaction"] == "rating"
        assert inserted["rating"] == 4.5
        assert isinstance(inserted["timestamp"], datetime)

    def test_search_books_combines_text_and_category(self):
        """Text and category search are merged into a single Mongo query."""
        db = MagicMock()
        db.books.find.return_value.limit.return_value = [{"book_id": 1}]

        result = models.search_books(db, "Harry", category="Fantasy", limit=5)

        query = db.books.find.call_args.args[0]
        assert query == {
            "$and": [
                {
                    "$or": [
                        {"title": {"$regex": "Harry", "$options": "i"}},
                        {"authors": {"$regex": "Harry", "$options": "i"}},
                    ]
                },
                {"category": "Fantasy"},
            ]
        }
        assert result == [{"book_id": 1}]
        db.books.find.return_value.limit.assert_called_once_with(5)

    def test_get_all_categories_filters_empty_values(self):
        """Category lookup excludes empty entries and sorts results."""
        db = MagicMock()
        db.books.distinct.return_value = ["Fantasy", "", None, "Classics"]

        categories = models.get_all_categories(db)

        assert categories == ["Classics", "Fantasy"]

    def test_get_user_by_reset_token_checks_expiry(self):
        """Reset token lookup requires a token that has not expired yet."""
        db = MagicMock()
        expected_user = {"email": "reader@example.com"}
        db.users.find_one.return_value = expected_user

        result = models.get_user_by_reset_token(db, "valid-token")

        query = db.users.find_one.call_args.args[0]
        assert query["reset_token"] == "valid-token"
        assert "$gt" in query["reset_token_expiry"]
        assert isinstance(query["reset_token_expiry"]["$gt"], datetime)
        assert result == expected_user

    def test_update_user_password_clears_reset_fields(self):
        """Password updates also clear the reset token and expiry."""
        db = MagicMock()
        user_id = ObjectId()

        models.update_user_password(db, user_id, "new-hash")

        query, update = db.users.update_one.call_args.args
        assert query == {"_id": ObjectId(user_id)}
        assert update == {
            "$set": {
                "password": "new-hash",
                "reset_token": None,
                "reset_token_expiry": None,
            }
        }
