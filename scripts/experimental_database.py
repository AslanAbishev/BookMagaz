"""Database-focused experimental checks for GoodBooks Assignment 3."""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from models import get_popular_books, search_books
from tests.helpers import CollectionStub


EVIDENCE_DIR = PROJECT_ROOT / "docs" / "experimental_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


class IndexedCollectionStub(CollectionStub):
    """Collection stub with simple index metadata for DB-level reporting."""

    def __init__(self, docs=None, indexes=None):
        super().__init__(docs)
        self._indexes = indexes or {"_id_": {"key": [("_id", 1)]}}

    def index_information(self):
        return self._indexes


def percentile(values, p):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def build_database_experiment_db() -> SimpleNamespace:
    books = [
        {
            "book_id": 1,
            "title": "Clean Code",
            "authors": "Robert C. Martin",
            "category": "Software",
            "average_rating": 4.7,
            "ratings_count": 550,
        },
        {
            "book_id": 2,
            "title": "Refactoring",
            "authors": "Martin Fowler",
            "category": "Software",
            "average_rating": 4.6,
            "ratings_count": 480,
        },
        {
            "book_id": 3,
            "title": "The Pragmatic Programmer",
            "authors": "Andrew Hunt, David Thomas",
            "category": "Software",
            "average_rating": 4.8,
            "ratings_count": 620,
        },
        {
            "book_id": 4,
            "title": "Atomic Habits",
            "authors": "James Clear",
            "category": "Productivity",
            "average_rating": 4.8,
            "ratings_count": 800,
        },
        {
            "book_id": 5,
            "title": "Dune",
            "authors": "Frank Herbert",
            "category": "Science Fiction",
            "average_rating": 4.5,
            "ratings_count": 1000,
        },
        {
            "book_id": 6,
            "title": "The Martian",
            "authors": "Andy Weir",
            "category": "Science Fiction",
            "average_rating": 4.6,
            "ratings_count": 910,
        },
    ]

    users = [
        {"username": "u-1", "email": "u1@example.com", "name": "Reader One"},
        {"username": "u-2", "email": "u2@example.com", "name": "Reader Two"},
        {"username": "u-3", "email": "u3@example.com", "name": "Reader Three"},
    ]

    interactions = [
        {"user_id": "u-1", "book_id": 1, "interaction": "rating", "rating": 5.0},
        {"user_id": "u-1", "book_id": 2, "interaction": "rating", "rating": 4.0},
        {"user_id": "u-1", "book_id": 4, "interaction": "purchase", "rating": None},
        {"user_id": "u-2", "book_id": 1, "interaction": "rating", "rating": 4.0},
        {"user_id": "u-2", "book_id": 3, "interaction": "rating", "rating": 5.0},
        {"user_id": "u-3", "book_id": 5, "interaction": "rating", "rating": 5.0},
        {"user_id": "u-3", "book_id": 6, "interaction": "rating", "rating": 4.0},
    ]

    books_indexes = {
        "_id_": {"key": [("_id", 1)]},
        "title_authors_text": {"key": [("title", "text"), ("authors", "text")]},
        "category_1": {"key": [("category", 1)]},
        "book_id_1": {"key": [("book_id", 1)]},
        "average_rating_1": {"key": [("average_rating", 1)]},
        "category_1_average_rating_-1": {"key": [("category", 1), ("average_rating", -1)]},
    }
    users_indexes = {"_id_": {"key": [("_id", 1)]}}
    interactions_indexes = {"_id_": {"key": [("_id", 1)]}}

    return SimpleNamespace(
        books=IndexedCollectionStub(books, books_indexes),
        users=IndexedCollectionStub(users, users_indexes),
        interactions=IndexedCollectionStub(interactions, interactions_indexes),
    )


def run_integrity_checks(db):
    rows = []

    duplicate_usernames = len({doc["username"] for doc in db.users.docs}) != len(db.users.docs)
    rows.append(
        {
            "check": "duplicate_usernames",
            "status": "PASS" if not duplicate_usernames else "FAIL",
            "details": "No duplicate usernames found" if not duplicate_usernames else "Duplicate usernames detected",
        }
    )

    duplicate_emails = len({doc["email"] for doc in db.users.docs}) != len(db.users.docs)
    rows.append(
        {
            "check": "duplicate_emails",
            "status": "PASS" if not duplicate_emails else "FAIL",
            "details": "No duplicate emails found" if not duplicate_emails else "Duplicate emails detected",
        }
    )

    invalid_ratings = [
        doc
        for doc in db.interactions.docs
        if doc.get("interaction") == "rating"
        and (not isinstance(doc.get("rating"), (int, float)) or doc["rating"] < 1 or doc["rating"] > 5)
    ]
    rows.append(
        {
            "check": "rating_range_and_type",
            "status": "PASS" if not invalid_ratings else "FAIL",
            "details": f"Invalid rating count: {len(invalid_ratings)}",
        }
    )

    known_users = {doc["username"] for doc in db.users.docs}
    orphaned_interactions = [doc for doc in db.interactions.docs if doc["user_id"] not in known_users]
    rows.append(
        {
            "check": "orphaned_interactions",
            "status": "PASS" if not orphaned_interactions else "FAIL",
            "details": f"Orphaned interaction count: {len(orphaned_interactions)}",
        }
    )

    return rows


