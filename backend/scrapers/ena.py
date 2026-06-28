import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapeResult, ScraperRegistry
from . import utils

logger = logging.getLogger(__name__)

LANGUAGES = {
    "eng": {"label": "en", "prefix": "eng_"},
    "amh": {"label": "am", "prefix": "amh_"},
}

CATEGORIES = [
    "politics", "social", "economy", "sport",
    "technology", "environment", "feature", "videos",
]


def _extract_article_id(url: str) -> str | None:
    m = re.search(r"/(?:eng_|amh_)(\d+)", url)
    return m.group(1) if m else None


def _fetch_soup(url: str, timeout: int = 15):
    resp = requests.get(url, headers=utils.HEADERS, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "lxml")


class ENAArticleScraper(BaseScraper):
    def scrape(self) -> list[ScrapeResult]:
        lang = self.source["scraper_type"].replace("ena_", "")
        if lang not in LANGUAGES:
            logger.error("Unknown ENA language: %s", lang)
            return []
        return self._scrape_language(lang)

    def _scrape_language(self, lang: str) -> list[ScrapeResult]:
        base_url = f"https://www.ena.et/web/{lang}/"
        seen = {}
        listing_urls = [f"https://www.ena.et/web/{lang}/{c}" for c in CATEGORIES] + [base_url]

        cat_from_url = {f"/{c}": c for c in CATEGORIES}

        for list_url in listing_urls:
            try:
                soup = _fetch_soup(list_url)
                cat = next((c for path, c in cat_from_url.items() if path in list_url), "general")
                cards = self._parse_listing_cards(soup, cat)
                for c in cards:
                    aid = _extract_article_id(c["url"])
                    if aid and aid not in seen:
                        seen[aid] = c
            except Exception as e:
                logger.warning("Listing %s failed: %s", list_url, e)

        results = []
        filtered = 0
        for aid, card in seen.items():
            result = self._enrich_with_body(lang, aid, card)
            if result:
                if len(result.body) >= 100:
                    results.append(result)
                else:
                    logger.debug("ENA %s: skipped %s (body too short: %d chars)", lang, card["url"], len(result.body))
                    filtered += 1
            else:
                filtered += 1

        if filtered:
            logger.info("ENA %s: %d articles after filtering %d", lang, len(results), filtered)
        else:
            logger.info("ENA %s: %d articles", lang, len(results))
        self.log_summary(results, skipped=filtered)
        return results

    def _parse_listing_cards(self, soup: BeautifulSoup, default_category: str) -> list[dict]:
        cards = []
        for container in soup.find_all("div", class_="ena_display_item_text_container"):
            title_el = container.find("div", class_="ena_display_item_title")
            date_el = container.find("div", class_="ena_display_item_date")
            content_el = container.find("div", class_="ena_display_item_content")

            link = container.find("a", href=True)
            if not link:
                continue
            href = link["href"]
            if not re.search(r"/(?:eng_|amh_)\d+", href):
                continue
            article_url = utils.ensure_absolute_url(href, "https://www.ena.et")

            title = title_el.get_text(strip=True) if title_el else ""
            summary = content_el.get_text(strip=True) if content_el else ""

            date = None
            view_count = None
            if date_el:
                date_text = date_el.get_text(" ", strip=True)
                date = utils.parse_date(date_text)
                vc = date_el.find("span", class_="ena_display_item_viewcount")
                if vc:
                    try:
                        view_count = int(vc.get_text(strip=True))
                    except ValueError:
                        pass

            thumbnail = ""
            img_container = container.find_previous("div", class_="ena_display_item_image_container")
            if img_container:
                img = img_container.find("img")
                if img and img.get("src"):
                    thumbnail = utils.ensure_absolute_url(img["src"], "https://www.ena.et")

            cards.append({
                "url": article_url,
                "title": title,
                "summary": summary[:500] if summary else "",
                "thumbnail": thumbnail,
                "category": default_category,
                "published_at": date,
                "view_count": view_count,
            })
        return cards

    def _enrich_with_body(self, lang: str, article_id: str, card: dict) -> ScrapeResult | None:
        try:
            soup = _fetch_soup(card["url"], timeout=10)
        except Exception as e:
            logger.warning("Detail fetch failed %s: %s", card["url"], e)
            return None

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else card["title"]

        body, summary = utils.extract_body(soup)
        if not body:
            body = card.get("summary", "")

        image_url = card["thumbnail"] or self._extract_detail_image(soup)

        date = card["published_at"]
        if not date:
            date = utils.parse_date(body)
        if not date:
            date = utils.parse_date(title)

        return ScrapeResult(
            title=title,
            url=card["url"],
            summary=summary[:500] if summary else "",
            body=body,
            image_url=image_url,
            author="",
            category=card["category"],
            language=LANGUAGES[lang]["label"],
            view_count=card["view_count"],
            published_at=date,
            content_hash=utils.make_content_hash(title, summary),
        )

    def _extract_detail_image(self, soup: BeautifulSoup) -> str:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            low = src.lower()
            if "/documents/" not in src:
                continue
            if any(x in low for x in ["global", "icon", "logo", "social", "small", "large"]):
                continue
            return utils.ensure_absolute_url(src, "https://www.ena.et")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        return ""


ScraperRegistry._types["ena_eng"] = ENAArticleScraper
ScraperRegistry._types["ena_amh"] = ENAArticleScraper
