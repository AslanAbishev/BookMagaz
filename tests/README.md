# GoodBooks Test Suite

## Quick Start

### 1. Install dependencies
```bash
pip install pytest flask-testing requests
# Full: pip install -r requirements-test.txt
# E2E: playwright install chromium
```

### 2. Start MongoDB
```bash
docker-compose up -d
# Or use local MongoDB on localhost:27017
```

### 3. Run tests
```bash
# Option A: Use the run script
.\run_tests.ps1        # PowerShell
.\run_tests.bat        # Command Prompt

# Option B: Run directly
python -m pytest tests/ -v --ignore=tests/e2e

# Option C: Run from project root
.\venv\Scripts\Activate.ps1
python -m pytest tests/ -v --ignore=tests/e2e
```

## Test Categories (by Risk Priority)

| File | Priority | Description |
|------|----------|-------------|
| `test_auth.py` | P1 Critical | Login, register, logout, forgot password |
| `test_api.py` | P2 High | Search, rate, like, purchase, categories |
| `test_search.py` | P2 High | Search by text, category, combined |
| `test_recommendations.py` | P2 High | Profile, recommendations, similar books |
| `test_models.py` | P1/P2 | Data layer, categories |
| `test_routes.py` | P3 Medium | Page loads, redirects |
| `e2e/test_selenium.py` | E2E | Browser tests (Selenium) |
| `e2e/test_playwright.py` | E2E | Browser tests (Playwright) |

## Expected Results

- **~34 tests** should pass (1 recommend API test is skipped - can hang with large data)
- All P1 (Authentication) and P2 (API, Search) tests must pass

## Tools

- **pytest** – Test runner
- **Postman** – `postman/GoodBooks_API_Collection.json`
- **JMeter** – `jmeter/goodbooks_load_test.jmx`
- **Selenium/Playwright** – E2E (optional)

## CI/CD

Tests run on push/PR to `main` via GitHub Actions (`.github/workflows/test-pipeline.yml`).
