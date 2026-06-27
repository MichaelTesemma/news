import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils
from .browser import CamoufoxPage, safe_goto

logger = logging.getLogger(__name__)

BASE = "https://borkena.com"


@ScraperRegistry.register("borkena")
class BorkenaScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        all_results = []
        seen = set()
        errors = 0

        try:
            with CamoufoxPage() as page:
                try:
                    html = safe_goto(page, BASE)
                except Exception as e:
                    logger.warning("Borkena listing page failed: %s", e)
                    return []

                soup = BeautifulSoup(html, "lxml")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if not re.match(rf"^{re.escape(BASE)}/\d{{4}}/\d{{2}}/\d{{2}}/", href):
                        continue
                    title = a_tag.get_text(strip=True)
                    if not title or len(title) < 15:
                        continue
                    if href in seen:
                        continue
                    seen.add(href)
                    all_results.append(ScrapeResult(url=href, title=title))

                logger.info("Borkena: found %d article URLs", len(all_results))

                self.enrich_batch(all_results, self._enrich, log_name="Borkena")
        except Exception as e:
            logger.error("Borkena scrape crashed: %s", e)
            errors = 1

        before_filter = len(all_results)
        filtered = [r for r in all_results if r.body and r.published_at and r.published_at >= utils.CUTOFF]
        skipped = before_filter - len(filtered)
        if skipped:
            logger.info("Borkena: filtered %d articles (no body, no date, or before cutoff)", skipped)
        self.log_summary(filtered, skipped=skipped, errors=errors)
        return filtered

    def _enrich(self, result: ScrapeResult):
        try:
            resp = requests.get(result.url, headers=utils.HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.debug("Borkena %s HTTP %d", result.url, resp.status_code)
                return
        except Exception as e:
            logger.debug("Borkena enrich request failed %s: %s", result.url, e)
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

            result.author = utils.extract_author(soup)
            result.image_url = utils.extract_image_url(soup)
            result.category = utils.extract_category(soup)
            result.language = "en"
            result.content_hash = utils.make_content_hash(result.title, result.summary)
        except Exception as e:
            logger.debug("Borkena enrich parse failed %s: %s", result.url, e)
