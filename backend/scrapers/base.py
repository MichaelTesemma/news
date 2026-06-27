import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    url: str
    title: str
    summary: str = ""
    body: str = ""
    image_url: str = ""
    author: str = ""
    category: str = "general"
    language: str = "en"
    view_count: int | None = None
    published_at: datetime | None = None
    content_hash: str = ""


class ScraperRegistry:
    _types: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        pass

    @classmethod
    def register(cls, scraper_type: str):
        def decorator(scraper_cls):
            cls._types[scraper_type] = scraper_cls
            return scraper_cls
        return decorator

    @classmethod
    def for_type(cls, scraper_type: str) -> type:
        scraper_cls = cls._types.get(scraper_type)
        if not scraper_cls:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        return scraper_cls

    @classmethod
    def all_types(cls) -> dict[str, type]:
        return dict(cls._types)


def _log_enrich(count: int, total: int, label: str):
    if count % max(1, total // 10) == 0 or count == total:
        logger.info("  %s %d/%d", label, count, total)


class BaseScraper(ABC):
    scraper_type: str = ""

    def __init__(self, source, **kwargs):
        self.source = source

    def enrich_batch(
        self,
        results: list[ScrapeResult],
        enrich_fn,
        batch_size: int = 25,
        log_name: str = "",
    ):
        total = len(results)
        name = log_name or self.__class__.__name__
        for i, result in enumerate(results, 1):
            try:
                enrich_fn(result)
            except Exception as e:
                logger.warning("%s enrich failed %s: %s", name, result.url, e)
            if i % batch_size == 0:
                logger.info("  %s enriched %d/%d", name, i, total)

    @abstractmethod
    def scrape(self) -> list[ScrapeResult]:
        ...

    def log_summary(self, results: list[ScrapeResult], skipped: int = 0, errors: int = 0):
        name = self.__class__.__name__
        total = len(results) + skipped + errors
        parts = [f"{len(results)} returned"]
        if skipped:
            parts.append(f"{skipped} filtered")
        if errors:
            parts.append(f"{errors} errors")
        logger.info("%s done: %s (from %d total)", name, ", ".join(parts), total)
