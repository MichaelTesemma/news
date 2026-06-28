from datetime import datetime, timezone

import requests


class SupabaseDB:
    def __init__(self, supabase_url, service_key):
        self.url = supabase_url.rstrip("/")
        key = service_key.strip()
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, table, params=None, count=False):
        headers = self._headers.copy()
        if count:
            headers["Prefer"] = "count=exact"
        r = requests.get(
            f"{self.url}/rest/v1/{table}", headers=headers, params=params
        )
        r.raise_for_status()
        data = r.json()
        total = None
        if count and "content-range" in r.headers:
            total = int(r.headers["content-range"].rsplit("/", 1)[-1])
        return data, total

    def post(self, table, data, return_repr=True):
        headers = self._headers.copy()
        if return_repr:
            headers["Prefer"] = "return=representation"
        r = requests.post(
            f"{self.url}/rest/v1/{table}", headers=headers, json=data
        )
        r.raise_for_status()
        return r.json()

    def _upsert(self, table, data, conflict_col):
        r = requests.post(
            f"{self.url}/rest/v1/{table}?on_conflict={conflict_col}",
            headers={
                **self._headers,
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
            json=data,
        )
        r.raise_for_status()
        return r.json()

    def patch(self, table, data, filters):
        params = {col: f"{op}.{val}" for col, (op, val) in filters.items()}
        r = requests.patch(
            f"{self.url}/rest/v1/{table}",
            headers={**self._headers, "Prefer": "return=representation"},
            params=params,
            json=data,
        )
        r.raise_for_status()
        return r.json()

    def _delete(self, table, filters):
        params = {col: f"{op}.{val}" for col, (op, val) in filters.items()}
        r = requests.delete(
            f"{self.url}/rest/v1/{table}", headers=self._headers, params=params
        )
        r.raise_for_status()

    def _paginate_params(self, page, per_page):
        return {"limit": per_page, "offset": (page - 1) * per_page}

    def _page_result(self, data, total, page, per_page):
        t = total or 0
        return {
            "items": data,
            "total": t,
            "page": page,
            "per_page": per_page,
            "pages": max(0, -(-t // per_page)) if t else 0,
        }

    # -- Sources -----------------------------------------------------------

    def list_sources(self):
        data, _ = self._get(
            "sources",
            params={
                "select": "id,name,url,scraper_type,enabled,last_scraped,articles(count)",
                "order": "name.asc",
            },
        )
        for s in data:
            count = (s.pop("articles") or [{}])[0].get("count", 0)
            s["article_count"] = count
        return data

    def get_source(self, source_id):
        data, _ = self._get("sources", params={"id": f"eq.{source_id}"})
        return data[0] if data else None

    def get_enabled_sources(self, source_id=None):
        params = {"enabled": "eq.true", "select": "*", "order": "name.asc"}
        if source_id is not None:
            params["id"] = f"eq.{source_id}"
        data, _ = self._get("sources", params=params)
        return data

    def source_exists(self, name):
        data, _ = self._get("sources", params={"name": f"eq.{name}", "select": "id"})
        return len(data) > 0

    def add_source(self, name, url, scraper_type):
        result = self.post(
            "sources", {"name": name, "url": url, "scraper_type": scraper_type}
        )
        return result[0]

    def update_source_last_scraped(self, source_id):
        now = datetime.now(timezone.utc).isoformat()
        self.patch("sources", {"last_scraped": now}, {"id": ("eq", source_id)})

    # -- Articles ----------------------------------------------------------

    def list_articles(self, page=1, per_page=20, source_id=None):
        params = {
            "select": "*,source:source_id(id,name)",
            "order": "published_at.desc.nullslast,id.desc",
            **self._paginate_params(page, per_page),
        }
        if source_id is not None:
            params["source_id"] = f"eq.{source_id}"
        data, total = self._get("articles", params=params, count=True)
        return self._page_result(data, total, page, per_page)

    def get_article(self, article_id):
        data, _ = self._get("articles", params={"id": f"eq.{article_id}"})
        return data[0] if data else None

    def get_article_with_source(self, article_id):
        data, _ = self._get(
            "articles",
            params={
                "id": f"eq.{article_id}",
                "select": "*,source:source_id(id,name,url)",
            },
        )
        return data[0] if data else None

    def search_articles(self, q, page=1, per_page=20):
        params = {
            "select": "*,source:source_id(id,name)",
            "or": f"(title.ilike.*{q}*,summary.ilike.*{q}*,body.ilike.*{q}*,author.ilike.*{q}*,category.ilike.*{q}*)",
            "order": "published_at.desc.nullslast,id.desc",
            **self._paginate_params(page, per_page),
        }
        data, total = self._get("articles", params=params, count=True)
        return self._page_result(data, total, page, per_page)

    def get_articles_by_urls(self, urls):
        if not urls:
            return {}
        data, _ = self._get(
            "articles",
            params={
                "select": "id,url,content_hash,title,summary,body,image_url,author,category,language,published_at",
                "url": f"in.({','.join(urls)})",
            },
        )
        return {row["url"]: row for row in data}

    def increment_view_count(self, article_id):
        article = self.get_article(article_id)
        if not article:
            return None
        current = (article.get("view_count") or 0) + 1
        self.patch("articles", {"view_count": current}, {"id": ("eq", article_id)})
        return current

    def get_related_articles(self, article_id, limit=4):
        article = self.get_article(article_id)
        if not article:
            return None
        data, _ = self._get(
            "articles",
            params={
                "select": "*",
                "source_id": f"eq.{article['source_id']}",
                "id": f"neq.{article_id}",
                "and": "(body.not.is.null,body.neq.)",
                "order": "published_at.desc.nullslast,id.desc",
                "limit": limit,
            },
        )
        return data

    def get_trending(self, limit=10):
        data, _ = self._get(
            "articles",
            params={
                "select": "*,source:source_id(id,name)",
                "view_count": "gt.0",
                "order": "view_count.desc,published_at.desc.nullslast",
                "limit": limit,
            },
        )
        return data

    def count_articles(self, language=None):
        params = {"select": "id"}
        if language:
            params["language"] = f"eq.{language}"
        _, total = self._get("articles", params=params, count=True)
        return total or 0

    def count_sources(self):
        _, total = self._get("sources", params={"select": "id"}, count=True)
        return total or 0

    def get_latest_article(self):
        data, _ = self._get(
            "articles",
            params={
                "select": "*",
                "order": "published_at.desc.nullslast,id.desc",
                "limit": 1,
            },
        )
        return data[0] if data else None

    def get_newest_article_date(self):
        data, _ = self._get(
            "articles",
            params={
                "select": "published_at",
                "order": "published_at.desc.nullslast",
                "limit": 1,
            },
        )
        return data[0].get("published_at") if data else None

    def get_categories(self):
        """Aggregate category counts via PostgREST distinct + client-side counting."""
        all_articles, _ = self._get(
            "articles",
            params={
                "select": "category",
                "category": "not.is.null",
                "category": "neq.",
            },
        )
        counts = {}
        for a in all_articles:
            cat = a.get("category")
            if cat:
                counts[cat] = counts.get(cat, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])

    def upsert_articles(self, articles):
        """Bulk insert-or-update articles by url."""
        if not articles:
            return []
        return self._upsert("articles", articles, "url")

    def get_sitemap_articles(self, limit=5000):
        data, _ = self._get(
            "articles",
            params={
                "select": "id,title,url,updated_at",
                "order": "published_at.desc.nullslast,id.desc",
                "limit": limit,
            },
        )
        return data

    def get_rss_articles(self, limit=50):
        data, _ = self._get(
            "articles",
            params={
                "select": "*",
                "order": "published_at.desc.nullslast,id.desc",
                "limit": limit,
            },
        )
        return data

    def get_articles_for_source(self, source_id):
        data, _ = self._get(
            "articles",
            params={
                "select": "id,title",
                "source_id": f"eq.{source_id}",
            },
        )
        return data

    def get_source_with_counts(self, source_id):
        data, _ = self._get(
            "sources",
            params={
                "id": f"eq.{source_id}",
                "select": "*,articles(count)",
            },
        )
        if not data:
            return None
        s = data[0]
        s["article_count"] = (s.pop("articles") or [{}])[0].get("count", 0)
        return s

    def get_latest_article_for_source(self, source_id):
        data, _ = self._get(
            "articles",
            params={
                "select": "published_at",
                "source_id": f"eq.{source_id}",
                "order": "published_at.desc.nullslast,id.desc",
                "limit": 1,
            },
        )
        return data[0] if data else None

    # -- Admin / lifecycle -------------------------------------------------

    def health_check(self):
        try:
            self.count_sources()
            return True
        except requests.RequestException:
            return False
