"""Deterministic performance experiment runner for GoodBooks."""
from __future__ import annotations

import csv
import json
import math
import io
import sys
import statistics
import time
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from experimental_common import make_client, patched_app_environment


EVIDENCE_DIR = Path("docs/experimental_evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

LOAD_LEVELS = {
    "expected": 20,
    "stress": 75,
    "extreme": 150,
}


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


def call_endpoint(client, scenario_name):
    with redirect_stdout(io.StringIO()):
        if scenario_name == "home_page":
            return client.get("/")
        if scenario_name == "search_api":
            return client.get("/api/search?q=code&limit=10")
        if scenario_name == "recommend_api":
            return client.get("/api/recommend/u-1")
        if scenario_name == "product_page":
            return client.get("/product/1")
        if scenario_name == "profile_page":
            with client.session_transaction() as session:
                session["user_id"] = "64a000000000000000000001"
                session["username"] = "reader1"
            return client.get("/profile")
    raise ValueError(f"Unknown scenario: {scenario_name}")


def run_performance_suite():
    rows = []
    started_at = datetime.now().isoformat(timespec="seconds")
    with patched_app_environment():
        scenarios = [
            "home_page",
            "search_api",
            "recommend_api",
            "product_page",
            "profile_page",
        ]
        for scenario_name in scenarios:
            for load_name, iterations in LOAD_LEVELS.items():
                timings = []
                errors = 0
                started = time.perf_counter()
                for _ in range(iterations):
                    client = make_client()
                    request_started = time.perf_counter()
                    response = call_endpoint(client, scenario_name)
                    elapsed_ms = (time.perf_counter() - request_started) * 1000
                    timings.append(elapsed_ms)
                    if response.status_code >= 500:
                        errors += 1
                duration_s = time.perf_counter() - started
                rows.append(
                    {
                        "timestamp": started_at,
                        "scenario": scenario_name,
                        "load_level": load_name,
                        "requests": iterations,
                        "avg_ms": round(statistics.mean(timings), 2),
                        "p95_ms": round(percentile(timings, 0.95), 2),
                        "max_ms": round(max(timings), 2),
                        "throughput_rps": round(iterations / duration_s, 2),
                        "errors": errors,
                        "error_rate_pct": round((errors / iterations) * 100, 2),
                    }
                )
    return rows


def write_outputs(rows):
    csv_path = EVIDENCE_DIR / "performance_results.csv"
    json_path = EVIDENCE_DIR / "performance_results.json"
    log_path = EVIDENCE_DIR / "performance_run.txt"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)

    lines = ["GoodBooks experimental performance run", ""]
    for row in rows:
        lines.append(
            f"{row['scenario']} [{row['load_level']}]: "
            f"avg={row['avg_ms']}ms p95={row['p95_ms']}ms "
            f"throughput={row['throughput_rps']} rps errors={row['errors']}"
        )
    log_path.write_text("\n".join(lines), encoding="utf-8")

    return csv_path, json_path, log_path


def main():
    rows = run_performance_suite()
    csv_path, json_path, log_path = write_outputs(rows)
    print("Performance experiment complete")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"LOG: {log_path}")
    for row in rows:
        print(
            f"{row['scenario']} [{row['load_level']}] -> "
            f"avg={row['avg_ms']}ms, p95={row['p95_ms']}ms, "
            f"throughput={row['throughput_rps']} rps, errors={row['errors']}"
        )


if __name__ == "__main__":
    main()
