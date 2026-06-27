import logging
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils
from .browser import CamoufoxPage, safe_goto

logger = logging.getLogger(__name__)

BASE = "https://addisstandard.com"
CATEGORIES = [
    "politics", "business", "social-affairs", "law-order",
    "art", "innovation", "news", "opinion", "as-commentary",
    "oped", "as-editorial", "as-feature", "in-depth-analysis", "interview",
]


@ScraperRegistry.register("addis_standard")
class AddisStandardScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        all_results = []
        seen = set()

        list_urls = [f"{BASE}/"] + [f"{BASE}/category/{c}/" for c in CATEGORIES]

        with CamoufoxPage() as page:
            for list_url in list_urls:
                try:
                    html = safe_goto(page, list_url)
                    soup = BeautifulSoup(html, "lxml")
                    cat = "general"
                    for c in CATEGORIES:
                        if f"/{c}" in list_url:
                            cat = c
                            break
                    cards = self._parse_cards(soup, cat)
                    for c in cards:
                        if c.url not in seen:
                            seen.add(c.url)
                            all_results.append(c)
                except Exception as e:
                    logger.warning("Listing %s failed: %s", list_url, e)

        logger.info("Found %d article URLs, enriching bodies...", len(all_results))
        self._enrich_all_batched(all_results)
        return all_results

    def _enrich_all_batched(self, results: list[ScrapeResult]):
        batch_size = 25
        for start in range(0, len(results), batch_size):
            batch = results[start:start + batch_size]
            try:
                with CamoufoxPage() as page:
                    def enrich_fn(result):
                        self._enrich(page, result)
                    self.enrich_batch(
                        batch, enrich_fn, batch_size=1,
                        log_name="Addis Standard",
                    )
            except Exception as e:
                msg = str(e).lower()
                if "interpreter shutdown" in msg or "shutdown" in msg:
                    logger.error("Fatal: browser pool shut down at article %d, giving up", start)
                    return
                logger.warning("Browser died at article %d, retrying batch...", start)
                try:
                    with CamoufoxPage() as page:
                        def enrich_retry(result):
                            self._enrich(page, result)
                        self.enrich_batch(
                            batch, enrich_retry, batch_size=1,
                            log_name="Addis Standard (retry)",
                        )
                except Exception as e3:
                    logger.error("Browser died again at article %d, skipping batch: %s", start, e3)

    def _parse_cards(self, soup: BeautifulSoup, default_category: str) -> list[ScrapeResult]:
        cards = []
        seen_slugs = set()

        for a_tag in soup.find_all("a", href=True):
            href = utils.ensure_absolute_url(a_tag["href"], BASE)
            if not href.startswith(BASE):
                continue
            if href.rstrip("/") == BASE:
                continue

            parts = href.rstrip("/").split("/")
            slug = parts[-1] if len(parts) >= 4 else ""
            if not slug or len(slug) < 10:
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 15:
                continue

            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            parent = a_tag.find_parent(["article", "div", "li", "section"])

            date = None
            summary = ""
            image_url = ""
            category = default_category
            author = ""

            img = a_tag.find("img")
            if img and img.get("src"):
                image_url = utils.ensure_absolute_url(img["src"], BASE)
            if not image_url and parent:
                img = parent.find("img")
                if img and img.get("src"):
                    image_url = utils.ensure_absolute_url(img["src"], BASE)

            if parent:
                full = parent.get_text(" ", strip=True)
                date = utils.parse_date(full)
                for cat in CATEGORIES:
                    if cat.replace("-", " ") in full.lower():
                        category = cat
                        break
                cat_link = parent.find("a", href=re.compile(r"/category/"))
                if cat_link:
                    cat_path = cat_link["href"].rstrip("/").split("/")[-1]
                    if cat_path in CATEGORIES:
                        category = cat_path

            cards.append(ScrapeResult(
                url=href,
                title=title,
                summary=summary,
                image_url=image_url,
                category=category,
                language="en",
                author=author,
                published_at=date,
                content_hash=utils.make_content_hash(title, summary),
            ))
        return cards

    def _enrich(self, page, result: ScrapeResult):
        html = ""
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
        if not html:
            try:
                page.wait_for_timeout(2000)
                html = page.content()
            except Exception as e:
                logger.debug("Addis Standard page content failed %s: %s", result.url, e)
                return
        if not html:
            return

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            logger.debug("Addis Standard parse failed %s: %s", result.url, e)
            return

        h1 = soup.find("h1")
        if h1:
            result.title = h1.get_text(strip=True)

        body, summary = utils.extract_body(soup)
        result.body = body
        if summary:
            result.summary = summary[:500]

        if not result.image_url:
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if "logo" in src.lower():
                    continue
                if src.startswith("http") and "gravatar" not in src:
                    result.image_url = src
                    break

        if not result.published_at:
            date = utils.parse_date(body)
            if date:
                result.published_at = date
            elif h1:
                date = utils.parse_date(h1.get_text(strip=True))
                if date:
                    result.published_at = date

        result.content_hash = utils.make_content_hash(result.title, result.summary)
