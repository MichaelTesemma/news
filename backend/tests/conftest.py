import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env before importing config so env vars are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import config as app_config
from app import create_app
from tests.fake_db import FakeDB

# Prevent seeding from real sources.yaml during tests
app_config.SOURCES_CONFIG_PATH = os.devnull


@pytest.fixture
def app():
    fake_db = FakeDB()
    app = create_app(test_config={
        "TESTING": True,
    }, db=fake_db)
    app._test_db = fake_db
    yield app


@pytest.fixture
def db(app):
    return app._test_db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_source(db):
    return db.add_source("Test Source", "https://example.com", "test")


@pytest.fixture(autouse=True)
def reset_progress():
    from scraper_runner import progress
    progress._data = {}
    yield


@pytest.fixture
def sample_article(db, sample_source):
    from datetime import datetime, timezone
    result = db.post("articles", {
        "source_id": sample_source["id"],
        "title": "Test Article",
        "url": "https://example.com/article/1",
        "summary": "Test summary",
        "body": "Test body content\n\nSecond paragraph.",
        "author": "Test Author",
        "category": "general",
        "language": "en",
        "published_at": datetime(2026, 6, 1, tzinfo=timezone.utc).isoformat(),
    })
    return result[0]
