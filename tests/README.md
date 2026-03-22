# GoodBooks Test Suite

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements-test.txt
playwright install chromium   # For E2E tests
```

### 2. Start MongoDB
```bash
docker-compose up -d
# Or use local MongoDB on localhost:27017
```

### 3. Run tests
```bash
# Unit + API tests (no app needed for most)
cd backend && python -m pytest ../tests/ --ignore=../tests/e2e/ -v

# E2E tests (app must be running)
# Terminal 1: python backend/app.py
# Terminal 2: pytest tests/e2e/ -v
```

## Test Categories

| Directory/File | Type | Description |
|----------------|------|-------------|
| `test_auth.py` | Unit/Integration | Login, register, logout, forgot password |
| `test_api.py` | API | Search, rate, like, purchase, categories |
| `test_routes.py` | Integration | Page loads, redirects |
| `e2e/test_selenium.py` | E2E | Browser tests (Selenium) |
| `e2e/test_playwright.py` | E2E | Browser tests (Playwright) |

## Tools

- **pytest** – Test runner
- **Selenium** – Browser automation (Chrome)
- **Playwright** – Browser automation (Chromium)
- **Postman** – API collection in `../postman/`
- **JMeter** – Load test in `../jmeter/`

## CI/CD

Tests run automatically on push/PR to `main` via GitHub Actions.
See `.github/workflows/test-pipeline.yml`.
