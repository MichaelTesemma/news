import json


class TestIndex:
    def test_returns_endpoints(self, client):
        resp = client.get("/")
        data = resp.get_json()
        assert resp.status_code == 200
        assert "endpoints" in data


class TestListArticles:
    def test_empty(self, client):
        resp = client.get("/api/articles")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["articles"] == []
        assert data["total"] == 0

    def test_with_article(self, client, sample_article):
        resp = client.get("/api/articles")
        data = resp.get_json()
        assert len(data["articles"]) == 1
        assert data["articles"][0]["title"] == "Test Article"

    def test_pagination(self, client, db, sample_source):
        from models import Article
        for i in range(5):
            a = Article(
                source_id=sample_source.id,
                title=f"Article {i}",
                url=f"https://example.com/article/{i}",
            )
            db.session.add(a)
        db.session.commit()

        resp = client.get("/api/articles?per_page=2&page=1")
        data = resp.get_json()
        assert len(data["articles"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3

    def test_filter_by_source(self, client, db, sample_source):
        from models import Article, Source
        other = Source(name="Other", url="https://other.com", scraper_type="other")
        db.session.add(other)
        db.session.commit()

        for i in range(3):
            a = Article(source_id=sample_source.id, title=f"A{sample_source.id}-{i}", url=f"https://ex.com/{sample_source.id}-{i}")
            db.session.add(a)
        for i in range(2):
            a = Article(source_id=other.id, title=f"Other-{i}", url=f"https://ex.com/other-{i}")
            db.session.add(a)
        db.session.commit()

        resp = client.get(f"/api/articles?source={sample_source.id}")
        data = resp.get_json()
        assert len(data["articles"]) == 3


class TestGetArticle:
    def test_not_found(self, client):
        resp = client.get("/api/articles/999")
        assert resp.status_code == 404

    def test_returns_article(self, client, sample_article):
        resp = client.get(f"/api/articles/{sample_article.id}")
        data = resp.get_json()
        assert data["title"] == "Test Article"
        assert data["reading_time"] >= 1
        assert "source" in data

    def test_increments_view_count(self, client, sample_article):
        v1 = sample_article.view_count or 0
        client.get(f"/api/articles/{sample_article.id}")
        client.get(f"/api/articles/{sample_article.id}")
        from models import Article, db
        updated = db.session.get(Article, sample_article.id)
        assert (updated.view_count or 0) == v1 + 2


class TestRelatedArticles:
    def test_empty_when_no_siblings(self, client, sample_article):
        resp = client.get(f"/api/articles/{sample_article.id}/related")
        data = resp.get_json()
        assert data["articles"] == []

    def test_returns_siblings(self, client, db, sample_source, sample_article):
        from models import Article
        from datetime import datetime, timezone
        sibling = Article(
            source_id=sample_source.id,
            title="Sibling",
            url="https://example.com/sibling",
            body="Has body content that is long enough for related.",
            published_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        db.session.add(sibling)
        db.session.commit()

        resp = client.get(f"/api/articles/{sample_article.id}/related")
        data = resp.get_json()
        assert len(data["articles"]) == 1
        assert data["articles"][0]["title"] == "Sibling"


class TestListSources:
    def test_empty(self, client):
        resp = client.get("/api/sources")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["sources"] == []

    def test_with_sources(self, client, sample_source):
        resp = client.get("/api/sources")
        data = resp.get_json()
        assert len(data["sources"]) >= 1
        assert data["sources"][0]["name"] == "Test Source"


class TestDashboard:
    def test_returns_stats(self, client, sample_article):
        resp = client.get("/api/dashboard")
        data = resp.get_json()
        assert data["total_articles"] >= 1
        assert data["total_sources"] >= 1


class TestScrape:
    def test_sync_scrape_returns_results(self, client):
        resp = client.post("/api/scrape", content_type="application/json", data=json.dumps({}))
        assert resp.status_code == 202
        data = resp.get_json()
        assert "sources" in data
        assert "total" in data

    def test_cancel_noop_when_not_running(self, client):
        resp = client.post("/api/scrape/cancel")
        assert resp.status_code == 409

    def test_background_start_and_cancel(self, client):
        resp = client.post("/api/scrape/start", content_type="application/json", data=json.dumps({}))
        assert resp.status_code in (202, 409)

        resp = client.post("/api/scrape/cancel")
        assert resp.status_code == 202
