"""Small-scope mutation harness for GoodBooks."""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "experimental_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR = PROJECT_ROOT / ".tmp_experiments"
WORK_DIR.mkdir(exist_ok=True)


MUTANTS = [
    {
        "id": "M1",
        "module": "backend/models.py",
        "description": "Remove lowercase normalization when creating a user",
        "old": '"email": email.strip().lower(),  # Store email in lowercase',
        "new": '"email": email,',
        "tests": ["tests/test_models.py"],
    },
    {
        "id": "M2",
        "module": "backend/app.py",
        "description": "Weaken rating validation by replacing OR with AND",
        "old": "if rating < 1 or rating > 5:",
        "new": "if rating < 1 and rating > 5:",
        "tests": ["tests/test_api.py"],
    },
    {
        "id": "M3",
        "module": "backend/app.py",
        "description": "Invert duplicate-like guard",
        "old": '        if not check_user_interaction(db, user_id, book_id, "like"):',
        "new": '        if check_user_interaction(db, user_id, book_id, "like"):',
        "tests": ["tests/test_api.py"],
    },
    {
        "id": "M4",
        "module": "backend/recommend.py",
        "description": "Break cold-start recommendation branch",
        "old": "    if not ratings:",
        "new": "    if ratings:",
        "tests": [
            "tests/test_recommendations.py::TestRecommendationUtilities::test_get_recommendations_returns_popular_books_for_cold_start"
        ],
    },
    {
        "id": "M5",
        "module": "backend/recommend.py",
        "description": "Make similarity threshold unrealistically strict",
        "old": "                    if sim_value > 0.1:  # Only use meaningful similarities",
        "new": "                    if sim_value > 0.9:  # Only use meaningful similarities",
        "tests": [
            "tests/test_recommendations.py::TestRecommendationUtilities::test_get_similar_books_uses_cache_and_content_boosts"
        ],
    },
    {
        "id": "M6",
        "module": "backend/models.py",
        "description": "Disable category filter participation in search queries",
        "old": "    if category and category.strip():",
        "new": "    if False and category and category.strip():",
        "tests": ["tests/test_api.py", "tests/test_models.py"],
    },
]


def copy_subset(temp_root: Path):
    for name in ["backend", "tests", "data"]:
        source = PROJECT_ROOT / name
        destination = temp_root / name
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )
    for filename in ["pytest.ini", "requirements-test.txt"]:
        source = PROJECT_ROOT / filename
        if source.exists():
            shutil.copy2(source, temp_root / filename)


def mutate_file(root: Path, mutant):
    target = root / mutant["module"]
    text = target.read_text(encoding="utf-8")
    if mutant["old"] not in text:
        raise ValueError(f"Could not find target text for {mutant['id']}")
    target.write_text(text.replace(mutant["old"], mutant["new"], 1), encoding="utf-8")


def run_pytest(root: Path, tests: list[str]):
    env = os.environ.copy()
    env.setdefault("SECRET_KEY", "mutation-secret")
    env.setdefault(
        "MONGO_URI",
        "mongodb://localhost:27017/?serverSelectionTimeoutMS=100&connectTimeoutMS=100&socketTimeoutMS=100",
    )
    command = [sys.executable, "-m", "pytest", *tests, "-q"]
    result = subprocess.run(
        command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result


def run_mutation_experiments():
    results = []

    for mutant in MUTANTS:
        baseline_root = WORK_DIR / f"{mutant['id'].lower()}_baseline"
        if baseline_root.exists():
            shutil.rmtree(baseline_root, ignore_errors=True)
        try:
            copy_subset(baseline_root)
            baseline_result = run_pytest(baseline_root, mutant["tests"])
        finally:
            shutil.rmtree(baseline_root, ignore_errors=True)

        root = WORK_DIR / mutant["id"].lower()
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        try:
            copy_subset(root)
            mutate_file(root, mutant)
            outcome = run_pytest(root, mutant["tests"])
            if baseline_result.returncode != 0:
                status = "baseline_failed"
            else:
                status = "killed" if outcome.returncode != 0 else "survived"
            results.append(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "mutant_id": mutant["id"],
                    "module": mutant["module"],
                    "description": mutant["description"],
                    "tests_run": " ".join(mutant["tests"]),
                    "baseline_return_code": baseline_result.returncode,
                    "status": status,
                    "return_code": outcome.returncode,
                    "stdout_excerpt": outcome.stdout[-400:].replace("\n", " ").strip(),
                    "stderr_excerpt": outcome.stderr[-400:].replace("\n", " ").strip(),
                }
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)
    return results


def write_outputs(results):
    csv_path = EVIDENCE_DIR / "mutation_results.csv"
    json_path = EVIDENCE_DIR / "mutation_results.json"
    log_path = EVIDENCE_DIR / "mutation_run.txt"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump({"mutants": results}, handle, indent=2)

    killed = sum(1 for result in results if result["status"] == "killed")
    valid = sum(1 for result in results if result["status"] != "baseline_failed")
    score = round((killed / valid) * 100, 2) if valid else 0.0
    lines = [
        "GoodBooks mutation experiment run",
        f"Killed mutants: {killed}/{valid}",
        f"Mutation score: {score}%",
        "",
    ]
    for result in results:
        lines.append(f"{result['mutant_id']} {result['status']}: {result['description']}")
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, json_path, log_path, score


def main():
    results = run_mutation_experiments()
    csv_path, json_path, log_path, score = write_outputs(results)
    print("Mutation experiment complete")
    print(f"Mutation score: {score}%")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"LOG: {log_path}")
    for result in results:
        print(f"{result['mutant_id']} -> {result['status']} ({result['module']})")


if __name__ == "__main__":
    main()
