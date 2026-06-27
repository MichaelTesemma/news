import logging
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone

from flask import current_app

from models import Article, Source, db
from scrapers.base import ScrapeResult, ScraperRegistry

_scrape_lock = threading.Lock()
from scrapers.addis_standard import AddisStandardScraper
from scrapers.al_jazeera import AlJazeeraScraper
from scrapers.ap_news import APNewsScraper
from scrapers.borkena import BorkenaScraper
from scrapers.dw_amharic import DW_AmharicScraper
from scrapers.ena import ENAArticleScraper
from scrapers.ethiopia_insider import EthiopiaInsiderScraper
from scrapers.generic_rss import GenericRSSScraper

from scrapers.hrw_ethiopia import HRWEthiopiaScraper
from scrapers.reporter_ethiopia import ReporterEthiopiaScraper
from scrapers.reuters import ReutersScraper
from scrapers.tigrai_online import TigraiOnlineScraper
from scrapers.voa_amharic import VOA_AmharicScraper

ScraperRegistry._types.update({
    "ena_eng": ENAArticleScraper,
    "addis_standard": AddisStandardScraper,
    "reporter_ethiopia": ReporterEthiopiaScraper,
    "ethiopia_observer": GenericRSSScraper,
    "borkena": BorkenaScraper,
    "ethiopia_insider": EthiopiaInsiderScraper,

    "horn_diplomat": GenericRSSScraper,
    "hrw_ethiopia": HRWEthiopiaScraper,
    "bbc_ethiopia": GenericRSSScraper,
    "ap_news": APNewsScraper,
    "al_jazeera": AlJazeeraScraper,
    "reuters": ReutersScraper,
    "voa_amharic": VOA_AmharicScraper,
    "dw_amharic": DW_AmharicScraper,
    "tigrai_online": TigraiOnlineScraper,
})

logger = logging.getLogger(__name__)


class ScrapeProgress:
    def __init__(self):
        self._data: dict = {}
        self._lock = threading.Lock()

    @property
    def data(self) -> dict:
        with self._lock:
            return dict(self._data)

    def reset(self, source_count: int = 0):
        with self._lock:
            self._data = {
                "running": True,
                "total": source_count,
                "current": 0,
                "source_name": "Starting...",
                "sources": [],
                "cancelled": False,
            }

    def start_source(self, name: str, index: int):
        with self._lock:
            if self._data.get("cancelled"):
                return False
            self._data["current"] = index
            self._data["source_name"] = name
            return True

    def finish_source(self, name: str, new_count: int, error: str | None = None):
        with self._lock:
            self._data["sources"].append({
                "name": name, "new": new_count, "error": error,
            })

    def finish(self):
        with self._lock:
            self._data["running"] = False
            self._data["current"] = len(self._data.get("sources", []))

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._data.get("cancelled", False)

    def cancel(self):
        with self._lock:
            self._data["cancelled"] = True

    def is_running(self) -> bool:
        with self._lock:
            return self._data.get("running", False)


progress = ScrapeProgress()


class ScrapeOrchestrator:
    def __init__(self, progress_observer: ScrapeProgress | None = None):
        self.progress = progress_observer

    def run(self, source_id: int | None = None) -> list[dict]:
        if not _scrape_lock.acquire(blocking=False):
            logger.warning("Scrape already in progress, skipping")
            return {"total": 0, "sources": [{"name": "Skipped — scrape already running", "new": 0}]}

        try:
            return self._run_sources(source_id)
        finally:
            _scrape_lock.release()

    def _run_sources(self, source_id: int | None = None) -> list[dict]:
        query = Source.query.filter_by(enabled=True)
        if source_id:
            query = query.filter_by(id=source_id)
        sources = query.all()

        results = {"total": 0, "sources": []}

        if self.progress:
            self.progress.reset(len(sources))

        for i, src in enumerate(sources):
            if self.progress:
                if not self.progress.start_source(src.name, i):
                    self.progress.finish()
                    results["sources"].append({"name": "Cancelled", "new": 0})
                    return results

            try:
                scraper_cls = ScraperRegistry.for_type(src.scraper_type)
                scraper = scraper_cls(src)
                articles = scraper.scrape()

                count = _store_articles(src, articles)
                src.last_scraped = datetime.now(timezone.utc)
                db.session.commit()
                results["sources"].append({"name": src.name, "new": count})
                results["total"] += count
                logger.info("Scraped %s: %d articles", src.name, count)
                if self.progress:
                    self.progress.finish_source(src.name, count)
            except Exception as e:
                logger.exception("Failed to scrape %s", src.name)
                results["sources"].append({"name": src.name, "error": str(e)})
                if self.progress:
                    self.progress.finish_source(src.name, 0, error=str(e))

        if self.progress:
            self.progress.finish()

        return results


def _store_articles(source, articles: list[ScrapeResult]) -> int:
    urls = [r.url for r in articles]
    existing = {
        row.url: row
        for row in Article.query.filter(Article.url.in_(urls)).all()
    }
    count = 0
    now = datetime.now(timezone.utc)
    for result in articles:
        data = asdict(result)
        existing_row = existing.get(result.url)
        if existing_row:
            if existing_row.content_hash != result.content_hash:
                for k, v in data.items():
                    setattr(existing_row, k, v)
                existing_row.scraped_at = now
                existing_row.updated_at = now
                count += 1
        else:
            article = Article(source_id=source.id, **data)
            db.session.add(article)
            count += 1
    db.session.commit()
    return count
