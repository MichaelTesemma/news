import logging
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone

from scrapers.base import ScrapeResult, ScraperRegistry

_scrape_lock = threading.Lock()

from scrapers.al_jazeera import AlJazeeraScraper
from scrapers.ena import ENAArticleScraper
from scrapers.generic_rss import GenericRSSScraper
from scrapers.hrw_ethiopia import HRWEthiopiaScraper
from scrapers.reuters import ReutersScraper
from scrapers.tigrai_online import TigraiOnlineScraper
from scrapers.voa_amharic import VOA_AmharicScraper

ScraperRegistry._types.update({
    "ena_eng": ENAArticleScraper,
    "ethiopia_observer": GenericRSSScraper,
    "horn_diplomat": GenericRSSScraper,
    "hrw_ethiopia": HRWEthiopiaScraper,
    "bbc_ethiopia": GenericRSSScraper,
    "al_jazeera": AlJazeeraScraper,
    "reuters": ReutersScraper,
    "voa_amharic": VOA_AmharicScraper,
    "tigrai_online": TigraiOnlineScraper,
})

# Playwright/Camoufox scrapers (may fail on resource-constrained hosts)
for _mod, _name, _key in [
    ("scrapers.addis_standard", "AddisStandardScraper", "addis_standard"),
    ("scrapers.ap_news", "APNewsScraper", "ap_news"),
    ("scrapers.borkena", "BorkenaScraper", "borkena"),
    ("scrapers.dw_amharic", "DW_AmharicScraper", "dw_amharic"),
    ("scrapers.ethiopia_insider", "EthiopiaInsiderScraper", "ethiopia_insider"),
    ("scrapers.reporter_ethiopia", "ReporterEthiopiaScraper", "reporter_ethiopia"),
]:
    try:
        _cls = getattr(__import__(_mod, fromlist=[_name]), _name)
        ScraperRegistry._types[_key] = _cls
    except ImportError:
        pass

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
    def __init__(self, progress_observer: ScrapeProgress | None = None, db=None):
        self.progress = progress_observer
        self.db = db

    def run(self, source_id: int | None = None) -> list[dict]:
        if not _scrape_lock.acquire(blocking=False):
            logger.warning("Scrape already in progress, skipping")
            return {"total": 0, "sources": [{"name": "Skipped — scrape already running", "new": 0}]}

        try:
            return self._run_sources(source_id)
        finally:
            _scrape_lock.release()

    def _run_sources(self, source_id: int | None = None) -> list[dict]:
        sources = self.db.get_enabled_sources(source_id)

        results = {"total": 0, "sources": []}

        if self.progress:
            self.progress.reset(len(sources))

        for i, src in enumerate(sources):
            if self.progress:
                if not self.progress.start_source(src["name"], i):
                    self.progress.finish()
                    results["sources"].append({"name": "Cancelled", "new": 0})
                    return results

            try:
                scraper_cls = ScraperRegistry.for_type(src["scraper_type"])
                scraper = scraper_cls(src)
                articles = scraper.scrape()

                count = _store_articles(self.db, src, articles)
                self.db.update_source_last_scraped(src["id"])
                results["sources"].append({"name": src["name"], "new": count})
                results["total"] += count
                logger.info("Scraped %s: %d articles", src["name"], count)
                if self.progress:
                    self.progress.finish_source(src["name"], count)
            except Exception as e:
                logger.exception("Failed to scrape %s", src["name"])
                results["sources"].append({"name": src["name"], "error": str(e)})
                if self.progress:
                    self.progress.finish_source(src["name"], 0, error=str(e))

        if self.progress:
            self.progress.finish()

        return results


def _store_articles(db, source, articles: list[ScrapeResult]) -> int:
    urls = [r.url for r in articles]
    existing = db.get_articles_by_urls(urls)

    count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for result in articles:
        data = {k: v for k, v in asdict(result).items()}
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
        existing_row = existing.get(result.url)
        if existing_row:
            if existing_row.get("content_hash") != result.content_hash:
                upd = {k: v for k, v in data.items() if k != "url"}
                upd["scraped_at"] = now_iso
                upd["updated_at"] = now_iso
                db.patch("articles", upd, {"id": ("eq", existing_row["id"])})
                count += 1
        else:
            data["source_id"] = source["id"]
            data["scraped_at"] = now_iso
            data["updated_at"] = now_iso
            db.post("articles", data)
            count += 1

    return count
