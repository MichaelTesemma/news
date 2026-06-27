import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils
from .browser import CamoufoxPage, safe_goto

logger = logging.getLogger(__name__)

BASE = "https://ethiopiainsider.com"


@ScraperRegistry.register("ethiopia_insider")
class EthiopiaInsiderScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        all_results = []
        seen = set()

        with CamoufoxPage() as page:
            try:
                for attempt in range(3):
                    try:
                        page.goto(BASE, wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(5000)
                        html = page.content()
                        if "security verification" not in html[:500].lower():
                            break
                        page.wait_for_timeout(5000)
                    except Exception:
                        page.wait_for_timeout(3000)

                soup = BeautifulSoup(html, "lxml")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if not re.match(rf"^{re.escape(BASE)}/\d{{4}}/\d+", href):
                        continue
                    title = a_tag.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue
                    if href in seen:
                        continue
                    seen.add(href)

                    published = self._parse_year_from_url(href)
                    if published and published < utils.CUTOFF:
                        continue

                    all_results.append(ScrapeResult(url=href, title=title, published_at=published))

                logger.info("EI: found %d article URLs", len(all_results))

                def enrich_fn(result):
                    self._enrich(page, result)

                self.enrich_batch(all_results, enrich_fn, log_name="EI")
            finally:
                page.close()

        if not all_results:
            logger.warning(
                "EI: 0 article URLs found — page structure may have changed "
                "(expected links matching /\\d{4}/\\d+/)"
            )
            return []

        before = len(all_results)
        filtered = [r for r in all_results if r.body and (r.published_at is None or r.published_at >= utils.CUTOFF)]
        skipped = before - len(filtered)
        if skipped:
            logger.info("EI: filtered %d articles (no body or before cutoff)", skipped)
        self.log_summary(filtered, skipped=skipped)
        return filtered

    def _enrich(self, page, result: ScrapeResult):
        for attempt in range(3):
            try:
                page.goto(result.url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                html = page.content()
                if "security verification" not in html[:500].lower():
                    break
                page.wait_for_timeout(5000)
            except Exception:
                page.wait_for_timeout(3000)
        else:
            html = page.content()
        page.wait_for_timeout(2000)
        html = page.content()

        soup = BeautifulSoup(html, "lxml")

        h1 = soup.find("h1")
        if h1:
            result.title = h1.get_text(strip=True)

        body, summary = utils.extract_body(soup)
        result.body = body
        result.summary = summary

        if not result.published_at:
            date = utils.parse_date(result.body)
            if date:
                result.published_at = date

        result.author = utils.extract_author(soup)
        result.image_url = utils.extract_image_url(soup)
        result.category = utils.extract_category(soup)
        result.language = "am"
        result.content_hash = utils.make_content_hash(result.title, result.summary)

    def _parse_year_from_url(self, url):
        m = re.search(r"/(\d{4})/", url)
        if m:
            year = int(m.group(1))
            if year >= 2026:
                return datetime(year, 1, 1, tzinfo=timezone.utc)
        return None
