import logging
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)

GNEWS_URL = (
    "https://news.google.com/rss/search?"
    "q=site:reuters.com+Ethiopia&hl=en-US&gl=US&ceid=US:en"
)


@ScraperRegistry.register("reuters")
class ReutersScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        results = []

        try:
            resp = requests.get(GNEWS_URL, headers=utils.HEADERS, timeout=30)
        except Exception as e:
            logger.warning("Reuters Google News RSS failed: %s", e)
            return results

        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            src = entry.get("source", {})
            if src.get("title") != "Reuters":
                continue

            title = entry.get("title", "").replace(" - Reuters", "").strip()
            if not title or len(title) < 15:
                continue

            published = self._parse_published(entry.get("published", ""))
            if published and published < utils.CUTOFF:
                continue

            link = entry.get("link", "")
            summary = self._extract_summary(entry)

            try:
                body = self._enrich_body(link) or summary
            except Exception as e:
                logger.debug("Reuters enrich failed %s: %s", link, e)
                body = summary

            results.append(ScrapeResult(
                url=link,
                title=title,
                summary=summary,
                body=body,
                image_url="",
                author="Reuters",
                category="general",
                language="en",
                published_at=published,
                content_hash=utils.make_content_hash(title, summary),
            ))

        logger.info("Reuters: %d articles from Google News RSS", len(results))
        return results

    def _parse_published(self, text: str) -> datetime | None:
        try:
            parsed = datetime.strptime(text, "%a, %d %b %Y %H:%M:%S %Z")
            return parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    def _extract_summary(self, entry) -> str:
        summary_html = entry.get("summary", "")
        if not summary_html:
            return ""
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(strip=True)
        return text[:500]

    def _enrich_body(self, url: str) -> str | None:
        try:
            resp = requests.get(
                url, headers=utils.HEADERS, timeout=15, allow_redirects=True
            )
        except Exception:
            return None
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        body, _ = utils.extract_body(soup)
        return body if body else None
