"""Shared helpers for experimental engineering assignments.

These helpers build a deterministic in-memory GoodBooks environment so we can
run performance, mutation, and chaos experiments without depending on a live
MongoDB instance.
"""
from __future__ import annotations

import copy
import os
import sys
import shutil
import uuid
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = PROJECT_ROOT / ".tmp_experiments"
WORK_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import app as app_module
import recommend
from tests.helpers import CollectionStub


def build_sample_db() -> SimpleNamespace:
    """Create a deterministic in-memory dataset for experiments."""
    books = [
        {
            "book_id": 1,
            "title": "Clean Code",
            "authors": "Robert C. Martin",
            "category": "Software",
            "average_rating": 4.7,
            "ratings_count": 550,
            "price": 25.0,
            "image_url": "https://example.com/1.jpg",
        },
        {
            "book_id": 2,
            "title": "Refactoring",
            "authors": "Martin Fowler",
            "category": "Software",
            "average_rating": 4.6,
            "ratings_count": 480,
            "price": 27.0,
            "image_url": "https://example.com/2.jpg",
        },
        {
            "book_id": 3,
            "title": "The Pragmatic Programmer",
            "authors": "Andrew Hunt, David Thomas",
            "category": "Software",
            "average_rating": 4.8,
            "ratings_count": 620,
            "price": 29.0,
            "image_url": "https://example.com/3.jpg",
        },
        {
            "book_id": 4,
            "title": "Deep Work",
            "authors": "Cal Newport",
            "category": "Productivity",
            "average_rating": 4.4,
            "ratings_count": 410,
            "price": 18.0,
            "image_url": "https://example.com/4.jpg",
        },
        {
            "book_id": 5,
            "title": "Atomic Habits",
            "authors": "James Clear",
            "category": "Productivity",
            "average_rating": 4.8,
            "ratings_count": 800,
            "price": 20.0,
            "image_url": "https://example.com/5.jpg",
        },
        {
            "book_id": 6,
            "title": "Dune",
            "authors": "Frank Herbert",
            "category": "Science Fiction",
            "average_rating": 4.5,
            "ratings_count": 1000,
            "price": 22.0,
            "image_url": "https://example.com/6.jpg",
        },
        {
            "book_id": 7,
            "title": "Neuromancer",
            "authors": "William Gibson",
            "category": "Science Fiction",
            "average_rating": 4.1,
            "ratings_count": 300,
            "price": 19.0,
            "image_url": "https://example.com/7.jpg",
        },
        {
            "book_id": 8,
            "title": "The Martian",
            "authors": "Andy Weir",
            "category": "Science Fiction",
            "average_rating": 4.6,
            "ratings_count": 910,
            "price": 21.0,
            "image_url": "https://example.com/8.jpg",
        },
    ]

    users = [
        {
            "_id": ObjectId("64a000000000000000000001"),
            "username": "reader1",
            "password": "hashed-password",
            "email": "reader1@example.com",
            "name": "Reader One",
            "preferences": {"categories": ["Software"], "favorite_authors": ["Martin Fowler"]},
        },
        {
            "_id": ObjectId("64a000000000000000000002"),
            "username": "reader2",
            "password": "hashed-password",
            "email": "reader2@example.com",
            "name": "Reader Two",
            "preferences": {"categories": ["Science Fiction"], "favorite_authors": ["Frank Herbert"]},
        },
    ]

    interactions = [
        {
            "_id": ObjectId("64b000000000000000000001"),
            "user_id": "u-1",
            "book_id": 1,
            "interaction": "rating",
            "rating": 5.0,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 0, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000002"),
            "user_id": "u-1",
            "book_id": 2,
            "interaction": "rating",
            "rating": 4.0,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 5, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000003"),
            "user_id": "u-2",
            "book_id": 1,
            "interaction": "rating",
            "rating": 4.0,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 10, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000004"),
            "user_id": "u-2",
            "book_id": 3,
            "interaction": "rating",
            "rating": 5.0,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 15, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000005"),
            "user_id": "u-3",
            "book_id": 6,
            "interaction": "rating",
            "rating": 5.0,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 20, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000006"),
            "user_id": "u-3",
            "book_id": 8,
            "interaction": "rating",
            "rating": 4.0,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 25, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000007"),
            "user_id": "u-1",
            "book_id": 5,
            "interaction": "like",
            "rating": None,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 30, 0),
        },
        {
            "_id": ObjectId("64b000000000000000000008"),
            "user_id": "u-1",
            "book_id": 4,
            "interaction": "purchase",
            "rating": None,
            "timestamp": __import__("datetime").datetime(2026, 4, 20, 10, 35, 0),
        },
    ]

    db = SimpleNamespace(
        books=CollectionStub(books),
        users=CollectionStub(users),
        interactions=CollectionStub(interactions),
    )
    return db


@contextmanager
def patched_app_environment():
    """Patch the Flask app and recommendation cache to use stub data."""
    db = build_sample_db()
    env_dir = WORK_DIR / f"exp_env_{uuid.uuid4().hex[:8]}"
    env_dir.mkdir(parents=True, exist_ok=True)
    cache_file = env_dir / "sim_cache.pkl"
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(app_module, "db", db))
            stack.enter_context(patch.object(app_module, "books_collection", db.books))
            stack.enter_context(patch.object(app_module, "ratings_collection", db.interactions))
            stack.enter_context(patch.object(app_module, "interactions_collection", db.interactions))
            stack.enter_context(patch.object(app_module, "users_collection", db.users))
            stack.enter_context(patch.object(recommend, "CACHE_FILE", str(cache_file)))
            yield db, cache_file
    finally:
        shutil.rmtree(env_dir, ignore_errors=True)


def make_client():
    """Create a Flask test client with exception propagation disabled."""
    flask_app = app_module.app
    flask_app.config["TESTING"] = False
    flask_app.config["PROPAGATE_EXCEPTIONS"] = False
    flask_app.secret_key = os.getenv("SECRET_KEY", "experimental-secret")
    return flask_app.test_client()


def clone_rows(rows):
    """Deep-copy experiment rows before writing them to disk."""
    return copy.deepcopy(rows)
