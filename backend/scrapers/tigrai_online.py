import logging

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)

BASE = "https://tigraionline.com"
LIST_URL = f"{BASE}/"


@ScraperRegistry.register("tigrai_online")
class TigraiOnlineScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        try:
            resp = requests.get(LIST_URL, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning("Tigrai Online listing failed: %d", resp.status_code)
                return []
        except Exception as e:
            logger.warning("Tigrai Online listing request failed: %s", e)
            return []

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning("Tigrai Online listing parse failed: %s", e)
            return []

        seen = set()
        results = []

        for a in soup.select('a[href*="/articles/"][href$=".html"]'):
            href = a["href"]
            title = a.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            url = utils.ensure_absolute_url(href, BASE)
            if url in seen:
                continue
            seen.add(url)
            results.append(ScrapeResult(url=url, title=title, language="en"))

        if not results:
            logger.warning(
                "Tigrai Online: 0 article URLs found — page structure may have changed "
                "(expected a[href*='/articles/'][href$='.html'])"
            )
            return []

        logger.info("Tigrai Online: found %d article URLs", len(results))

        self.enrich_batch(results, self._enrich, log_name="Tigrai Online")

        before = len(results)
        filtered = [r for r in results if r.body and r.published_at and r.published_at >= utils.CUTOFF]
        skipped = before - len(filtered)
        if skipped:
            logger.info(
                "Tigrai Online: filtered %d articles — %d no body, %d no date/before cutoff",
                skipped,
                sum(1 for r in results if not r.body),
                sum(1 for r in results if r.body and (not r.published_at or r.published_at < utils.CUTOFF)),
            )
        self.log_summary(filtered, skipped=skipped)
        return filtered

    def _enrich(self, result: ScrapeResult):
        try:
            resp = requests.get(result.url, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.debug("Tigrai Online %s HTTP %d", result.url, resp.status_code)
                return
        except Exception as e:
            logger.debug("Tigrai Online enrich request failed %s: %s", result.url, e)
            return

        try:
            soup = BeautifulSoup(resp.text, "lxml")

            h1 = soup.select_one("header h1")
            if h1:
                result.title = h1.get_text(strip=True)

            published = utils.extract_published_at(soup)
            if published:
                result.published_at = published
                if result.published_at < utils.CUTOFF:
                    return

            body_el = soup.select_one(".article-body")
            if body_el:
                paragraphs = []
                for p in body_el.find_all(["p", "h2", "h3"]):
                    text = p.get_text(strip=True)
                    if len(text) >= 20:
                        paragraphs.append(text)
                if paragraphs:
                    result.body = "\n\n".join(paragraphs)
                    result.summary = paragraphs[0][:500] if paragraphs else ""
            else:
                logger.debug("Tigrai Online: no .article-body found at %s", result.url)

            result.image_url = utils.extract_image_url(soup)
            result.author = utils.extract_author(soup)
            result.category = utils.extract_category(soup)
            result.language = "en"
            result.content_hash = utils.make_content_hash(result.title, result.summary)
        except Exception as e:
            logger.debug("Tigrai Online enrich parse failed %s: %s", result.url, e)
