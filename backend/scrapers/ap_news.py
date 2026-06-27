import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils
from .browser import CamoufoxPage, safe_goto

logger = logging.getLogger(__name__)

BASE = "https://apnews.com"
LIST_URL = f"{BASE}/hub/ethiopia"


@ScraperRegistry.register("ap_news")
class APNewsScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        urls = self._discover_urls()
        if not urls:
            logger.warning(
                "AP: 0 article URLs found — page structure may have changed "
                "(expected links matching https://apnews.com/article/[\\w-]{20,})"
            )
            return []

        logger.info("AP: %d article URLs", len(urls))
        results = []

        try:
            with CamoufoxPage() as page:
                for i, url in enumerate(urls, 1):
                    try:
                        r = self._enrich(page, url)
                        if r:
                            results.append(r)
                        else:
                            logger.debug("AP enrich returned None for %s", url)
                    except Exception as e:
                        logger.warning("AP enrich failed %s: %s", url, e)
                    if i % 10 == 0:
                        logger.info("  AP enriched %d/%d", i, len(urls))
        except Exception as e:
            logger.error("AP News CamoufoxPage crashed: %s", e)

        if not results:
            logger.warning("AP: 0 articles returned after enriching %d URLs", len(urls))

        self.log_summary(results)
        return results

    def _discover_urls(self) -> list[str]:
        try:
            resp = requests.get(LIST_URL, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning("AP listing failed: %d", resp.status_code)
                return []
        except Exception as e:
            logger.warning("AP listing request failed: %s", e)
            return []

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning("AP listing parse failed: %s", e)
            return []

        seen = set()
        urls = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.match(r"https://apnews\.com/article/[\w-]{20,}", href):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            if not re.search(r"Ethiopia|ethiopia", title):
                continue
            if href in seen:
                continue
            seen.add(href)
            urls.append(href)

        return urls

    def _enrich(self, page, url: str) -> ScrapeResult | None:
        try:
            html = safe_goto(page, url)
        except Exception:
            return None

        soup = BeautifulSoup(html, "lxml")

        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        body, summary = utils.extract_body(soup)
        published = utils.extract_published_at(soup)
        author = utils.extract_author(soup)
        image_url = utils.extract_image_url(soup)
        category = utils.extract_category(soup)

        if published and published < utils.CUTOFF:
            return None

        return ScrapeResult(
            url=url,
            title=title,
            summary=summary,
            body=body,
            image_url=image_url,
            author=author,
            category=category,
            language="en",
            published_at=published,
            content_hash=utils.make_content_hash(title, summary),
        )
