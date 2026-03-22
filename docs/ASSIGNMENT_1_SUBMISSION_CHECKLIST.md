# Assignment 1 – Submission Checklist

Use this checklist when submitting Assignment 1.

---

## Deliverables

| # | Deliverable | File/Location | Status |
|---|-------------|---------------|--------|
| 1 | Risk Assessment Document | `docs/RISK_ASSESSMENT.md` or Section 2 of `docs/ASSIGNMENT_1_REPORT.md` | ✓ |
| 2 | QA Test Strategy Document | `docs/TEST_STRATEGY.md` or Section 3 of `docs/ASSIGNMENT_1_REPORT.md` | ✓ |
| 3 | QA Environment Setup Report | Section 4 of `docs/ASSIGNMENT_1_REPORT.md` | ✓ |
| 4 | Baseline Metrics & Screenshots | Section 5 of `docs/ASSIGNMENT_1_REPORT.md` | ✓ |

---

## Screenshots to Capture

1. **Test execution** – Run `.\run_tests.ps1` and screenshot the output showing "34 passed, 1 skipped".
2. **CI/CD pipeline** – GitHub Actions workflow run (if pushed to GitHub).
3. **Postman** – API collection imported and a successful request.
4. **Repository structure** – Folder view showing `tests/`, `docs/`, `postman/`, `jmeter/`, `.github/`.

---

## Quick Commands

```powershell
# Run all tests
.\run_tests.ps1

# Run with verbose output
python -m pytest tests/ -v --ignore=tests/e2e
```

---

## Main Report

The full report is in: **`docs/ASSIGNMENT_1_REPORT.md`**

It includes all four deliverables and the connection to the final research paper.
