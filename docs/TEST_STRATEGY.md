# Initial Test Strategy Documentation
## GoodBooks E-Commerce Platform

**Version:** 1.0  
**Last Updated:** November 2025  
**Project:** GoodBooks - Book Recommendation Platform

---

## 1. Project Scope and Objectives

### 1.1 Project Description
GoodBooks is a NoSQL-based e-commerce platform for book recommendations. It includes:
- User registration and authentication
- Product catalog with search and categories
- Collaborative filtering recommendation engine
- User interactions (ratings, likes, purchases)
- Purchase history and profile management

### 1.2 Test Objectives
| Objective | Description |
|-----------|-------------|
| **Functional Correctness** | Verify all features work as specified |
| **Security** | Validate authentication, authorization, input validation |
| **Reliability** | Ensure system handles errors gracefully |
| **Performance** | Meet response time and load requirements |
| **User Experience** | Critical flows work end-to-end |

### 1.3 In-Scope
- Authentication (login, register, logout, forgot password)
- API endpoints (search, rate, like, purchase)
- Recommendation engine
- Search functionality
- Core user flows (E2E)
- Performance baseline

### 1.4 Out-of-Scope
- Third-party integrations (e.g., payment gateways)
- Email delivery (until configured)
- Penetration testing
- Full accessibility audit

---

## 2. Risk Assessment Results

*See [RISK_ASSESSMENT.md](./RISK_ASSESSMENT.md) for full details.*

### 2.1 Modules Prioritized by Risk

| Priority | Module | Risk Level | Test Focus |
|----------|--------|------------|------------|
| **P1** | Authentication | Critical | Security, session, validation |
| **P1** | User Data & Security | Critical | Hashing, injection, validation |
| **P1** | MongoDB & Data Layer | Critical | Connectivity, queries |
| **P2** | Recommendation Engine | High | Accuracy, cold start |
| **P2** | API Endpoints | High | Status codes, error handling |
| **P2** | Search | High | Results, filters |
| **P2** | User Interactions | High | Persistence, consistency |
| **P2** | Forgot Password | High | Token flow |
| **P3** | Product Catalog | Medium | Display, filtering |
| **P3** | UI & Templates | Medium | Forms, validation |
| **P3** | Performance | Medium | Load, response times |
| **P4** | Static Assets | Low | Links, images |

---

## 3. Test Approach

### 3.1 Manual vs Automated

| Test Type | Manual | Automated | Rationale |
|-----------|--------|-----------|-----------|
| Unit | — | ✅ | Fast feedback, repeatable |
| API/Integration | — | ✅ | Deterministic, CI-friendly |
| E2E (Critical flows) | Backup | ✅ | Regression prevention |
| E2E (Edge cases) | ✅ | — | Exploratory |
| UX/Usability | ✅ | — | Subjective |
| Security (basic) | — | ✅ | Automated checks |
| Performance | — | ✅ | JMeter/Postman |

**Strategy:** Automate high-risk areas first; use manual testing for exploratory and UX.

### 3.2 High-Risk Areas First
1. **Phase 1:** Authentication, security, data layer
2. **Phase 2:** APIs, recommendations, search
3. **Phase 3:** E2E flows, performance
4. **Phase 4:** Edge cases, usability

---

## 4. Tool Selection and Configuration

### 4.1 Tools Overview

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **pytest** | Unit, API, integration tests | `pytest.ini`, `conftest.py` |
| **Selenium** | Browser E2E (Chrome) | Headless, webdriver-manager |
| **Playwright** | Browser E2E (Chromium) | Headless, sync API |
| **Postman** | API manual/exploratory testing | `postman/GoodBooks_API_Collection.json` |
| **JMeter** | Load testing | `jmeter/goodbooks_load_test.jmx` |
| **GitHub Actions** | CI/CD pipeline | `.github/workflows/test-pipeline.yml` |

### 4.2 Installation

```bash
# Core testing
pip install -r requirements-test.txt

# Playwright browsers (for E2E)
playwright install chromium

# Selenium uses webdriver-manager (auto-downloads ChromeDriver)
```

### 4.3 Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | mongodb://localhost:27017/ | MongoDB connection |
| `SECRET_KEY` | test-secret-key | Flask secret |
| `BASE_URL` | http://localhost:5000 | E2E target URL |
| `TESTING` | 1 | Enables test mode |

---

## 5. Planned Metrics

### 5.1 Coverage Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Authentication code coverage | 95% | pytest-cov |
| API endpoint coverage | 90% | pytest-cov |
| Critical path E2E coverage | 100% | Test count |

### 5.2 Effectiveness Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Defect detection rate | — | Bugs found per phase |
| Test execution time | < 5 min (unit/API) | CI pipeline |
| Flaky test rate | < 2% | Retry analysis |
| API response time (p95) | < 500ms | JMeter/Postman |

### 5.3 Quality Gates
- All P1 tests must pass before merge
- No new critical/high severity defects
- Test pipeline must complete successfully
- Coverage must not decrease (configurable)

---

## 6. Test Repository Structure

```
goodbooks_app/
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # P1: Authentication
│   ├── test_api.py           # P2: API endpoints
│   ├── test_routes.py        # P3: Page loads
│   └── e2e/
│       ├── test_selenium.py
│       └── test_playwright.py
├── postman/
│   └── GoodBooks_API_Collection.json
├── jmeter/
│   └── goodbooks_load_test.jmx
├── docs/
│   ├── RISK_ASSESSMENT.md
│   └── TEST_STRATEGY.md
├── .github/workflows/
│   └── test-pipeline.yml
├── pytest.ini
└── requirements-test.txt
```

---

## 7. Running Tests

### 7.1 Unit & API Tests
```bash
# All unit/API tests
pytest tests/ --ignore=tests/e2e/

# With coverage
pytest tests/ --ignore=tests/e2e/ --cov=backend --cov-report=html

# Specific module
pytest tests/test_auth.py -v
```

### 7.2 E2E Tests
```bash
# Ensure app is running: python backend/app.py
# Set BASE_URL if different
pytest tests/e2e/ -v
```

### 7.3 Postman
1. Import `postman/GoodBooks_API_Collection.json`
2. Set `base_url` variable (default: http://localhost:5000)
3. Run collection or individual requests

### 7.4 JMeter
```bash
jmeter -n -t jmeter/goodbooks_load_test.jmx -l results.jtl
```

---

## 8. CI/CD Pipeline

- **Trigger:** Push/PR to `main`
- **Jobs:**
  1. Unit & API tests (Python 3.10, 3.11)
  2. E2E tests (Playwright) – app started in CI
- **Services:** MongoDB 7.x
- **Artifacts:** Test results, coverage (optional)

---

## 9. Assumptions

1. Test MongoDB available (local or CI service)
2. No production data used in tests
3. Test data can be seeded or mocked
4. GitHub/GitLab available for CI
5. Chrome/Chromium available for E2E

---

*This document should be updated as the test strategy evolves.*
