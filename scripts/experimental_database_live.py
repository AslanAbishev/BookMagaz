"""Live MongoDB experimental checks for GoodBooks Assignment 3."""
from __future__ import annotations

import csv
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from models import get_popular_books, search_books


EVIDENCE_DIR = PROJECT_ROOT / "docs" / "experimental_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("GOODBOOKS_DB", "goodbooks")
SAMPLE_SIZE = 1000


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


def normalize_stage(plan):
    if not isinstance(plan, dict):
        return "UNKNOWN"
    stage = plan.get("stage")
    if stage:
        if stage in {"FETCH", "LIMIT", "SORT", "PROJECTION_SIMPLE", "PROJECTION_DEFAULT"} and "inputStage" in plan:
            return normalize_stage(plan["inputStage"])
        return stage
    if "queryPlan" in plan:
        return normalize_stage(plan["queryPlan"])
    if "winningPlan" in plan:
        return normalize_stage(plan["winningPlan"])
    if "inputStage" in plan:
        return normalize_stage(plan["inputStage"])
    if "inputStages" in plan and plan["inputStages"]:
        return normalize_stage(plan["inputStages"][0])
    if "shards" in plan and plan["shards"]:
        first = next(iter(plan["shards"].values()))
        return normalize_stage(first)
    return "UNKNOWN"


def safe_first(collection, projection=None):
    return collection.find_one({}, projection)


def benchmark_query(name, fn, explain_fn, note, iterations=25):
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

    explain = explain_fn()
    plan_stage = normalize_stage(explain.get("queryPlanner", {}).get("winningPlan", explain))
    return {
        "query": name,
        "avg_ms": round(statistics.mean(timings), 4),
        "p95_ms": round(percentile(timings, 0.95), 4),
        "max_ms": round(max(timings), 4),
        "results_returned": result_len,
        "winning_plan": plan_stage,
        "note": note,
    }


def run_integrity_and_schema_checks(db):
    users_count = db.users.count_documents({})
    books_count = db.books.count_documents({})
    interactions_count = db.interactions.count_documents({})

    rows = [
        {
            "check": "collection_counts",
            "status": "INFO",
            "details": f"users={users_count}, books={books_count}, interactions={interactions_count}",
        }
    ]

    duplicate_usernames = list(
        db.users.aggregate(
            [
                {"$group": {"_id": "$username", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}, "count": {"$gt": 1}}},
                {"$limit": 1},
            ]
        )
    )
    rows.append(
        {
            "check": "duplicate_usernames",
            "status": "PASS" if not duplicate_usernames else "FAIL",
            "details": "No duplicate usernames found" if not duplicate_usernames else "Duplicate usernames detected",
        }
    )

    emails_present = db.users.count_documents({"email": {"$exists": True, "$nin": [None, ""]}})
    if emails_present:
        duplicate_emails = list(
            db.users.aggregate(
                [
                    {"$match": {"email": {"$exists": True, "$nin": [None, ""]}}},
                    {"$group": {"_id": "$email", "count": {"$sum": 1}}},
                    {"$match": {"count": {"$gt": 1}}},
                    {"$limit": 1},
                ]
            )
        )
        rows.append(
            {
                "check": "duplicate_emails",
                "status": "PASS" if not duplicate_emails else "FAIL",
                "details": f"email-bearing users={emails_present}",
            }
        )
    else:
        rows.append(
            {
                "check": "duplicate_emails",
                "status": "WARN",
                "details": "email field is absent across the live users collection",
            }
        )

    invalid_ratings = db.interactions.count_documents(
        {
            "rating": {"$exists": True},
            "$or": [
                {"rating": {"$type": "string"}},
                {"rating": {"$lt": 1}},
                {"rating": {"$gt": 5}},
            ],
        }
    )
    rows.append(
        {
            "check": "rating_range_and_type",
            "status": "PASS" if invalid_ratings == 0 else "FAIL",
            "details": f"invalid_ratings={invalid_ratings}",
        }
    )

    user_name_field_coverage = round(
        db.users.count_documents({"name": {"$exists": True, "$ne": None}}) / max(users_count, 1) * 100,
        2,
    )
    user_email_field_coverage = round(emails_present / max(users_count, 1) * 100, 2)
    book_category_coverage = round(
        db.books.count_documents({"category": {"$exists": True, "$nin": [None, ""]}}) / max(books_count, 1) * 100,
        2,
    )
    interaction_type_coverage = round(
        db.interactions.count_documents({"interaction": {"$exists": True, "$nin": [None, ""]}})
        / max(interactions_count, 1)
        * 100,
        2,
    )
    timestamp_coverage = round(
        db.interactions.count_documents({"timestamp": {"$exists": True, "$ne": None}})
        / max(interactions_count, 1)
        * 100,
        2,
    )

    rows.extend(
        [
            {
                "check": "users_name_field_coverage",
                "status": "PASS" if user_name_field_coverage >= 90 else "WARN",
                "details": f"{user_name_field_coverage}%",
            },
            {
                "check": "users_email_field_coverage",
                "status": "PASS" if user_email_field_coverage >= 90 else "WARN",
                "details": f"{user_email_field_coverage}%",
            },
            {
                "check": "books_category_field_coverage",
                "status": "PASS" if book_category_coverage >= 90 else "WARN",
                "details": f"{book_category_coverage}%",
            },
            {
                "check": "interactions_interaction_field_coverage",
                "status": "PASS" if interaction_type_coverage >= 90 else "WARN",
                "details": f"{interaction_type_coverage}%",
            },
            {
                "check": "interactions_timestamp_field_coverage",
                "status": "PASS" if timestamp_coverage >= 90 else "WARN",
                "details": f"{timestamp_coverage}%",
            },
        ]
    )

    sampled_interaction_user_ids = {
        str(doc["user_id"])
        for doc in db.interactions.find({}, {"user_id": 1, "_id": 0}).limit(SAMPLE_SIZE)
        if "user_id" in doc
    }
    sampled_known_users = {
        str(doc["username"])
        for doc in db.users.find({"username": {"$in": list(sampled_interaction_user_ids)}}, {"username": 1, "_id": 0})
    }
    sample_orphans = len(sampled_interaction_user_ids - sampled_known_users)
    rows.append(
        {
            "check": "sampled_orphaned_interactions",
            "status": "PASS" if sample_orphans == 0 else "WARN",
            "details": f"sampled_user_ids={len(sampled_interaction_user_ids)}, unmatched_sampled_user_ids={sample_orphans}",
        }
    )

    return rows


