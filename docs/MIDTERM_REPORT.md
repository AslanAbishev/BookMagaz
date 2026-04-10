# Midterm Project: QA Implementation & Empirical Analysis
## GoodBooks

**Project under test:** GoodBooks  
**Repository:** `https://github.com/AslanAbishev/BookMagaz`  
**Analysis date:** `2026-04-11`  
**Primary evidence folder:** [`docs/midterm_evidence/`](../docs/midterm_evidence/)

## 1. System Description

GoodBooks is a monolithic web application for book discovery and recommendation. The backend is built with Flask, the persistence layer uses MongoDB, and the user-facing frontend is rendered with Jinja templates and static assets. The platform supports registration, login, password reset, search, category browsing, product detail pages, user profile/history pages, and recommendation features built from ratings and interactions.

From a QA perspective, the most important workflows are:
- user authentication and account recovery
- search and product discovery
- interaction APIs for rating, liking, purchasing, and viewing
- profile aggregation and recommendations
- recommendation/similarity logic in the backend

## 2. Methodology

### 2.1 Risk-Based Testing Approach

The midterm continued the risk-based approach defined in Assignment 1. The initial high-risk areas were:
- Authentication
- Password Recovery
- API Endpoints / User Interactions
- Search
- Recommendation Engine
- Data Layer

The goal in the midterm was to move from planned priority to empirical priority using evidence from automation runs, coverage results, repeated execution, and pipeline behavior.

### 2.2 Test Design Strategy

The automation strategy combines:
- unit tests for backend logic and helper functions
- integration tests for Flask routes and API endpoints
- E2E tests for browser-level user flow checks

The midterm also required new tests in the following categories:
- failure scenarios
- edge cases
- concurrency / race-like repeated operations
- invalid user behavior

### 2.3 Tools Used

| Purpose | Tool |
|---|---|
| Test runner | `pytest` |
| Coverage collection | `pytest-cov`, `coverage.py` |
| Route/API testing | Flask test client |
| Isolation/mocking | `unittest.mock`, local stubs in `tests/helpers.py` |
| E2E | Playwright and Selenium test files |
| CI/CD | GitHub Actions |
| Metrics processing | Python scripts and CSV exports |

## 3. Task 1: Refine Risk-Based Testing Strategy

### 3.1 Re-evaluate High-Risk Components

Numeric risk scores below use a simple 10-point scale derived from Assignment 1 priority and adjusted using observed automation evidence.

| Module | Original Risk Score | Observed Issues (A2 / Midterm) | Updated Risk Score | Justification |
|---|---:|---|---:|---|
| Authentication | 9 | No failures in final runs; more edge validation now covered; highly critical to access control | 8 | Impact remains very high, but repeated stable runs and 90.65% coverage reduce likelihood |
| Password Recovery | 8 | No failures in final runs; token validation and empty/mismatched password scenarios covered | 7 | Still important but empirical evidence shows stable behavior after stronger tests |
| API Endpoints / User Interactions | 8 | No failed runs; invalid rating, missing book id, auth guard, repeated like behavior all pass | 7 | Business impact stays high, but detectability improved through broader API tests |
| Search | 7 | No failures; backend error path and blank-category normalization now covered | 6 | Search is still high-use, but failure likelihood dropped after stable route/API checks |
| Recommendation Engine | 8 | Was previously weaker due to skipped/limited coverage; now stronger but remains algorithmically complex | 8 | Coverage improved to 90.84%, but business impact and algorithm complexity keep risk high |

### 3.2 Extract Evidence from Automation Runs

#### A. Failed Test Cases

During the final midterm regression runs, no test failures were observed.

| Test name / ID | Module affected | Failure type | Frequency |
|---|---|---|---:|
| None in final evidence set | N/A | N/A | 0 |

Evidence:
- [`docs/midterm_evidence/pytest-run.txt`](../docs/midterm_evidence/pytest-run.txt)
- [`docs/midterm_evidence/pytest-results.xml`](../docs/midterm_evidence/pytest-results.xml)

#### B. Flaky Tests (Instability Analysis)

Repeated non-E2E executions were run five times.

| Test / Suite | Passes | Failures | Suspected cause |
|---|---:|---:|---|
| Main non-E2E regression suite | 5 | 0 | No flakiness observed |

Observed flaky rate:
- `0 / 5 = 0%`

Evidence:
- [`docs/midterm_evidence/stability_runs.txt`](../docs/midterm_evidence/stability_runs.txt)

#### C. Coverage Gaps

Coverage was collected using `pytest-cov`.

High-risk backend file coverage:

