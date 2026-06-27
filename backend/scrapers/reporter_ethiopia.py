import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils
from .browser import CamoufoxPage

logger = logging.getLogger(__name__)

URLS = [
    "https://www.thereporterethiopia.com/",
    "https://www.thereporterethiopia.com/category/news/",
    "https://www.thereporterethiopia.com/category/opinion/",
]
ARTICLE_ID_RE = re.compile(r"https://www\.thereporterethiopia\.com/(\d+)/$")


@ScraperRegistry.register("reporter_ethiopia")
class ReporterEthiopiaScraper(BaseScraper):
    def _fetch_html(self, url):
        try:
            resp = requests.get(url, headers=utils.HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 403:
                logger.info("CF block %s, using Camoufox...", url)
                return ""
            logger.debug("Reporter %s HTTP %d", url, resp.status_code)
            return None
        except Exception as e:
            logger.debug("Reporter fetch failed %s: %s", url, e)
            return None

    def scrape(self) -> list[ScrapeResult]:
        urls = self._discover_urls()
        if not urls:
            logger.warning(
                "Reporter: 0 article URLs found — page structure may have changed, "
                "or site is blocking requests"
            )
            return []

        logger.info("Reporter: %d unique article URLs", len(urls))
        results = []

        for i, url in enumerate(urls, 1):
            text = self._fetch_html(url)
            if text:
                r = self._parse_article(url, text)
                if r:
                    results.append(r)
                else:
                    logger.debug("Reporter parse returned None for %s", url)
            else:
                try:
                    with CamoufoxPage() as page:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        html = page.content()
                        r = self._parse_article(url, html)
                        if r:
                            results.append(r)
                except Exception as e:
                    logger.warning("Reporter Camoufox enrich failed %s: %s", url, e)
            if i % 30 == 0:
                logger.info("  Reporter parsed %d/%d", i, len(urls))

        logger.info("Reporter: %d articles after enrichment", len(results))
        return results

    def _discover_urls(self):
        seen = set()
        for page_url in URLS:
            try:
                text = self._fetch_html(page_url)
                if not text:
                    try:
                        with CamoufoxPage() as page:
                            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                            text = page.content()
                    except Exception as e:
                        logger.warning("Reporter listing Camoufox failed %s: %s", page_url, e)
                        continue
                soup = BeautifulSoup(text, "lxml")
                count = 0
                for a in soup.select("a[href]"):
                    href = a.get("href", "").strip()
                    txt = a.get_text(strip=True)
                    m = ARTICLE_ID_RE.match(href)
                    if m and len(txt) > 10:
                        seen.add(href)
                        count += 1
                if count == 0:
                    logger.debug("Reporter: no article links found on %s", page_url)
            except Exception as e:
                logger.warning("Reporter failed to discover URLs from %s: %s", page_url, e)
        return list(seen)

    def _parse_article(self, url, html) -> ScrapeResult | None:
        try:
            soup = BeautifulSoup(html, "lxml")
            title_el = soup.select_one("h1.entry-title, h1")
            title = title_el.get_text(strip=True) if title_el else ""

            if not title:
                logger.debug("Reporter: no title found at %s", url)
                return None

            published = utils.extract_published_at(soup)

            if published and published < utils.CUTOFF:
                logger.debug("Reporter: filtered %s (before cutoff)", url)
                return None

            body, summary = utils.extract_body(soup)
            author = utils.extract_author(soup)
            category = utils.extract_category(soup)
            image_url = utils.extract_image_url(soup)

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
        except Exception as e:
            logger.debug("Reporter parse crashed for %s: %s", url, e)
            return None
