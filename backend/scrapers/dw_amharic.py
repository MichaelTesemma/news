import logging

from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils
from .browser import CamoufoxPage, safe_goto

logger = logging.getLogger(__name__)

LIST_URL = "https://www.dw.com/am/%E1%8B%AD%E1%8B%98%E1%89%B5/s-11646"


@ScraperRegistry.register("dw_amharic")
class DW_AmharicScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        urls = self._discover_urls()
        if not urls:
            logger.warning(
                "DW: 0 article URLs found — page structure may have changed "
                "(expected a[href*='/am/'][href*='/a-'])"
            )
            return []

        logger.info("DW: found %d article URLs", len(urls))
        results = []

        try:
            with CamoufoxPage() as page:
                for i, url in enumerate(urls, 1):
                    try:
                        r = self._enrich(page, url)
                        if r:
                            results.append(r)
                        else:
                            logger.debug("DW enrich returned None for %s", url)
                    except Exception as e:
                        logger.warning("DW enrich failed %s: %s", url, e)
                    if i % 10 == 0:
                        logger.info("  DW enriched %d/%d", i, len(urls))
        except Exception as e:
            logger.error("DW Amharic CamoufoxPage crashed: %s", e)

        if not results:
            logger.warning("DW: 0 articles returned after enriching %d URLs", len(urls))

        self.log_summary(results)
        return results

    def _discover_urls(self) -> list[str]:
        seen = set()
        urls = []

        try:
            with CamoufoxPage() as page:
                html = safe_goto(page, LIST_URL)
        except Exception as e:
            logger.warning("DW listing failed: %s", e)
            return urls

        soup = BeautifulSoup(html, "lxml")
        for a in soup.select('a[href*="/am/"][href*="/a-"]'):
            href = a["href"]
            if href.startswith("/"):
                href = "https://www.dw.com" + href
            if not href.startswith("https://www.dw.com/am/"):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 10:
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

        h1 = soup.select_one("article h1")
        if not h1:
            return None
        title = h1.get_text(strip=True)
        if not title:
            return None

        body = ""
        summary = ""
        rich = soup.select_one(".rich-text")
        if rich:
            paragraphs = []
            for p in rich.find_all(["p", "h2", "h3"]):
                text = p.get_text(strip=True)
                if len(text) >= 20:
                    paragraphs.append(text)
            body = "\n\n".join(paragraphs)
            summary = paragraphs[0][:500] if paragraphs else ""

        published = utils.extract_published_at(soup)
        if published and published < utils.CUTOFF:
            return None

        image_url = ""
        meta_og = soup.select_one("meta[property='og:image']")
        if meta_og:
            image_url = (meta_og.get("content") or "").strip()
        if not image_url:
            for img in soup.select("article img[srcset]"):
                srcset = (img.get("srcset") or "").strip()
                if srcset:
                    parts = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
                    if parts:
                        image_url = parts[-1]
                        break

        return ScrapeResult(
            url=url,
            title=title,
            summary=summary,
            body=body,
            image_url=image_url,
            author=utils.extract_author(soup),
            category=utils.extract_category(soup),
            language="am",
            published_at=published,
            content_hash=utils.make_content_hash(title, summary),
        )
