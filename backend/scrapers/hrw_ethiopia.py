import logging

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)

BASE = "https://www.hrw.org"
LIST_URL = f"{BASE}/africa/ethiopia"


@ScraperRegistry.register("hrw_ethiopia")
class HRWEthiopiaScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        all_results = []
        seen = set()

        resp = requests.get(LIST_URL, headers=utils.HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning("HRW listing failed: HTTP %d", resp.status_code)
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/news/" not in href:
                continue
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 20:
                continue

            full_url = utils.ensure_absolute_url(href, BASE)
            if full_url in seen:
                continue
            seen.add(full_url)

            all_results.append(ScrapeResult(url=full_url, title=title))

        logger.info("HRW: found %d Ethiopia articles", len(all_results))

        self.enrich_batch(all_results, self._enrich, log_name="HRW")

        return all_results

    def _enrich(self, result: ScrapeResult):
        try:
            resp = requests.get(result.url, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.debug("HRW %s HTTP %d", result.url, resp.status_code)
                return
        except Exception as e:
            logger.debug("HRW enrich request failed %s: %s", result.url, e)
            return

        try:
            soup = BeautifulSoup(resp.text, "lxml")

            body, summary = utils.extract_body(soup)
            result.body = body
            result.summary = summary

            published = utils.extract_published_at(soup)
            if published:
                result.published_at = published
            if not result.published_at:
                date = utils.parse_date(result.body)
                if date:
                    result.published_at = date

            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                result.image_url = og["content"]

            result.author = utils.extract_author(soup)
            result.category = "human-rights"
            result.language = "en"
            result.content_hash = utils.make_content_hash(result.title, result.summary)
        except Exception as e:
            logger.debug("HRW enrich parse failed %s: %s", result.url, e)
