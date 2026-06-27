from datetime import datetime, timezone

from bs4 import BeautifulSoup

from scrapers import utils


class TestParseDate:
    def test_month_day_year_format(self):
        result = utils.parse_date("June 15, 2026")
        assert result == datetime(2026, 6, 15, tzinfo=timezone.utc)

    def test_abbreviated_month(self):
        result = utils.parse_date("Jan 5, 2026")
        assert result == datetime(2026, 1, 5, tzinfo=timezone.utc)

    def test_no_comma(self):
        result = utils.parse_date("Mar 20 2026")
        assert result == datetime(2026, 3, 20, tzinfo=timezone.utc)

    def test_mm_dd_yyyy_format(self):
        result = utils.parse_date("12/25/2026")
        assert result == datetime(2026, 12, 25, tzinfo=timezone.utc)

    def test_dd_month_yyyy_format(self):
        result = utils.parse_date("15 June 2026")
        assert result == datetime(2026, 6, 15, tzinfo=timezone.utc)

    def test_none_input(self):
        assert utils.parse_date(None) is None

    def test_empty_string(self):
        assert utils.parse_date("") is None

    def test_invalid_date(self):
        assert utils.parse_date("not a date") is None

    def test_full_month_name(self):
        result = utils.parse_date("February 28, 2026")
        assert result == datetime(2026, 2, 28, tzinfo=timezone.utc)

    def test_with_extra_text(self):
        result = utils.parse_date("Published: Monday, April 10, 2026")
        assert result == datetime(2026, 4, 10, tzinfo=timezone.utc)


class TestParseIsoDate:
    def test_iso_format(self):
        result = utils.parse_iso_date("2026-06-15T10:30:00")
        assert result == datetime(2026, 6, 15, 10, 30, tzinfo=timezone.utc)

    def test_with_z(self):
        result = utils.parse_iso_date("2026-06-15T10:30:00Z")
        assert result == datetime(2026, 6, 15, 10, 30, tzinfo=timezone.utc)

    def test_none_input(self):
        assert utils.parse_iso_date(None) is None


class TestContentHash:
    def test_consistent_hash(self):
        h1 = utils.make_content_hash("Title", "Summary")
        h2 = utils.make_content_hash("Title", "Summary")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = utils.make_content_hash("Title A", "Summary A")
        h2 = utils.make_content_hash("Title B", "Summary B")
        assert h1 != h2


class TestEnsureAbsoluteUrl:
    def test_already_absolute(self):
        assert utils.ensure_absolute_url("https://example.com", "https://base.com") == "https://example.com"

    def test_relative_with_slash(self):
        assert utils.ensure_absolute_url("/path", "https://base.com") == "https://base.com/path"

    def test_relative_without_slash(self):
        assert utils.ensure_absolute_url("path", "https://base.com") == "https://base.com/path"


class TestExtractBody:
    def test_from_article_tag(self):
        html = "<html><body><article><p>This is a paragraph with enough text.</p></article></body></html>"
        soup = BeautifulSoup(html, "lxml")
        body, summary = utils.extract_body(soup)
        assert "This is a paragraph" in body
        assert len(summary) > 0

    def test_skips_short_paragraphs(self):
        html = "<html><body><article><p>Short</p><p>This one is long enough to be included in body extraction.</p></article></body></html>"
        soup = BeautifulSoup(html, "lxml")
        body, summary = utils.extract_body(soup)
        assert "Short" not in body
        assert "long enough" in body

    def test_with_container_selector(self):
        html = '<html><body><div class="entry-content"><p>A paragraph that is definitely long enough to be extracted.</p></div></body></html>'
        soup = BeautifulSoup(html, "lxml")
        body, summary = utils.extract_body(soup, container_selector="div.entry-content")
        assert "A paragraph" in body

    def test_returns_empty_for_no_content(self):
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        body, summary = utils.extract_body(soup)
        assert body == ""


class TestExtractPublishedAt:
    def test_from_time_tag(self):
        html = '<html><body><article><time datetime="2026-06-15T10:00:00Z">June 15, 2026</time></article></body></html>'
        soup = BeautifulSoup(html, "lxml")
        result = utils.extract_published_at(soup)
        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 15

    def test_from_meta_tag(self):
        html = '<html><head><meta name="date" content="2026-06-15"></head><body></body></html>'
        soup = BeautifulSoup(html, "lxml")
        result = utils.extract_published_at(soup)
        assert result is not None

    def test_no_date(self):
        html = "<html><body><p>No date here</p></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert utils.extract_published_at(soup) is None


class TestExtractAuthor:
    def test_from_byline(self):
        html = '<html><body><span class="byline">By John Doe</span></body></html>'
        soup = BeautifulSoup(html, "lxml")
        assert utils.extract_author(soup) == "John Doe"

    def test_no_author(self):
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert utils.extract_author(soup) == ""


class TestExtractImageUrl:
    def test_from_og_image(self):
        html = '<html><head><meta property="og:image" content="https://example.com/image.jpg"></head></html>'
        soup = BeautifulSoup(html, "lxml")
        assert utils.extract_image_url(soup) == "https://example.com/image.jpg"

    def test_no_image(self):
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert utils.extract_image_url(soup) == ""
