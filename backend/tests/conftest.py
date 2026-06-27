import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from models import db as _db, Source, Article


@pytest.fixture
def app():
    app = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_source(db):
    src = Source(name="Test Source", url="https://example.com", scraper_type="test")
    db.session.add(src)
    db.session.commit()
    return src


@pytest.fixture(autouse=True)
def reset_progress():
    from scraper_runner import progress
    progress._data = {}
    yield


@pytest.fixture
def sample_article(db, sample_source):
    from datetime import datetime, timezone
    article = Article(
        source_id=sample_source.id,
        title="Test Article",
        url="https://example.com/article/1",
        summary="Test summary",
        body="Test body content\n\nSecond paragraph.",
        author="Test Author",
        category="general",
        language="en",
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    db.session.add(article)
    db.session.commit()
    return article
