import threading
import time

import pytest
import requests

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

BASE_URL = "http://localhost:5002"


@pytest.fixture(scope="module")
def live_server():
    from app import create_app
    from tests.fake_db import FakeDB
    fake_db = FakeDB()
    test_app = create_app(test_config={
        "TESTING": True,
        "SOURCES_CONFIG_PATH": "/dev/null",
    }, db=fake_db)

    def run():
        test_app.run(port=5002, debug=False, use_reloader=False)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            resp = requests.get(f"{BASE_URL}/", timeout=1)
            if resp.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("Server did not start in time")

    yield


class TestAPIE2E:
    def test_index_endpoint(self, live_server):
        resp = requests.get(f"{BASE_URL}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "The Ethiopia Digest API"

    def test_list_articles(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/articles")
        assert resp.status_code == 200
        data = resp.json()
        assert "articles" in data
        assert "total" in data

    def test_list_sources(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data

    def test_dashboard(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_articles" in data

    def test_sitemap(self, live_server):
        resp = requests.get(f"{BASE_URL}/sitemap.xml")
        assert resp.status_code == 200
        assert "xml" in resp.headers.get("content-type", "")

    def test_robots_txt(self, live_server):
        resp = requests.get(f"{BASE_URL}/robots.txt")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_rss_feed(self, live_server):
        resp = requests.get(f"{BASE_URL}/rss.xml")
        assert resp.status_code == 200
        assert "xml" in resp.headers.get("content-type", "")

    def test_digest(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/digest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "The Ethiopia Digest"

    def test_sync_scrape(self, live_server):
        resp = requests.post(f"{BASE_URL}/api/scrape", json={}, timeout=5)
        assert resp.status_code == 202
        data = resp.json()
        assert "sources" in data
        assert "total" in data

    def test_categories(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data

    def test_trending(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/articles/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert "articles" in data

    def test_search(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/articles/search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["articles"] == []

    def test_404(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/articles/99999")
        assert resp.status_code == 404

    def test_cors_headers(self, live_server):
        resp = requests.get(f"{BASE_URL}/api/articles",
                            headers={"Origin": "http://localhost:5173"})
        assert resp.status_code == 200

    def test_cancel_noop_when_not_running(self, live_server):
        resp = requests.post(f"{BASE_URL}/api/scrape/cancel", timeout=5)
        assert resp.status_code == 409


@pytest.fixture(scope="module")
def browser():
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


class TestPlaywrightE2E:
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
    def test_homepage_title(self, live_server, browser):
        page = browser.new_page()
        page.goto(f"{BASE_URL}/")
        body = page.text_content("body")
        assert body is not None
        assert "The Ethiopia Digest API" in body
        page.close()

    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
    def test_api_response_json(self, live_server, browser):
        page = browser.new_page()
        resp = page.goto(f"{BASE_URL}/api/articles")
        assert resp.status == 200
        content = page.content()
        assert '"articles"' in content
        page.close()

    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
    def test_404_response(self, live_server, browser):
        page = browser.new_page()
        resp = page.goto(f"{BASE_URL}/api/articles/99999")
        assert resp.status == 404
        content = page.content()
        assert "not found" in content.lower()
        page.close()

    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
    def test_sources_response(self, live_server, browser):
        page = browser.new_page()
        resp = page.goto(f"{BASE_URL}/api/sources")
        assert resp.status == 200
        page.close()

    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
    def test_dashboard_response(self, live_server, browser):
        page = browser.new_page()
        resp = page.goto(f"{BASE_URL}/api/dashboard")
        assert resp.status == 200
        page.close()
