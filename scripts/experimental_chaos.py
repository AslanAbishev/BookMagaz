"""Controlled chaos and fault-injection experiments for GoodBooks."""
from __future__ import annotations

import csv
import json
import io
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import app as app_module
import recommend
from experimental_common import make_client, patched_app_environment


EVIDENCE_DIR = Path("docs/experimental_evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def execute_request(client, scenario):
    with redirect_stdout(io.StringIO()):
        if scenario == "search_api":
            return client.get("/api/search?q=code")
        if scenario == "recommend_api":
            return client.get("/api/recommend/u-1")
        if scenario == "product_page":
            return client.get("/product/1")
        if scenario == "profile_page":
            with client.session_transaction() as session:
                session["user_id"] = "64a000000000000000000001"
                session["username"] = "reader1"
            return client.get("/profile", follow_redirects=False)
        if scenario == "admin_rebuild":
            return client.get("/admin/rebuild-sim")
    raise ValueError(f"Unknown scenario: {scenario}")


def classify_response(response):
    return response.status_code < 500


def chaos_experiments():
    experiments = []
    with patched_app_environment():
        cases = [
            {
                "scenario": "search_api",
                "fault": "search backend raises RuntimeError",
                "patcher": lambda: patch.object(
                    app_module, "search_books", side_effect=RuntimeError("search backend failed")
                ),
            },
            {
                "scenario": "recommend_api",
                "fault": "recommendation engine raises RuntimeError",
                "patcher": lambda: patch.object(
                    app_module, "get_recommendations", side_effect=RuntimeError("engine unavailable")
                ),
            },
            {
                "scenario": "product_page",
                "fault": "book lookup raises RuntimeError",
                "patcher": lambda: patch.object(
                    app_module, "get_book", side_effect=RuntimeError("book store unavailable")
                ),
            },
            {
                "scenario": "profile_page",
                "fault": "user profile missing during active session",
                "patcher": lambda: patch.object(app_module, "get_user_by_id", return_value=None),
            },
            {
                "scenario": "admin_rebuild",
                "fault": "similarity rebuild raises RuntimeError",
                "patcher": lambda: patch.object(
                    recommend, "build_item_similarity", side_effect=RuntimeError("cache disk full")
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
    csv_path = EVIDENCE_DIR / "chaos_results.csv"
    json_path = EVIDENCE_DIR / "chaos_results.json"
    log_path = EVIDENCE_DIR / "chaos_run.txt"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)

    lines = ["GoodBooks chaos experiment run", ""]
    for row in rows:
        lines.append(
            f"{row['scenario']}: fault={row['fault_status_code']} "
            f"graceful={row['graceful_degradation']} "
            f"recovery={row['recovery_status_code']} in {row['recovery_time_ms']}ms"
        )
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, json_path, log_path


def main():
    rows = chaos_experiments()
    csv_path, json_path, log_path = write_outputs(rows)
    print("Chaos experiment complete")
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
