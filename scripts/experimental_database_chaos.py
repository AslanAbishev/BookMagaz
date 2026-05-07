"""Database-specific chaos and fault-injection experiments for GoodBooks."""
from __future__ import annotations

import csv
import io
import json
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import app as app_module
from experimental_common import make_client, patched_app_environment


EVIDENCE_DIR = Path("docs/experimental_evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def execute_request(client, scenario):
    with redirect_stdout(io.StringIO()):
        if scenario == "home_page_books_query_failure":
            return client.get("/")
        if scenario == "categories_api_distinct_failure":
            return client.get("/api/categories")
        if scenario == "search_api_books_find_failure":
            return client.get("/api/search?q=code")
        if scenario == "user_interactions_query_failure":
            with client.session_transaction() as session:
                session["user_id"] = "u-1"
                session["username"] = "reader1"
            return client.get("/api/user/interactions")
        if scenario == "login_user_lookup_failure":
            return client.post(
                "/login",
                data={"username": "reader1", "password": "hashed-password"},
                follow_redirects=False,
            )
        if scenario == "admin_rebuild_count_failure":
            return client.get("/admin/rebuild-sim")
    raise ValueError(f"Unknown scenario: {scenario}")


def classify_response(response):
    return response.status_code < 500


def database_chaos_experiments():
    experiments = []
    with patched_app_environment():
        cases = [
            {
                "scenario": "home_page_books_query_failure",
                "fault": "db.books.find raises AutoReconnect during home page render",
                "patcher": lambda: patch.object(
                    app_module.db.books,
                    "find",
                    side_effect=AutoReconnect("books collection unavailable"),
                ),
            },
            {
                "scenario": "categories_api_distinct_failure",
                "fault": "db.books.distinct raises ServerSelectionTimeoutError",
                "patcher": lambda: patch.object(
                    app_module.db.books,
                    "distinct",
                    side_effect=ServerSelectionTimeoutError("category index node unavailable"),
                ),
            },
            {
                "scenario": "search_api_books_find_failure",
                "fault": "db.books.find raises AutoReconnect inside search fallback",
                "patcher": lambda: patch.object(
                    app_module.db.books,
                    "find",
                    side_effect=AutoReconnect("search collection unavailable"),
                ),
            },
            {
                "scenario": "user_interactions_query_failure",
                "fault": "db.interactions.find raises AutoReconnect during history lookup",
                "patcher": lambda: patch.object(
                    app_module.db.interactions,
                    "find",
                    side_effect=AutoReconnect("interaction history unavailable"),
                ),
            },
            {
                "scenario": "login_user_lookup_failure",
                "fault": "db.users.find_one raises ServerSelectionTimeoutError on login",
                "patcher": lambda: patch.object(
                    app_module.db.users,
                    "find_one",
                    side_effect=ServerSelectionTimeoutError("user lookup timed out"),
                ),
            },
            {
                "scenario": "admin_rebuild_count_failure",
                "fault": "db.interactions.count_documents raises AutoReconnect after rebuild",
                "patcher": lambda: patch.object(
                    app_module.db.interactions,
                    "count_documents",
                    side_effect=AutoReconnect("ratings count unavailable"),
                ),
            },
        ]

        for case in cases:
            with case["patcher"]():
                client = make_client()
                started = time.perf_counter()
                response = execute_request(client, case["scenario"])
                fault_duration_ms = (time.perf_counter() - started) * 1000
                graceful = classify_response(response)

            recovery_client = make_client()
            recovery_started = time.perf_counter()
            recovery_response = execute_request(recovery_client, case["scenario"])
            recovery_ms = (time.perf_counter() - recovery_started) * 1000

            experiments.append(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "scenario": case["scenario"],
                    "fault": case["fault"],
                    "fault_status_code": response.status_code,
                    "graceful_degradation": "yes" if graceful else "no",
                    "fault_duration_ms": round(fault_duration_ms, 2),
                    "recovery_status_code": recovery_response.status_code,
                    "recovery_time_ms": round(recovery_ms, 2),
                    "recovered_after_fault": "yes" if recovery_response.status_code < 500 else "no",
                }
            )
    return experiments


def write_outputs(rows):
    csv_path = EVIDENCE_DIR / "database_chaos_results.csv"
    json_path = EVIDENCE_DIR / "database_chaos_results.json"
    log_path = EVIDENCE_DIR / "database_chaos_run.txt"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)

    lines = ["GoodBooks database chaos experiment run", ""]
    for row in rows:
        lines.append(
            f"{row['scenario']}: fault={row['fault_status_code']} "
            f"graceful={row['graceful_degradation']} "
            f"recovery={row['recovery_status_code']} in {row['recovery_time_ms']}ms"
        )
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, json_path, log_path


def main():
    rows = database_chaos_experiments()
    csv_path, json_path, log_path = write_outputs(rows)
    print("Database chaos experiment complete")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"LOG: {log_path}")
    for row in rows:
        print(
            f"{row['scenario']} -> fault={row['fault_status_code']} "
            f"graceful={row['graceful_degradation']} recovery={row['recovery_status_code']}"
        )


if __name__ == "__main__":
    main()
