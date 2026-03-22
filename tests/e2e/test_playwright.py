"""
E2E tests using Playwright
Run: pytest tests/e2e/test_playwright.py -v
Setup: playwright install chromium
"""
import os
import pytest

try:
    from playwright.sync_api import sync_playwright, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestGoodBooksPlaywright:
    """End-to-end tests with Playwright."""

    @pytest.fixture(scope="class")
    def browser(self):
        """Create browser context."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture
    def page(self, browser):
        """Create new page for each test."""
        return browser.new_page()

    @pytest.fixture
    def base_url(self):
        return os.getenv("BASE_URL", "http://localhost:5000")

    def test_homepage_title(self, page, base_url):
        """Homepage has expected title."""
        page.goto(base_url)
        assert page.title()

    def test_register_flow(self, page, base_url):
        """Register page has form fields."""
        page.goto(f"{base_url}/register")
        page.wait_for_load_state("networkidle")
        username = page.locator('input[name="username"]')
        email = page.locator('input[name="email"]')
        password = page.locator('input[name="password"]')
        assert username.is_visible()
        assert email.is_visible()
        assert password.is_visible()

    def test_login_flow(self, page, base_url):
        """Login page has form and forgot password link."""
        page.goto(f"{base_url}/login")
        page.wait_for_load_state("networkidle")
        assert page.locator('input[name="username"]').is_visible()
        assert page.locator('input[name="password"]').is_visible()
        # Forgot password link
        forgot_link = page.get_by_text("Forgot Password", exact=False)
        assert forgot_link.count() > 0
