import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)

BASE = "https://www.aljazeera.com"
LIST_URL = f"{BASE}/where/ethiopia/"


@ScraperRegistry.register("al_jazeera")
class AlJazeeraScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        try:
            resp = requests.get(LIST_URL, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning("AJ listing failed: %d", resp.status_code)
                return []
        except Exception as e:
            logger.warning("AJ listing request failed: %s", e)
            return []

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning("AJ listing parse failed: %s", e)
            return []

        seen = set()
        results = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"/\d{4}/\d+/\d+/", href):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 15:
                continue

            url = utils.ensure_absolute_url(href, BASE)
            if url in seen:
                continue
            seen.add(url)

            results.append(ScrapeResult(url=url, title=title, language="en"))

        if not results:
            logger.warning(
                "AJ: 0 article URLs found — page structure may have changed "
                "(expected links matching /\\d{4}/\\d+/\\d+/)"
            )
            return []

        logger.info("AJ: found %d article URLs", len(results))

        self.enrich_batch(results, self._enrich, log_name="AJ")

        self.log_summary(results)
        return results

    def _enrich(self, result: ScrapeResult):
        try:
            resp = requests.get(result.url, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.debug("AJ %s HTTP %d", result.url, resp.status_code)
                return
        except Exception as e:
            logger.debug("AJ enrich request failed %s: %s", result.url, e)
            return

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.debug("AJ enrich parse failed %s: %s", result.url, e)
            return

        h1 = soup.find("h1")
        if h1:
            result.title = h1.get_text(strip=True)

        published = utils.extract_published_at(soup)
        if published:
            result.published_at = published
            if published < utils.CUTOFF:
                logger.debug("AJ: filtered %s (before cutoff)", result.url)
                return

        body_el = soup.select_one("div.wysiwyg, div.article-body, article")
        if body_el:
            paragraphs = []
            for p in body_el.find_all(["p", "h2", "h3"]):
                text = p.get_text(strip=True)
                if len(text) >= 20:
                    paragraphs.append(text)
            result.body = "\n\n".join(paragraphs)
            result.summary = paragraphs[0][:500] if paragraphs else ""

        if not result.published_at:
            date = utils.parse_date(result.body or "")
            if date:
                result.published_at = date
                if date < utils.CUTOFF:
                    logger.debug("AJ: filtered %s (date from body before cutoff)", result.url)
                    return

        result.author = utils.extract_author(soup)
        result.image_url = utils.extract_image_url(soup)
        result.category = utils.extract_category(soup)
        result.content_hash = utils.make_content_hash(result.title, result.summary)