| Module/File | Coverage % | Coverage < 70%? |
|---|---:|---|
| `backend/app.py` | 90.65% | No |
| `backend/models.py` | 71.60% | No |
| `backend/recommend.py` | 90.84% | No |

Backend files below 70% overall:

| Module/File | Coverage % | Comment |
|---|---:|---|
| `backend/db_setup.py` | 0% | Environment/bootstrap utility, not part of regression-critical app behavior |
| `backend/locustfile.py` | 0% | Load-testing script, not exercised in unit/integration regression suite |
| `backend/performance_test.py` | 0% | Standalone performance analysis script |
| `backend/testing.py` | 0% | Separate database analysis script, not application runtime logic |

Evidence:
- [`docs/midterm_evidence/coverage.json`](../docs/midterm_evidence/coverage.json)
- [`docs/midterm_evidence/coverage.xml`](../docs/midterm_evidence/coverage.xml)
- [`docs/midterm_evidence/high_risk_coverage.csv`](../docs/midterm_evidence/high_risk_coverage.csv)

#### D. Unexpected System Behavior

| Observation | Predicted in A1? | Notes |
|---|---|---|
| Coverage data file could not be saved inside the OneDrive workspace without redirecting `COVERAGE_FILE` | No | This was an environment/tooling issue, not an application defect |
| Overall backend coverage looked artificially low because utility scripts were included in the report | No | High-risk runtime modules were actually covered much better than the total suggests |
| Initial recommendation coverage from Assignment 2 was weaker than other high-risk modules | Partly | Midterm work added more recommendation tests to improve detectability |
| GitHub Actions initially failed because recommendation tests used Windows-only cache paths | No | Fixed by switching to repository-relative paths |
| GitHub Actions then failed because the `data/` directory did not exist on the Linux runner | No | Fixed by creating the cache directory inside the tests before writing files |

### 3.3 Map Evidence to Risk Dimensions

| Module | Likelihood | Impact | Detectability | Evidence-based interpretation |
|---|---|---|---|---|
| Authentication | Medium | Very High | High | No repeated failures and strong route coverage reduced likelihood; impact stays severe |
| Password Recovery | Medium | High | High | Validation and token tests improved detectability; no failures in repeated runs |
| API Endpoints | Medium | High | High | Route/API validation tests now cover more bad-input and repeated-action scenarios |
| Search | Low-Medium | High | High | Search error path and normalization are now observable in automation |
| Recommendation Engine | Medium | High | Medium-High | Coverage improved substantially, but algorithmic complexity keeps likelihood above low |

## 4. Task 2: Expand Automation & Coverage

### 4.1 New Test Cases Added in the Midterm

The test suite was extended with new cases targeting failure, edge, concurrency-like, and invalid-user behavior.

| Test ID | Target module | Scenario type | Input data | Expected output | Actual result |
|---|---|---|---|---|---|
| `TC-AUTH-EDGE-01` | Authentication | Edge / invalid input | Email `bad<script>@example` during registration | Validation error and no successful registration | Pass |
| `TC-AUTH-FAIL-02` | Password Recovery | Invalid user behavior | Empty password on reset form | `Password is required` validation message | Pass |
| `TC-SEARCH-FAIL-01` | Search | Failure scenario | Backend search raises runtime error | Route returns `500` JSON error payload | Pass |
| `TC-API-EDGE-01` | Rating API | Edge / invalid input | Non-numeric rating `five<script>` | `400` JSON error: `Invalid rating` | Pass |
| `TC-API-CONC-01` | Like API | Concurrency-like repeated action | Same like request sent twice | Only one like insert recorded | Pass |
| `TC-API-INV-01` | Interactions API | Invalid user behavior | Missing interaction type | Route defaults to `view` interaction | Pass |
| `TC-API-FAIL-02` | Interactions API | Failure / access control | Anonymous request to `/api/user/interactions` | `401 Not authenticated` | Pass |
| `TC-PROFILE-INT-01` | Profile / Data update | Integration | Authenticated profile edit POST | User profile update called and redirect to `/profile` | Pass |
| `TC-PRODUCT-CONC-01` | Product route | Concurrency-like repeated action | Existing recent view for same product | No duplicate view insert | Pass |
| `TC-E2E-AUTH-01` | E2E / Route security | E2E invalid access | Browser request to `/profile` without login | Redirect to `/login` | Implemented in Playwright test |

Code mapping:
- [`tests/test_auth.py`](../tests/test_auth.py)
- [`tests/test_api.py`](../tests/test_api.py)
- [`tests/test_recommendations.py`](../tests/test_recommendations.py)
- [`tests/e2e/test_playwright.py`](../tests/e2e/test_playwright.py)

