import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)

BASE = "https://amharic.voanews.com"
LIST_URL = f"{BASE}/"


@ScraperRegistry.register("voa_amharic")
class VOA_AmharicScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        try:
            resp = requests.get(LIST_URL, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning("VOA listing failed: %d", resp.status_code)
                return []
        except Exception as e:
            logger.warning("VOA listing request failed: %s", e)
            return []

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning("VOA listing parse failed: %s", e)
            return []

        seen = set()
        results = []

        for a in soup.select('a[href*="/a/"][href$=".html"]'):
            href = a["href"]
            title = a.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            url = utils.ensure_absolute_url(href, BASE)
            if url in seen:
                continue
            seen.add(url)

            results.append(ScrapeResult(url=url, title=title, language="am"))

        if not results:
            logger.warning(
                "VOA: 0 article URLs found — page structure may have changed "
                "(expected a[href*='/a/'][href$='.html'])"
            )
            return []

        logger.info("VOA: found %d article URLs", len(results))

        self.enrich_batch(results, self._enrich, log_name="VOA")

        before = len(results)
        filtered = [r for r in results if r.published_at is None or r.published_at >= utils.CUTOFF]
        skipped = before - len(filtered)
        if skipped:
            logger.info("VOA: filtered %d articles before cutoff", skipped)
        self.log_summary(filtered, skipped=skipped)
        return filtered

    def _enrich(self, result: ScrapeResult):
        try:
            resp = requests.get(result.url, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.debug("VOA %s HTTP %d", result.url, resp.status_code)
                return
        except Exception as e:
            logger.debug("VOA enrich request failed %s: %s", result.url, e)
            return

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.debug("VOA enrich parse failed %s: %s", result.url, e)
            return

        h1 = soup.find("h1")
        if h1:
            result.title = h1.get_text(strip=True)

        published = utils.extract_published_at(soup)
        if published:
            result.published_at = published
            if result.published_at and result.published_at < utils.CUTOFF:
                return

        wsw = soup.select_one(".wsw")
        if wsw:
            paragraphs = []
            for p in wsw.find_all(["p", "h2", "h3"]):
                text = p.get_text(strip=True)
                if len(text) >= 20:
                    paragraphs.append(text)
            result.body = "\n\n".join(paragraphs)
            result.summary = paragraphs[0][:500] if paragraphs else ""
        else:
            logger.debug("VOA: no .wsw found at %s", result.url)

        result.image_url = utils.extract_image_url(soup)
        result.author = utils.extract_author(soup)
        result.category = utils.extract_category(soup)
        result.language = "am"
        result.content_hash = utils.make_content_hash(result.title, result.summary)
