"""In-memory fake database for testing.

Implements the same interface as SupabaseDB (post, patch, get, etc.)
using Python lists/dicts.
"""

from datetime import datetime, timezone
from copy import deepcopy


def _auto_id(table):
    if not table:
        return 1
    return max(item["id"] for item in table) + 1


def _matches(item, filters):
    for col, spec in filters.items():
        if isinstance(spec, tuple):
            op, val = spec
        elif isinstance(spec, str):
            parts = spec.split(".", 1)
            if len(parts) != 2:
                continue
            op, val = parts
        else:
            continue
        col_val = item.get(col)
        if col_val is None and op not in ("is",):
            if op == "neq":
                continue
            return False
        if op == "eq":
            if str(col_val) != str(val):
                return False
        elif op == "neq":
            if str(col_val) == str(val):
                return False
        elif op == "gt":
            if not (col_val is not None and int(col_val) > int(val)):
                return False
        elif op == "is":
            if val == "null" and col_val is not None:
                return False
            if val in ("not.null", "not.null") and col_val is None:
                return False
        elif op == "not.is":
            if val == "null" and col_val is None:
                return False
    return True


def _order_key(item, order_spec):
    cols = order_spec.split(",")
    keys = []
    for col_spec in cols:
        parts = col_spec.split(".")
        col = parts[0]
        desc = "desc" in parts
        nullslast = "nullslast" in parts
        val = item.get(col)
        keys.append((0 if nullslast and val is None else (1 if val is not None else 0),
                      val if val is not None else "",
                      0 if desc else 1))
    return keys


