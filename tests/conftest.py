"""
Pytest configuration and fixtures for GoodBooks test suite.
"""
import os
import sys

# Add project root and backend to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

import pytest
from flask import Flask
from pymongo import MongoClient

# Test configuration
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("TESTING", "1")


@pytest.fixture(scope="session")
def app():
    """Create Flask app for testing."""
    # Import app from backend (backend must be in path)
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture(scope="session")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def db():
    """Get test database connection."""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    return client["goodbooks_test"]  # Use separate test DB


@pytest.fixture
def base_url():
    """Base URL for E2E tests."""
    return os.getenv("BASE_URL", "http://localhost:5000")