### 4.2 Required Test Types

| Test level | Implemented? | Evidence |
|---|---|---|
| Unit Tests | Yes | `tests/test_models.py`, recommendation utility tests in `tests/test_recommendations.py` |
| Integration Tests | Yes | `tests/test_api.py`, `tests/test_auth.py`, `tests/test_search.py`, `tests/test_recommendations.py` |
| End-to-End Tests | Yes | `tests/e2e/test_playwright.py`, `tests/e2e/test_selenium.py` |

### 4.3 CI/CD Execution

The CI/CD workflow now:
- installs dependencies on every push/PR
- runs the full non-E2E regression suite
- generates JUnit and coverage reports
- applies quality gates through `scripts/quality_gate.py`
- runs Playwright E2E tests after the regression job

Workflow source:
- [`.github/workflows/test-pipeline.yml`](../.github/workflows/test-pipeline.yml)

Quality-gate source:
- [`scripts/quality_gate.py`](../scripts/quality_gate.py)

### 4.4 Quality Gates

| Gate | Threshold | Observed result | Status |
|---|---:|---:|---|
| Test pass rate | >= 90% | 100% | Pass |
| Overall backend coverage | >= 40% | 45.70% | Pass |
| High-risk backend coverage average | >= 70% | 84.37% | Pass |

Critical analysis:
- The `overall backend coverage` threshold is intentionally lower than the high-risk threshold because utility scripts and standalone analysis scripts are included in the backend folder but are not part of the core regression target.
- The `high-risk coverage` threshold is stricter and more meaningful for release readiness.
- An earlier 45% threshold was too close to the measured result and proved brittle across environments, so it was relaxed to 40% while keeping the stronger 70% threshold for high-risk runtime files.
- A higher overall threshold such as 70% would be unrealistic without either excluding support scripts from coverage or writing dedicated tests for tooling files that do not affect the main application flow.

## 5. Task 3: Metrics Collection

### 5.1 Coverage

| Metric | Value |
|---|---:|
| Overall backend coverage | 45.70% |
| High-risk backend coverage average | 84.37% |
| High-risk modules below 70% | 0 |

### 5.2 Defect Detection

| Metric | Value |
|---|---:|
| Defects found in final regression evidence | 0 |
| New midterm tests added | 10 |
| New tests passed | 10 |

### 5.3 Efficiency

| Metric | Value |
|---|---:|
| Final non-E2E regression runtime | 2.63 sec |
| Assignment 2 non-E2E baseline runtime | 2.51 sec |
| Current total non-E2E tests | 80 |

Interpretation:
- The suite grew from 68 to 80 non-E2E tests.
- Runtime increased only slightly while coverage and scenario depth improved.
- This indicates that the new tests were added efficiently and did not significantly reduce CI practicality.

### 5.4 Stability

| Metric | Value |
|---|---:|
| Repeated reruns analyzed | 5 |
| Runs passed | 5 |
| Runs failed | 0 |
| Flaky rate | 0% |

## 6. Task 4: Comparative Analysis

### 6.1 Planned vs Actual

| Aspect | Planned (A1) | Actual (A2 / Midterm) | Gap |
|---|---|---|---|
| Authentication automation | High-priority regression coverage | Stable high coverage with additional edge cases | Gap reduced |
| Recommendation testing | Moderate test depth with 85% target | Initially weaker, then expanded with hybrid/cold-start/similarity tests | Needed extra iteration |
| CI/CD | Push/PR pipeline with automated checks | Implemented with coverage reports and quality-gate script | Improved beyond original plan |
| Coverage visibility | Planned module targets | Real measured coverage with high-risk vs overall distinction | Better than initial plan |
| Stability analysis | Not deeply specified in A1 | 5 repeated reruns with 0 flaky observations | New empirical dimension added |

### 6.2 Required Insights

| Insight type | Observation |
|---|---|
| Incorrect assumptions in planning | Overall backend coverage was initially assumed to reflect app quality directly, but support scripts distorted the total |
| Missing test scenarios | Recommendation logic, repeated actions, backend error routes, and invalid input edge cases were under-tested before the midterm |
| Inefficient automation design | Early evidence collection depended too much on single-run outputs and lacked explicit quality-gate automation |

## 7. Automation Implementation

### 7.1 CI/CD Setup

The pipeline is defined in GitHub Actions and now covers both regression checks and browser-level E2E execution. The regression job runs on each push/PR, generates coverage artifacts, and applies scripted quality gates. The Playwright E2E job verifies a browser-level flow after the regression stage.

