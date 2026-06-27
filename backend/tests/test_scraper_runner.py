from datetime import datetime, timezone

import pytest

from models import Article, Source
from scrapers.base import ScrapeResult, ScraperRegistry
from scraper_runner import ScrapeOrchestrator, ScrapeProgress, _store_articles


class TestScrapeProgress:
    def test_initial_state(self):
        p = ScrapeProgress()
        assert not p.is_running()

    def test_reset(self):
        p = ScrapeProgress()
        p.reset(5)
        assert p.is_running()
        data = p.data
        assert data["total"] == 5
        assert data["running"] is True

    def test_start_source_while_running(self):
        p = ScrapeProgress()
        p.reset(3)
        assert p.start_source("Source A", 0) is True
        data = p.data
        assert data["current"] == 0
        assert data["source_name"] == "Source A"

    def test_cancel(self):
        p = ScrapeProgress()
        p.reset(3)
        p.cancel()
        assert p.cancelled is True

    def test_finish_source(self):
        p = ScrapeProgress()
        p.reset(3)
        p.start_source("Source A", 0)
        p.finish_source("Source A", 5)
        data = p.data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["name"] == "Source A"
        assert data["sources"][0]["new"] == 5

    def test_finish(self):
        p = ScrapeProgress()
        p.reset(3)
        p.finish()
        data = p.data
        assert data["running"] is False


class TestStoreArticles:
    def test_insert_new(self, db, sample_source):
        results = [ScrapeResult(
            url="https://example.com/new",
            title="New Article",
            summary="New summary",
            content_hash="abc123",
        )]
        count = _store_articles(sample_source, results)
        assert count == 1
        assert Article.query.count() == 1

    def test_skip_duplicate_content(self, db, sample_source, sample_article):
        results = [ScrapeResult(
            url=sample_article.url,
            title=sample_article.title,
            summary=sample_article.summary,
            content_hash=sample_article.content_hash,
        )]
        count = _store_articles(sample_source, results)
        assert count == 0

    def test_update_changed_content(self, db, sample_source, sample_article):
        results = [ScrapeResult(
            url=sample_article.url,
            title="Updated Title",
            summary="Updated summary",
            content_hash="new_hash",
        )]
        count = _store_articles(sample_source, results)
        assert count == 1
        updated = Article.query.get(sample_article.id)
        assert updated.title == "Updated Title"

    def test_insert_multiple(self, db, sample_source):
        results = [
            ScrapeResult(url="https://example.com/a", title="A"),
            ScrapeResult(url="https://example.com/b", title="B"),
            ScrapeResult(url="https://example.com/c", title="C"),
        ]
        count = _store_articles(sample_source, results)
        assert count == 3


class TestScraperRegistry:
    def test_register_and_retrieve(self):
        @ScraperRegistry.register("test_scraper")
        class TestScraper:
            pass

        cls = ScraperRegistry.for_type("test_scraper")
        assert cls is TestScraper

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown scraper type"):
            ScraperRegistry.for_type("nonexistent")

    def test_all_types(self):
        before = len(ScraperRegistry.all_types())

        @ScraperRegistry.register("test_scraper_b")
        class TestScraperB:
            pass

        assert len(ScraperRegistry.all_types()) == before + 1