def run_query_benchmarks(db, iterations=120):
    scenarios = [
        (
            "find_user_by_username",
            lambda: db.users.find_one({"username": "u-1"}),
            "no",
            "users.username unique index missing",
        ),
        (
            "find_user_by_email",
            lambda: db.users.find_one({"email": "u1@example.com"}),
            "no",
            "users.email unique index missing",
        ),
        (
            "find_book_by_book_id",
            lambda: db.books.find_one({"book_id": 1}),
            "yes",
            "book_id index present",
        ),
        (
            "find_books_by_category",
            lambda: list(db.books.find({"category": "Software"}).limit(10)),
            "yes",
            "category index present",
        ),
        (
            "find_interactions_by_user",
            lambda: list(db.interactions.find({"user_id": "u-1"})),
            "no",
            "interactions.user_id index missing",
        ),
        (
            "search_books_text_and_category",
            lambda: search_books(db, "Code", category="Software", limit=10),
            "partial",
            "application uses regex fallback rather than a pure text-index path",
        ),
        (
            "get_popular_books",
            lambda: get_popular_books(db, limit=5),
            "partial",
            "average_rating index exists but ratings_count compound support is missing",
        ),
    ]

    rows = []
    for name, fn, indexed, note in scenarios:
        timings = []
        result_len = 0
        for _ in range(iterations):
            started = time.perf_counter()
            result = fn()
            timings.append((time.perf_counter() - started) * 1000)
            if isinstance(result, list):
                result_len = len(result)
            else:
                result_len = 1 if result else 0
        rows.append(
            {
                "query": name,
                "avg_ms": round(statistics.mean(timings), 4),
                "p95_ms": round(percentile(timings, 0.95), 4),
                "max_ms": round(max(timings), 4),
                "results_returned": result_len,
                "indexed": indexed,
                "note": note,
            }
        )
    return rows


def run_index_audit(db):
    rows = []
    checks = [
        ("books", "book_id_1", "HIGH"),
        ("books", "category_1", "MEDIUM"),
        ("books", "title_authors_text", "MEDIUM"),
        ("users", "username_unique", "CRITICAL"),
        ("users", "email_unique", "CRITICAL"),
        ("interactions", "user_id_idx", "HIGH"),
        ("interactions", "book_id_idx", "HIGH"),
        ("interactions", "user_id_1_book_id_1", "HIGH"),
    ]
    for collection_name, index_name, priority in checks:
        collection = getattr(db, collection_name)
        present = index_name in collection.index_information()
        rows.append(
            {
                "collection": collection_name,
                "index_name": index_name,
                "priority": priority,
                "present": "yes" if present else "no",
            }
        )
    return rows


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    db = build_database_experiment_db()
    integrity_rows = run_integrity_checks(db)
    query_rows = run_query_benchmarks(db)
    index_rows = run_index_audit(db)

    integrity_path = EVIDENCE_DIR / "database_integrity_results.csv"
    query_path = EVIDENCE_DIR / "database_query_results.csv"
    index_path = EVIDENCE_DIR / "database_index_results.csv"
    json_path = EVIDENCE_DIR / "database_results.json"
    log_path = EVIDENCE_DIR / "database_run.txt"

    write_csv(integrity_path, integrity_rows)
    write_csv(query_path, query_rows)
    write_csv(index_path, index_rows)

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "integrity": integrity_rows,
        "queries": query_rows,
        "indexes": index_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    missing_indexes = sum(1 for row in index_rows if row["present"] == "no")
    slowest_query = max(query_rows, key=lambda row: row["avg_ms"])
    lines = [
        "GoodBooks database-focused experimental run",
        "",
        f"Integrity checks passed: {sum(1 for row in integrity_rows if row['status'] == 'PASS')}/{len(integrity_rows)}",
        f"Missing expected indexes: {missing_indexes}",
        f"Slowest query: {slowest_query['query']} ({slowest_query['avg_ms']} ms avg)",
        "",
        "Integrity checks:",
    ]
    for row in integrity_rows:
        lines.append(f"- {row['check']}: {row['status']} ({row['details']})")
    lines.append("")
    lines.append("Query benchmarks:")
    for row in query_rows:
        lines.append(
            f"- {row['query']}: avg={row['avg_ms']} ms p95={row['p95_ms']} ms indexed={row['indexed']}"
        )
    lines.append("")
    lines.append("Index audit:")
    for row in index_rows:
        lines.append(
            f"- {row['collection']}.{row['index_name']}: present={row['present']} priority={row['priority']}"
        )
    log_path.write_text("\n".join(lines), encoding="utf-8")

    print("Database experiment complete")
    print(f"Integrity CSV: {integrity_path}")
    print(f"Query CSV: {query_path}")
    print(f"Index CSV: {index_path}")
    print(f"JSON: {json_path}")
    print(f"LOG: {log_path}")
    for row in query_rows:
        print(
            f"{row['query']} -> avg={row['avg_ms']} ms, p95={row['p95_ms']} ms, indexed={row['indexed']}"
        )


if __name__ == "__main__":
    main()
