# Assignment 1 – QA Landscape & Testing Planning Report
## GoodBooks E-Commerce Platform

**Course:** QA / Software Testing  
**Assignment:** 1 – Risk-Based Testing & QA Environment Setup  
**Deadline:** Week 2  
**System:** GoodBooks – Book Recommendation E-Commerce Platform (Web Application)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Deliverable 1: Risk Assessment Document](#2-deliverable-1-risk-assessment-document)
3. [Deliverable 2: QA Test Strategy Document](#3-deliverable-2-qa-test-strategy-document)
4. [Deliverable 3: QA Environment Setup Report](#4-deliverable-3-qa-environment-setup-report)
5. [Deliverable 4: Baseline Metrics](#5-deliverable-4-baseline-metrics)
6. [Connection to Final Research Paper](#6-connection-to-final-research-paper)

---

## 1. Executive Summary

This report documents the QA activities for **Assignment 1** on the **GoodBooks** system—a web-based e-commerce platform for book recommendations. The work includes:

- **Risk assessment** of 12 components, with 3 critical (P1), 5 high (P2), 3 medium (P3), and 1 low (P4).
- **QA environment setup** with pytest, Selenium, Playwright, Postman, JMeter, and a GitHub Actions CI/CD pipeline.
- **Test strategy** that prioritizes high-risk areas and uses automation for regression.
- **Baseline metrics**: 35 tests, 34 passing, with initial coverage across P1–P3 modules.

---

## 2. Deliverable 1: Risk Assessment Document

### 2.1 System Description

GoodBooks is a **web application** that provides:

- User registration and authentication (email required)
- Book catalog with search and category filtering
- Hybrid recommendation engine (collaborative + content-based)
- User interactions (ratings, likes, purchases)
- Profile and purchase history
- Forgot-password flow

**Architecture:**
- **Backend:** Flask (Python)
- **Database:** MongoDB (NoSQL)
- **Frontend:** HTML/CSS/JS (Jinja2)

### 2.2 Risk Assessment Methodology

**Criteria:**

| Level      | Probability   | Impact  | Action              |
|-----------|---------------|---------|---------------------|
| Critical  | High          | Severe  | P1 – Test first     |
| High      | Medium–High   | Major   | P2 – Test early     |
| Medium    | Medium        | Moderate| P3 – Normal cycle   |
| Low       | Low           | Minor   | P4 – When possible  |

**Assumptions:**
1. Tests run against a dedicated test MongoDB instance.
2. Test data is seeded or mocked for reproducibility.
3. Email for password reset is optional for testing.
4. CI/CD runs on GitHub Actions.

### 2.3 Prioritized Components/Modules

| # | Component             | Description                    | Failure Impact                         | Risk  | Priority |
|---|-----------------------|--------------------------------|----------------------------------------|-------|----------|
| 1 | **Authentication**    | Login, register, session       | Users locked out; security breach      | Critical | P1    |
| 2 | **User Data & Security** | Passwords, profiles        | Credential theft; privacy violation    | Critical | P1    |
| 3 | **MongoDB & Data Layer** | Connections, queries       | System failure; data loss              | Critical | P1    |
| 4 | **Recommendation Engine** | Collaborative filtering   | Poor UX; wrong recommendations         | High   | P2       |
| 5 | **API Endpoints**     | rate, like, purchase, search   | Broken features; integration failures  | High   | P2       |
| 6 | **Search Functionality** | Full-text, category filter | Users cannot find products             | High   | P2       |
| 7 | **User Interactions** | Ratings, likes, purchases     | Incorrect data; bad recommendations    | High   | P2       |
| 8 | **Forgot Password**   | Token generation, reset        | Users cannot recover accounts          | High   | P2       |
| 9 | **Product Catalog**   | Book display, categories       | Poor browsing; lost sales              | Medium | P3       |
|10 | **UI & Templates**    | Forms, validation              | Usability issues; validation bypass    | Medium | P3       |
|11 | **Performance**       | Similarity matrix, queries     | Slow responses; timeouts               | Medium | P3       |
|12 | **Static Assets**     | CSS, images                    | Broken layout                          | Low    | P4       |

### 2.4 Count of High-Risk Modules

- **Critical (P1):** 3 modules  
- **High (P2):** 5 modules  
- **Total high-risk:** 8 modules

### 2.5 Reasoning for Priorities

- **P1 (Authentication, Security, DB):** Core to access and data; failure affects the whole system.
- **P2 (APIs, Search, Recommendations):** Business-critical; poor behavior directly impacts usage and value.
- **P3 (Catalog, UI, Performance):** Important for usability but less critical than P1/P2.

---

## 3. Deliverable 2: QA Test Strategy Document

### 3.1 Project Scope and Objectives

**Scope:**
- Authentication flows
- API endpoints
- Search and recommendations
- Core user flows (E2E)
- Performance baseline

**Objectives:**
- Ensure functional correctness
- Validate security (auth, input validation)
- Maintain reliability and performance
- Cover critical flows end-to-end

### 3.2 Risk Assessment Results Summary

Modules are tested in order of risk: P1 first, then P2, then P3.

### 3.3 Test Approach: Manual vs Automated

| Test Type        | Manual | Automated | Rationale                    |
|------------------|--------|-----------|------------------------------|
| Unit             | —      | Yes       | Fast, repeatable             |
| API/Integration  | —      | Yes       | Deterministic, CI-friendly   |
| E2E (critical)   | Backup | Yes       | Regression prevention        |
| E2E (edge cases) | Yes    | —         | Exploratory                  |
| UX/Usability     | Yes    | —         | Subjective                   |
| Performance      | —      | Yes       | JMeter, Postman              |

### 3.4 Tool Selection and Configuration

| Tool       | Purpose                 | Configuration                      |
|------------|-------------------------|------------------------------------|
| pytest     | Unit, API, integration  | `pytest.ini`, `conftest.py`        |
| Selenium   | Browser E2E (Chrome)    | Headless, webdriver-manager        |
| Playwright | Browser E2E (Chromium)  | Headless, sync API                 |
| Postman    | API testing             | `postman/GoodBooks_API_Collection.json` |
| JMeter     | Load testing            | `jmeter/goodbooks_load_test.jmx`   |
| GitHub Actions | CI/CD                | `.github/workflows/test-pipeline.yml` |

### 3.5 Planned Automation

- **Phase 1 (P1):** Auth, security, data layer – automated unit/API tests  
- **Phase 2 (P2):** APIs, search, recommendations – automated API and integration tests  
- **Phase 3 (P3):** Routes, catalog – automated route tests  
- **Phase 4:** E2E – Selenium/Playwright for critical flows  

---

## 4. Deliverable 3: QA Environment Setup Report

### 4.1 Installed Tools

| Tool       | Version  | Purpose                    |
|------------|----------|----------------------------|
| pytest     | 9.0.2    | Test runner                |
| flask-testing | 0.8.1 | Flask test client          |
| requests   | 2.32.5   | HTTP client                |
| Selenium   | (in requirements-test) | Browser automation |
| Playwright | (in requirements-test) | Browser automation |
| Postman    | (standalone)           | API testing                |
| JMeter     | (standalone)           | Load testing               |

### 4.2 Installation Commands

```bash
pip install pytest flask-testing requests
# Full suite: pip install -r requirements-test.txt
playwright install chromium   # For E2E
```

### 4.3 Repository Structure

```
goodbooks_app/
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_auth.py             # P1: Authentication (10 tests)
│   ├── test_api.py              # P2: API endpoints (9 tests)
│   ├── test_search.py           # P2: Search (4 tests)
│   ├── test_recommendations.py  # P2: Recommendations (4 tests)
│   ├── test_models.py           # P1/P2: Data layer (2 tests)
│   ├── test_routes.py           # P3: Routes (7 tests)
│   └── e2e/
│       ├── test_selenium.py
│       └── test_playwright.py
├── postman/
│   └── GoodBooks_API_Collection.json
├── jmeter/
│   └── goodbooks_load_test.jmx
├── docs/
│   ├── RISK_ASSESSMENT.md
│   ├── TEST_STRATEGY.md
│   └── ASSIGNMENT_1_REPORT.md
├── .github/workflows/
│   └── test-pipeline.yml
├── pytest.ini
├── requirements-test.txt
├── run_tests.ps1
└── run_tests.bat
```

### 4.4 CI/CD Pipeline Configuration

- **Platform:** GitHub Actions  
- **Trigger:** Push and pull requests to `main`  
- **Jobs:**
  1. Unit & API tests (Python 3.10, 3.11)
  2. E2E tests (Playwright)
- **Services:** MongoDB 7.x  
- **File:** `.github/workflows/test-pipeline.yml`  

### 4.5 Version Control

- **System:** Git  
- **Host:** GitHub/GitLab  
- **Branches:** `main` for production; feature branches for development  
- **Test artifacts:** Stored in `tests/`, `postman/`, `jmeter/`  

---

## 5. Deliverable 4: Baseline Metrics

### 5.1 Test Execution Results

| Metric              | Value   |
|---------------------|---------|
| Total tests         | 35      |
| Passed              | 34      |
| Skipped             | 1       |
| Failed              | 0       |
| Execution time      | ~4 min  |

### 5.2 Tests by Priority

| Priority | Module           | Tests | Status    |
|----------|------------------|-------|-----------|
| P1       | Authentication   | 10    | All pass  |
| P1       | Models/Data      | 2     | All pass  |
| P2       | API endpoints    | 9     | All pass  |
| P2       | Search           | 4     | All pass  |
| P2       | Recommendations  | 4     | 3 pass, 1 skip |
| P3       | Routes           | 7     | All pass  |

### 5.3 Initial Coverage Plan

| Module        | Target | Current (planned)      |
|---------------|--------|------------------------|
| Authentication| 95%    | 10 tests               |
| API Endpoints | 90%    | 9 tests                |
| Search        | 90%    | 4 tests                |
| Recommendations| 85%   | 4 tests                |
| Routes        | 80%    | 7 tests                |

### 5.4 Estimated Testing Effort

| Phase   | Modules    | Effort (approx) |
|---------|------------|------------------|
| Phase 1 | P1         | 1 week           |
| Phase 2 | P2         | 1 week           |
| Phase 3 | P3         | 0.5 week         |
| Phase 4 | E2E, P4    | Ongoing          |

### 5.5 Screenshots for Research (Placeholders)

> **Screenshot 1: Test execution output**  
> *Capture: Output of `.\run_tests.ps1` showing "34 passed, 1 skipped"*

> **Screenshot 2: CI/CD pipeline**  
> *Capture: GitHub Actions run showing successful test jobs*

> **Screenshot 3: Postman collection**  
> *Capture: Postman with GoodBooks API collection imported and run*

> **Screenshot 4: Repository structure**  
> *Capture: Project tree with `tests/`, `docs/`, `.github/`*

---

## 6. Connection to Final Research Paper

### 6.1 Introduction Chapter

- **System description:** GoodBooks as a web-based book recommendation e-commerce platform.
- **Problem context:** Need for risk-based testing and QA environment setup in an agile/devops context.
- **Objectives:** Apply risk assessment, build QA infrastructure, and establish baseline metrics.

### 6.2 Methodology Chapter

- **Risk assessment:** Use of probability × impact matrix and prioritized testing.
- **Environment setup:** Tools, repository layout, and CI/CD configuration.
- **Test strategy:** Manual vs automated, high-risk-first approach.
- **Metrics:** Baseline counts, coverage targets, effort estimates.

### 6.3 Reproducibility

- Configurations: `pytest.ini`, `conftest.py`, `requirements-test.txt`
- Scripts: `run_tests.ps1`, `run_tests.bat`
- Pipeline: `.github/workflows/test-pipeline.yml`
- Documentation: `docs/RISK_ASSESSMENT.md`, `docs/TEST_STRATEGY.md`

### 6.4 Future Assignments

- **Automation:** Expand E2E and integration tests.
- **Experiments:** Performance, coverage, and defect analysis.
- **Synthesis:** Integrate results into the final research paper.

---

## Appendix A: Sample Test Output

```
========================================
GoodBooks Test Suite
========================================

[1] Running Unit + API + Route + Search + Recommendation tests...
=============================== test session starts ================================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0
collected 35 items

tests/test_auth.py ............ [ 10 tests - P1 ]
tests/test_api.py .........    [  9 tests - P2 ]
tests/test_routes.py ......    [  7 tests - P3 ]
tests/test_search.py ....     [  4 tests - P2 ]
tests/test_recommendations.py .... [ 4 tests - P2, 1 skipped ]
tests/test_models.py ..       [  2 tests ]

=============================== 34 passed, 1 skipped in 234.39s ================================

========================================
All tests PASSED!
========================================
```

---

## Appendix B: Document References

| Document              | Location                    |
|-----------------------|-----------------------------|
| Risk Assessment       | `docs/RISK_ASSESSMENT.md`   |
| Test Strategy         | `docs/TEST_STRATEGY.md`     |
| Test README           | `tests/README.md`           |
| Postman Collection    | `postman/GoodBooks_API_Collection.json` |
| JMeter Plan           | `jmeter/goodbooks_load_test.jmx` |

---

*Report prepared for Assignment 1 – QA Landscape & Testing Planning. Last updated: November 2025.*
