import hashlib
import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CUTOFF = datetime(2026, 1, 1, tzinfo=timezone.utc)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

FULL_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}


def parse_date(text: str | None) -> datetime | None:
    if not text:
        return None

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                pass

    m = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})", text, re.I)
    if m:
        month = MONTH_MAP.get(m.group(2).lower()[:3])
        day = int(m.group(1))
        year = int(m.group(3))
        if month:
            try:
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                pass

    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s*(\d{4})", text)
    if m:
        month_str = m.group(1).lower()[:3]
        day = int(m.group(2))
        year = int(m.group(3))
        month = FULL_MONTH_MAP.get(m.group(1).lower())
        if not month:
            month = MONTH_MAP.get(month_str)
        if month:
            try:
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                pass

    return None


def parse_iso_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        cleaned = text.replace("T", " ").split("+")[0].split("Z")[0].strip()
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def ensure_absolute_url(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return base + href
    return base + "/" + href


def make_content_hash(title: str, summary: str) -> str:
    return hashlib.md5(f"{title}{summary}".encode()).hexdigest()


def find_content_container(soup: BeautifulSoup) -> BeautifulSoup:
    content = soup.select_one(
        "div.entry-content, article .entry-content, .post-content, "
        ".td-post-content, .the-post-content, .single-content, "
        "main article, article, .node-content, .field-name-body, "
        "div.RichTextStoryBody, div.wysiwyg, div.article-body, "
        "div.rich-text, div.ena_article_body"
    )
    if not content:
        content = soup.find(
            "div", class_=lambda c: c and "content" in (c or "").lower()
        )
    if not content:
        content = soup.find("article")
    if not content:
        content = soup
    return content


def extract_body(soup: BeautifulSoup, container_selector: str | None = None) -> tuple[str, str]:
    if container_selector:
        content = soup.select_one(container_selector)
        if not content:
            content = find_content_container(soup)
    else:
        content = find_content_container(soup)

    paragraphs = []
    for tag in content.find_all(["p", "h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        if len(text) >= 20 and not tag.find_parent(["nav", "footer", "header"]):
            paragraphs.append(text)
    body = "\n\n".join(paragraphs)
    summary = paragraphs[0][:500] if paragraphs else ""
    return body, summary


def extract_author(soup: BeautifulSoup) -> str:
    el = soup.select_one(
        ".td-post-author-name a, .author, .byline, .entry-author, "
        ".submitted, .td-author"
    )
    if el:
        text = el.get_text(strip=True)
        return text.replace("By ", "", 1).strip()
    return ""


def extract_category(soup: BeautifulSoup, default: str = "general") -> str:
    el = soup.select_one(
        ".td-post-category, .cat-links a, .post-categories a"
    )
    if el:
        return el.get_text(strip=True).lower()
    return default


def extract_image_url(soup: BeautifulSoup) -> str:
    img = soup.select_one(
        ".td-post-featured-image img, article img, .post-thumbnail img, "
        ".wp-post-image, .entry-image img"
    )
    if img:
        src = img.get("data-lazy-src", "") or img.get("src", "") or ""
        if src and "svg" not in src.lower() and "logo" not in src.lower():
            return src
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"]
    return ""


def extract_published_at(soup: BeautifulSoup) -> datetime | None:
    time_el = soup.find("time") or soup.select_one(
        ".entry-date, .date, .td-post-date, .td-module-date, .post-date, "
        "meta[name='date']"
    )
    if time_el:
        if time_el.name == "meta":
            dt_str = time_el.get("content", "")
        else:
            dt_str = time_el.get("datetime", "") or time_el.get_text(strip=True)
        parsed = parse_iso_date(dt_str)
        if parsed:
            return parsed
        return parse_date(dt_str)
    return None