def run_live_query_benchmarks(db):
    first_user = safe_first(db.users, {"_id": 0, "username": 1, "email": 1})
    first_book = safe_first(db.books, {"_id": 0, "book_id": 1})
    first_interaction = safe_first(db.interactions, {"_id": 0, "user_id": 1})

    username = first_user.get("username") if first_user else None
    email = first_user.get("email") if first_user else None
    book_id = first_book.get("book_id") if first_book else None
    interaction_user = first_interaction.get("user_id") if first_interaction else None

    rows = []

    if username is not None:
        rows.append(
            benchmark_query(
                "find_user_by_username_live",
                lambda: db.users.find_one({"username": username}),
                lambda: db.users.find({"username": username}).explain(),
                "direct login-style lookup on the live users collection",
            )
        )

    if email is not None:
        rows.append(
            benchmark_query(
                "find_user_by_email_live",
                lambda: db.users.find_one({"email": email}),
                lambda: db.users.find({"email": email}).explain(),
                "password-reset style lookup on the live users collection",
            )
        )
    else:
        rows.append(
            {
                "query": "find_user_by_email_live",
                "avg_ms": 0.0,
                "p95_ms": 0.0,
                "max_ms": 0.0,
                "results_returned": 0,
                "winning_plan": "SCHEMA_GAP",
                "note": "email field is absent in the live users collection",
            }
        )

    if book_id is not None:
        rows.append(
            benchmark_query(
                "find_book_by_book_id_live",
                lambda: db.books.find_one({"book_id": book_id}),
                lambda: db.books.find({"book_id": book_id}).explain(),
                "product-detail lookup on the live books collection",
            )
        )

    category_count = db.books.count_documents({"category": {"$exists": True, "$nin": [None, ""]}})
    if category_count:
        sample_category = db.books.find_one({"category": {"$exists": True, "$nin": [None, ""]}}, {"category": 1})["category"]
        rows.append(
            benchmark_query(
                "find_books_by_category_live",
                lambda: list(db.books.find({"category": sample_category}).limit(20)),
                lambda: db.books.find({"category": sample_category}).explain(),
                "catalog category filtering on the live books collection",
            )
        )
    else:
        rows.append(
            {
                "query": "find_books_by_category_live",
                "avg_ms": 0.0,
                "p95_ms": 0.0,
                "max_ms": 0.0,
                "results_returned": 0,
                "winning_plan": "SCHEMA_GAP",
                "note": "category field is absent in the live books collection",
            }
        )

    if interaction_user is not None:
        rows.append(
            benchmark_query(
                "find_interactions_by_user_live",
                lambda: list(db.interactions.find({"user_id": interaction_user}).limit(50)),
                lambda: db.interactions.find({"user_id": interaction_user}).limit(50).explain(),
                "history/profile lookup on the live interactions collection",
            )
        )

    rows.append(
        benchmark_query(
            "text_search_books_live",
            lambda: list(db.books.find({"$text": {"$search": "Hunger Games"}}).limit(10)),
            lambda: db.books.find({"$text": {"$search": "Hunger Games"}}).limit(10).explain(),
            "text-index-backed live catalog search",
        )
    )

    rows.append(
        benchmark_query(
            "get_popular_books_live",
            lambda: get_popular_books(db, limit=10),
            lambda: db.books.find(
                {"average_rating": {"$exists": True, "$ne": None}, "ratings_count": {"$exists": True, "$gte": 100}}
            )
            .sort([("average_rating", -1), ("ratings_count", -1)])
            .limit(10)
            .explain(),
            "sorted popularity query used by fallback and recommendation flows",
        )
    )

    return rows


