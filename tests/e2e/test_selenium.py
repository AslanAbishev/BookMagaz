"""
E2E tests using Selenium
Run: pytest tests/e2e/test_selenium.py -v
Requires: Chrome/Chromium, chromedriver (via webdriver-manager)
"""
import os
import pytest

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@pytest.mark.skipif(not SELENIUM_AVAILABLE, reason="Selenium not installed")
class TestGoodBooksE2E:
    """End-to-end tests with Selenium."""

    @pytest.fixture(scope="class")
    def driver(self):
        """Create headless Chrome driver."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        yield driver
        driver.quit()

    @pytest.fixture
    def base_url(self):
        return os.getenv("BASE_URL", "http://localhost:5000")

    def test_homepage_loads(self, driver, base_url):
        """Homepage loads and shows content."""
        driver.get(base_url)
        assert "GoodBooks" in driver.title or "goodbooks" in driver.title.lower()

    def test_navigation_to_login(self, driver, base_url):
        """Can navigate to login page."""
        driver.get(base_url)
        login_link = driver.find_element(By.LINK_TEXT, "Login")
        login_link.click()
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        assert "login" in driver.current_url.lower()

    def test_search_form_exists(self, driver, base_url):
        """Search form is present on homepage."""
        driver.get(base_url)
        search_input = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[name='q']")
        assert len(search_input) > 0