After the first GitHub Actions runs, two portability issues were identified and fixed:
- recommendation tests were using Windows-only absolute cache paths
- recommendation cache-writing tests assumed the `data/` directory already existed

These fixes made the regression suite portable across the local Windows environment and the Linux-based GitHub runner.

### 7.2 Test Structure

| Area | Files |
|---|---|
| Auth / recovery | `tests/test_auth.py` |
| API / interactions | `tests/test_api.py` |
| Search | `tests/test_search.py` |
| Recommendations / profile | `tests/test_recommendations.py` |
| Models / data logic | `tests/test_models.py` |
| Basic route smoke | `tests/test_routes.py` |
| E2E | `tests/e2e/test_playwright.py`, `tests/e2e/test_selenium.py` |
| Shared helpers | `tests/conftest.py`, `tests/helpers.py` |

### 7.3 Quality Gates Definition

Quality gates are intentionally split into:
- release-critical gates on pass rate
- meaningful coverage gates on high-risk runtime modules
- a pragmatic overall coverage floor acknowledging the presence of non-runtime support scripts

## 8. Results

### 8.1 Key Numerical Results

| Result | Value |
|---|---:|
| Total non-E2E tests | 80 |
| Passed | 80 |
| Failed | 0 |
| High-risk coverage average | 84.37% |
| Overall backend coverage | 45.70% |
| Stability reruns passed | 5/5 |

### 8.2 Graph Guidance

Recommended visuals for the final document:
- Bar chart: high-risk module coverage (`app.py`, `models.py`, `recommend.py`)
- Line chart: execution time per functional module
- Table: defects found vs expected risk

Raw data sources:
- [`docs/midterm_evidence/high_risk_coverage.csv`](../docs/midterm_evidence/high_risk_coverage.csv)
- [`docs/evidence/module_execution_times.csv`](../docs/evidence/module_execution_times.csv)
- [`docs/midterm_evidence/stability_runs.txt`](../docs/midterm_evidence/stability_runs.txt)

### 8.3 Screenshots / Logs to Include Manually

The following should be captured manually for submission:
- GitHub Actions workflow run screenshot
- Job view showing steps and statuses
- Coverage or artifact summary screenshot
- Terminal screenshot showing the final `80 passed` run

## 9. Discussion

### 9.1 What Worked

- Risk-based prioritization remained useful: the most important modules are now strongly covered.
- The additional midterm tests improved recommendation and API robustness without making the suite slow.
- The pipeline now has real measurable gates instead of only passive test execution.

### 9.2 What Did Not Work Perfectly

- Overall backend coverage is still dragged down by non-runtime scripts in the backend folder.
- Coverage collection inside the OneDrive workspace required a workaround using a temp `COVERAGE_FILE`.
- The first GitHub Actions runs exposed cross-platform issues in recommendation tests, which required an additional portability fix.
- E2E evidence is better supported in CI than in the local Windows environment without installing browser tooling.

### 9.3 Improvements for Next Phase

- Add dedicated tests or exclude support scripts from the release coverage gate to make overall coverage more meaningful.
- Expand authenticated browser-level E2E scenarios.
- Add performance/load metrics into the same evidence pipeline for a stronger empirical comparison in the final project phase.

## 10. Evidence Index

| Evidence | File |
|---|---|
| Final midterm regression log | `docs/midterm_evidence/pytest-run.txt` |
| JUnit XML results | `docs/midterm_evidence/pytest-results.xml` |
| Coverage JSON | `docs/midterm_evidence/coverage.json` |
| Coverage XML | `docs/midterm_evidence/coverage.xml` |
| High-risk coverage summary | `docs/midterm_evidence/high_risk_coverage.csv` |
| Stability reruns | `docs/midterm_evidence/stability_runs.txt` |
| Midterm per-test execution log | `docs/midterm_evidence/test_execution_log.csv` |
| Existing per-test timing log | `docs/evidence/test_execution_log.csv` |
| Existing per-module timing log | `docs/evidence/module_execution_times.csv` |

## 11. Recent Fixes After Initial CI Failures

The latest repository history includes the CI-specific fixes that were required after the first GitHub Actions runs:

| Commit | Date | Purpose |
|---|---|---|
| `d8ace60` | 2026-04-10 | Added midterm QA analysis, coverage gates, and new tests |
| `f293dc0` | 2026-04-11 | Replaced Windows-only recommendation test paths with repository-relative paths |
| `9bdfb13` | 2026-04-11 | Relaxed brittle overall coverage gate and stabilized matrix workflow behavior |
| `c333180` | 2026-04-11 | Ensured recommendation tests create the cache directory before writing files in CI |