def run_live_index_audit(db):
    expected = [
        ("books", "title_text_authors_text", "MEDIUM", "Supports $text search in the live catalog"),
        ("books", "book_id_1", "HIGH", "Product page book lookup"),
        ("books", "category_1", "MEDIUM", "Category filtering"),
        ("users", "username_1", "CRITICAL", "Login and user lookup"),
        ("users", "email_1", "CRITICAL", "Password reset and account recovery"),
        ("interactions", "user_id_1", "HIGH", "Profile/history lookup"),
        ("interactions", "book_id_1", "HIGH", "Book interaction aggregation"),
        ("interactions", "user_id_1_book_id_1", "HIGH", "Repeated interaction and deduplication checks"),
    ]
    rows = []
    for collection_name, index_name, priority, rationale in expected:
        indexes = getattr(db, collection_name).index_information()
        rows.append(
            {
                "collection": collection_name,
                "index_name": index_name,
                "priority": priority,
                "present": "yes" if index_name in indexes else "no",
                "rationale": rationale,
            }
        )
    return rows


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    db = client[DB_NAME]

    integrity_rows = run_integrity_and_schema_checks(db)
    query_rows = run_live_query_benchmarks(db)
    index_rows = run_live_index_audit(db)

    integrity_path = EVIDENCE_DIR / "database_live_integrity_results.csv"
    query_path = EVIDENCE_DIR / "database_live_query_results.csv"
    index_path = EVIDENCE_DIR / "database_live_index_results.csv"
    json_path = EVIDENCE_DIR / "database_live_results.json"
    log_path = EVIDENCE_DIR / "database_live_run.txt"

    write_csv(integrity_path, integrity_rows)
    write_csv(query_path, query_rows)
    write_csv(index_path, index_rows)

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mongo_uri": MONGO_URI,
        "database": DB_NAME,
        "integrity": integrity_rows,
        "queries": query_rows,
        "indexes": index_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    slowest_query = max(query_rows, key=lambda row: row["avg_ms"])
    missing_indexes = sum(1 for row in index_rows if row["present"] == "no")
    warning_checks = sum(1 for row in integrity_rows if row["status"] in {"WARN", "FAIL"})

    lines = [
        "GoodBooks live MongoDB experimental run",
        "",
        f"Database: {DB_NAME}",
        f"Integrity checks with warnings/failures: {warning_checks}/{len(integrity_rows)}",
        f"Missing expected indexes: {missing_indexes}",
        f"Slowest live query: {slowest_query['query']} ({slowest_query['avg_ms']} ms avg, plan={slowest_query['winning_plan']})",
        "",
        "Integrity + schema checks:",
    ]
    for row in integrity_rows:
        lines.append(f"- {row['check']}: {row['status']} ({row['details']})")
    lines.append("")
    lines.append("Live query benchmarks:")
    for row in query_rows:
        lines.append(
            f"- {row['query']}: avg={row['avg_ms']} ms p95={row['p95_ms']} ms plan={row['winning_plan']}"
        )
    lines.append("")
    lines.append("Live index audit:")
    for row in index_rows:
        lines.append(
            f"- {row['collection']}.{row['index_name']}: present={row['present']} priority={row['priority']}"
        )
    log_path.write_text("\n".join(lines), encoding="utf-8")

    print("Live database experiment complete")
    print(f"Integrity CSV: {integrity_path}")
    print(f"Query CSV: {query_path}")
    print(f"Index CSV: {index_path}")
    print(f"JSON: {json_path}")
    print(f"LOG: {log_path}")
    for row in query_rows:
        print(
            f"{row['query']} -> avg={row['avg_ms']} ms, p95={row['p95_ms']} ms, plan={row['winning_plan']}"
        )


if __name__ == "__main__":
    main()