class FakeDB:
    def __init__(self):
        self._sources = []
        self._articles = []
        self._next_id = {"sources": 1, "articles": 1}

    def post(self, table, data, return_repr=True):
        items = self._table(table)
        if isinstance(data, dict):
            data = [data]
        results = []
        for item in data:
            row = dict(item)
            row["id"] = self._next_id[table]
            self._next_id[table] += 1
            if table == "sources":
                row.setdefault("enabled", True)
                row.setdefault("last_scraped", None)
            if table == "articles":
                row.setdefault("view_count", 0)
                row.setdefault("scraped_at", datetime.now(timezone.utc).isoformat())
                row.setdefault("updated_at", None)
                row.setdefault("content_hash", None)
                row.setdefault("published_at", None)
                row.setdefault("body", None)
                row.setdefault("summary", None)
                row.setdefault("image_url", None)
                row.setdefault("author", None)
                row.setdefault("category", None)
                row.setdefault("language", None)
            items.append(row)
            results.append(dict(row))
        return results

    def patch(self, table, data, filters):
        items = self._table(table)
        results = []
        for item in items:
            if _matches(item, filters):
                item.update(data)
                results.append(dict(item))
        return results

    def _table(self, name):
        if name == "sources":
            return self._sources
        if name == "articles":
            return self._articles
        raise KeyError(f"Unknown table: {name}")

    # -- Sources -----------------------------------------------------------

    def list_sources(self):
        data = sorted(self._sources, key=lambda s: s.get("name", "") or "")
        for s in data:
            s["article_count"] = sum(
                1 for a in self._articles if a.get("source_id") == s["id"]
            )
        return list(data)

    def get_source(self, source_id):
        for s in self._sources:
            if s["id"] == source_id:
                return dict(s)
        return None

    def get_enabled_sources(self, source_id=None):
        result = [s for s in self._sources if s.get("enabled", True)]
        if source_id is not None:
            result = [s for s in result if s["id"] == source_id]
        return list(result)

    def source_exists(self, name):
        return any(s.get("name") == name for s in self._sources)

    def add_source(self, name, url, scraper_type):
        return self.post("sources", {
            "name": name, "url": url, "scraper_type": scraper_type,
        })[0]

    def update_source_last_scraped(self, source_id):
        now = datetime.now(timezone.utc).isoformat()
        self.patch("sources", {"last_scraped": now}, {"id": f"eq.{source_id}"})

    # -- Articles ----------------------------------------------------------

    def list_articles(self, page=1, per_page=20, source_id=None):
        items = list(self._articles)
        if source_id is not None:
            items = [a for a in items if a.get("source_id") == source_id]
        items.sort(key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = []
        for a in items[start:end]:
            a_copy = dict(a)
            src = self.get_source(a.get("source_id"))
            if src:
                a_copy["source"] = {"id": src["id"], "name": src["name"]}
            page_data.append(a_copy)
        return {
            "items": page_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(0, -(-total // per_page)) if total else 0,
        }

    def get_article(self, article_id):
        for a in self._articles:
            if a["id"] == article_id:
                return dict(a)
        return None

    def get_article_with_source(self, article_id):
        a = self.get_article(article_id)
        if a:
            src = self.get_source(a.get("source_id"))
            if src:
                a["source"] = {"id": src["id"], "name": src["name"], "url": src["url"]}
        return a

    def search_articles(self, q, page=1, per_page=20):
        ql = q.lower()
        items = [
            a for a in self._articles
            if ql in (a.get("title") or "").lower()
            or ql in (a.get("summary") or "").lower()
            or ql in (a.get("body") or "").lower()
            or ql in (a.get("author") or "").lower()
            or ql in (a.get("category") or "").lower()
        ]
        items.sort(key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = []
        for a in items[start:end]:
            a_copy = dict(a)
            src = self.get_source(a.get("source_id"))
            if src:
                a_copy["source"] = {"id": src["id"], "name": src["name"]}
            page_data.append(a_copy)
        return {
            "items": page_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(0, -(-total // per_page)) if total else 0,
        }

    def get_articles_by_urls(self, urls):
        return {a["url"]: dict(a) for a in self._articles if a.get("url") in urls}

    def increment_view_count(self, article_id):
        for a in self._articles:
            if a["id"] == article_id:
                a["view_count"] = (a.get("view_count") or 0) + 1
                return a["view_count"]
        return None

    def get_related_articles(self, article_id, limit=4):
        article = self.get_article(article_id)
        if not article:
            return None
        items = [
            a for a in self._articles
            if a.get("source_id") == article.get("source_id")
            and a["id"] != article_id
            and a.get("body") is not None
            and a.get("body") != ""
        ]
        items.sort(key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        return items[:limit]

    def get_trending(self, limit=10):
        items = [a for a in self._articles if (a.get("view_count") or 0) > 0]
        items.sort(key=lambda a: (
            -(a.get("view_count") or 0),
        ))
        # stable sort preserves insertion order for same view_count
        return items[:limit]

    def count_articles(self, language=None):
        if language:
            return sum(1 for a in self._articles if a.get("language") == language)
        return len(self._articles)

    def count_sources(self):
        return len(self._sources)

    def get_latest_article(self):
        if not self._articles:
            return None
        items = sorted(self._articles, key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        return dict(items[0])

    def get_categories(self):
        counts = {}
        for a in self._articles:
            cat = a.get("category")
            if cat and cat.strip():
                counts[cat] = counts.get(cat, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])

    def get_sitemap_articles(self, limit=5000):
        items = sorted(self._articles, key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        return items[:limit]

    def get_rss_articles(self, limit=50):
        items = sorted(self._articles, key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        return items[:limit]

    def get_articles_for_source(self, source_id):
        return [a for a in self._articles if a.get("source_id") == source_id]

    def get_source_with_counts(self, source_id):
        s = self.get_source(source_id)
        if s:
            s["article_count"] = sum(
                1 for a in self._articles if a.get("source_id") == source_id
            )
        return s

    def get_latest_article_for_source(self, source_id):
        items = [a for a in self._articles if a.get("source_id") == source_id]
        if not items:
            return None
        items.sort(key=lambda a: (
            a.get("published_at") or "",
            -(a["id"]),
        ), reverse=True)
        return items[0]

    def health_check(self):
        return True

    # -- Test helpers ------------------------------------------------------

    def clear(self):
        self._sources.clear()
        self._articles.clear()
        self._next_id = {"sources": 1, "articles": 1}
