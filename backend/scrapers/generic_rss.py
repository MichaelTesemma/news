import logging
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)


class GenericRSSScraper(BaseScraper):
    def __init__(self, source, feed_url=None, language="en"):
        super().__init__(source)
        if feed_url:
            self.feed_url = feed_url
        else:
            url = source["url"].rstrip("/")
            if url.endswith(".xml") or url.endswith(".rss") or url.endswith("/feed"):
                self.feed_url = url
            else:
                self.feed_url = url + "/feed/"
        self.language = language

    def _fetch_feed(self):
        resp = requests.get(
            self.feed_url,
            headers={
                "User-Agent": utils.USER_AGENT,
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.text
        if not body:
            return feedparser.parse(self.feed_url)
        return feedparser.parse(body)

    def scrape(self) -> list[ScrapeResult]:
        parsed = self._fetch_feed()
        results = []

        for entry in parsed.entries:
            published = self._parse_pubdate(entry)
            if published and published < utils.CUTOFF:
                continue

            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue

            body_html = ""
            if hasattr(entry, "content") and entry.content:
                body_html = entry.content[0].get("value", "")
            if not body_html:
                body_html = entry.get("description", "")

            author = ""
            if hasattr(entry, "dc_creator"):
                author = entry.dc_creator.strip()
            if not author and hasattr(entry, "author"):
                author = entry.author.strip()

            categories = []
            if hasattr(entry, "tags"):
                categories = [t.get("term", "") for t in entry.tags if t.get("term")]
            category = categories[0] if categories else "general"

            image_url = self._extract_image(body_html)

            body_soup = BeautifulSoup(body_html, "lxml")
            body_text = body_soup.get_text("\n\n", strip=True)

            summary = entry.get("summary", "") or ""
            if summary:
                summary_soup = BeautifulSoup(summary, "lxml")
                summary = summary_soup.get_text(strip=True)[:500]

            results.append(ScrapeResult(
                url=url,
                title=title,
                summary=summary,
                body=body_text,
                image_url=image_url,
                author=author,
                category=category,
                language=self.language,
                published_at=published,
                content_hash=utils.make_content_hash(title, summary),
            ))

        logger.info("RSS feed %s: %d articles", self.feed_url, len(results))
        return results

    def _parse_pubdate(self, entry):
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            import time as time_module
            ts = time_module.mktime(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if hasattr(entry, "published") and entry.published:
            import email.utils
            try:
                parsed = email.utils.parsedate_to_datetime(entry.published)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                pass
        return None

    def _extract_image(self, html):
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        img = soup.find("img")
        if img and img.get("src"):
            src = img["src"]
            if "logo" not in src.lower() and "gravatar" not in src.lower():
                return src
        return ""


ScraperRegistry._types["ethiopia_observer"] = GenericRSSScraper
ScraperRegistry._types["bbc_ethiopia"] = GenericRSSScraper
