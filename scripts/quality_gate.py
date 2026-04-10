"""
Evaluate simple quality gates for the GoodBooks midterm pipeline.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "midterm_evidence"
COVERAGE_JSON = EVIDENCE_DIR / "coverage.json"
PYTEST_XML = EVIDENCE_DIR / "pytest-results.xml"

PASS_RATE_THRESHOLD = 0.90
OVERALL_COVERAGE_THRESHOLD = 0.45
HIGH_RISK_COVERAGE_THRESHOLD = 0.70
HIGH_RISK_FILES = {
    "backend\\app.py",
    "backend\\models.py",
    "backend\\recommend.py",
}


def load_junit_metrics(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    tests = 0
    failures = 0
    for suite in root.iter("testsuite"):
        tests += int(suite.attrib.get("tests", 0))
        failures += int(suite.attrib.get("failures", 0)) + int(suite.attrib.get("errors", 0))
    return tests, failures


def load_coverage_metrics(path: Path) -> tuple[float, dict[str, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    totals = payload["totals"]
    overall = totals["percent_covered"] / 100.0
    file_coverages = {}
    for file_name, file_data in payload["files"].items():
        normalized = file_name.replace("/", "\\")
        file_coverages[normalized] = file_data["summary"]["percent_covered"] / 100.0
    return overall, file_coverages


def main() -> int:
    tests, failures = load_junit_metrics(PYTEST_XML)
    overall_coverage, file_coverages = load_coverage_metrics(COVERAGE_JSON)
    pass_rate = 0.0 if tests == 0 else (tests - failures) / tests
    high_risk_values = [file_coverages[path] for path in HIGH_RISK_FILES if path in file_coverages]
    high_risk_average = sum(high_risk_values) / len(high_risk_values) if high_risk_values else 0.0

    print("Quality Gate Evaluation")
    print(f"Pass rate: {pass_rate:.2%} (threshold {PASS_RATE_THRESHOLD:.0%})")
    print(f"Overall backend coverage: {overall_coverage:.2%} (threshold {OVERALL_COVERAGE_THRESHOLD:.0%})")
    print(f"High-risk file coverage average: {high_risk_average:.2%} (threshold {HIGH_RISK_COVERAGE_THRESHOLD:.0%})")

    failed = []
    if pass_rate < PASS_RATE_THRESHOLD:
        failed.append("pass rate")
    if overall_coverage < OVERALL_COVERAGE_THRESHOLD:
        failed.append("overall coverage")
    if high_risk_average < HIGH_RISK_COVERAGE_THRESHOLD:
        failed.append("high-risk coverage")

    if failed:
        print(f"FAILED quality gates: {', '.join(failed)}")
        return 1

    print("All quality gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
