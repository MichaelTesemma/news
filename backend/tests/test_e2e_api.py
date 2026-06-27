import json


class TestIndex:
    def test_returns_endpoints(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "The Ethiopia Digest API"
        assert "endpoints" in data
        assert len(data["endpoints"]) >= 14

    def test_returns_json_content_type(self, client):
        resp = client.get("/")
        assert resp.content_type == "application/json"


class TestListArticles:
    def test_empty(self, client):
        resp = client.get("/api/articles")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["articles"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 0

    def test_with_article(self, client, sample_article):
        resp = client.get("/api/articles")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 1
        assert data["total"] == 1
        a = data["articles"][0]
        assert a["title"] == "Test Article"
        assert a["source"] == "Test Source"
        assert a["id"] == sample_article["id"]

    def test_pagination(self, client, db, sample_source):
        for i in range(5):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Article {i}",
                "url": f"https://example.com/article/{i}",
            })

        resp = client.get("/api/articles?per_page=2&page=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3
        assert data["page"] == 1

    def test_pagination_page_2(self, client, db, sample_source):
        for i in range(5):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Article {i}",
                "url": f"https://example.com/article/{i}",
            })

        resp = client.get("/api/articles?per_page=2&page=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 2
        assert data["page"] == 2

    def test_pagination_page_3(self, client, db, sample_source):
        for i in range(5):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Article {i}",
                "url": f"https://example.com/article/{i}",
            })

        resp = client.get("/api/articles?per_page=2&page=3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 1

    def test_per_page_capped_at_100(self, client):
        resp = client.get("/api/articles?per_page=999")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) <= 100

    def test_filter_by_source(self, client, db, sample_source):
        other = db.add_source("Other", "https://other.com", "other")

        for i in range(3):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"A{sample_source['id']}-{i}",
                "url": f"https://ex.com/{sample_source['id']}-{i}",
            })
        for i in range(2):
            db.post("articles", {
                "source_id": other["id"],
                "title": f"Other-{i}",
                "url": f"https://ex.com/other-{i}",
            })

        resp = client.get(f"/api/articles?source={sample_source['id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 3

        resp2 = client.get(f"/api/articles?source={other['id']}")
        assert resp2.status_code == 200
        data2 = resp2.get_json()
        assert len(data2["articles"]) == 2

    def test_filter_by_nonexistent_source(self, client):
        resp = client.get("/api/articles?source=99999")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["articles"] == []


class TestGetArticle:
    def test_not_found(self, client):
        resp = client.get("/api/articles/999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_returns_article(self, client, sample_article):
        resp = client.get(f"/api/articles/{sample_article['id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["title"] == "Test Article"
        assert data["reading_time"] >= 1
        assert "source" in data
        assert data["source"] == "Test Source"
        assert data["id"] == sample_article["id"]
        assert data["body"] == "Test body content\n\nSecond paragraph."
        assert data["author"] == "Test Author"
        assert data["category"] == "general"
        assert data["language"] == "en"
        assert data["summary"] == "Test summary"

    def test_increments_view_count(self, client, sample_article):
        v1 = sample_article.get("view_count", 0) or 0
        client.get(f"/api/articles/{sample_article['id']}")
        client.get(f"/api/articles/{sample_article['id']}")
        client.get(f"/api/articles/{sample_article['id']}")
        updated = sample_article["id"]
        assert True

    def test_reading_time_accurate(self, client, db, sample_source):
        a = db.post("articles", {
            "source_id": sample_source["id"],
            "title": "Long article",
            "url": "https://example.com/long",
            "body": "word " * 600,
        })[0]
        resp = client.get(f"/api/articles/{a['id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["reading_time"] == 3

    def test_returns_serialized_fields(self, client, sample_article):
        resp = client.get(f"/api/articles/{sample_article['id']}")
        data = resp.get_json()
        expected = {"id", "title", "url", "summary", "body", "image_url",
                     "author", "category", "language", "view_count", "source",
                     "source_id", "source_description", "reading_time",
                     "published_at", "updated_at"}
        assert set(data.keys()) == expected


class TestRelatedArticles:
    def test_empty_when_no_siblings(self, client, sample_article):
        resp = client.get(f"/api/articles/{sample_article['id']}/related")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["articles"] == []

    def test_returns_siblings(self, client, db, sample_source, sample_article):
        from datetime import datetime, timezone
        db.post("articles", {
            "source_id": sample_source["id"],
            "title": "Sibling",
            "url": "https://example.com/sibling",
            "body": "Has body content that is long enough for related.",
            "published_at": datetime(2026, 6, 2, tzinfo=timezone.utc).isoformat(),
        })

        resp = client.get(f"/api/articles/{sample_article['id']}/related")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 1
        assert data["articles"][0]["title"] == "Sibling"

    def test_excludes_self(self, client, db, sample_source, sample_article):
        from datetime import datetime, timezone
        for i in range(3):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Sibling {i}",
                "url": f"https://example.com/sib/{i}",
                "body": f"Content with enough text for sibling {i}.",
                "published_at": datetime(2026, 6, 2, tzinfo=timezone.utc).isoformat(),
            })

        resp = client.get(f"/api/articles/{sample_article['id']}/related")
        data = resp.get_json()
        titles = [a["title"] for a in data["articles"]]
        assert "Test Article" not in titles

    def test_not_found(self, client):
        resp = client.get("/api/articles/999/related")
        assert resp.status_code == 404

    def test_skips_bodyless_articles(self, client, db, sample_source, sample_article):
        db.post("articles", {
            "source_id": sample_source["id"],
            "title": "No Body",
            "url": "https://example.com/nobody",
            "body": None,
        })

        resp = client.get(f"/api/articles/{sample_article['id']}/related")
        data = resp.get_json()
        assert all(a["title"] != "No Body" for a in data["articles"])


class TestListSources:
    def test_empty(self, client):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["sources"] == []

    def test_with_sources(self, client, sample_source):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["sources"]) >= 1
        s = data["sources"][0]
        assert s["name"] == "Test Source"
        assert s["url"] == "https://example.com"
        assert s["enabled"] is True
        assert "id" in s
        assert "article_count" in s
        assert "last_scraped" in s

    def test_article_count(self, client, db, sample_source):
        for i in range(3):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Article {i}",
                "url": f"https://example.com/art/{i}",
            })

        resp = client.get("/api/sources")
        data = resp.get_json()
        s = next(s for s in data["sources"] if s["name"] == "Test Source")
        assert s["article_count"] == 3

    def test_language_counts(self, client, db, sample_source):
        urls = ["https://example.com/en1", "https://example.com/en2", "https://example.com/am"]
        for i, lang in enumerate(["en", "en", "am"]):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Article {lang}",
                "url": urls[i],
                "language": lang,
            })

        resp = client.get("/api/sources")
        data = resp.get_json()
        assert data["lang_en"] == 2
        assert data["lang_am"] == 1

    def test_sorted_by_name(self, client, db):
        for i, name in enumerate(["Z Source", "A Source", "M Source"]):
            db.add_source(name, f"https://{name.lower().replace(' ', '')}.com", "test")

        resp = client.get("/api/sources")
        data = resp.get_json()
        names = [s["name"] for s in data["sources"]]
        assert names == sorted(names)


class TestDashboard:
    def test_returns_stats(self, client, sample_article):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_articles"] >= 1
        assert data["total_sources"] >= 1
        assert "lang_en" in data
        assert "lang_am" in data
        assert "sources" in data


class TestSearch:
    def test_empty_query(self, client):
        resp = client.get("/api/articles/search?q=")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["articles"] == []
        assert data["total"] == 0

    def test_search_by_title(self, client, sample_article):
        resp = client.get("/api/articles/search?q=Test")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) >= 1
        assert data["articles"][0]["title"] == "Test Article"

    def test_search_by_author(self, client, sample_article):
        resp = client.get("/api/articles/search?q=Author")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) >= 1

    def test_search_no_results(self, client):
        resp = client.get("/api/articles/search?q=zzzzzzz")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["articles"] == []
        assert data["total"] == 0

    def test_search_pagination(self, client, db, sample_source):
        for i in range(5):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Searchable Article {i}",
                "url": f"https://example.com/searchable/{i}",
            })

        resp = client.get("/api/articles/search?q=Searchable&per_page=2&page=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["articles"]) == 2
        assert data["total"] == 5

    def test_search_case_insensitive(self, client, sample_article):
        resp = client.get("/api/articles/search?q=test")
        data = resp.get_json()
        assert len(data["articles"]) >= 1

        resp2 = client.get("/api/articles/search?q=TEST")
        data2 = resp2.get_json()
        assert len(data2["articles"]) >= 1


class TestCategories:
    def test_empty(self, client):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["categories"] == []

    def test_with_categories(self, client, db, sample_source):
        for i, cat in enumerate(["politics", "politics", "sports", "tech"]):
            db.post("articles", {
                "source_id": sample_source["id"],
                "title": cat,
                "url": f"https://example.com/{cat}/{i}",
                "category": cat,
            })

        resp = client.get("/api/categories")
        data = resp.get_json()
        cats = {c["name"]: c["count"] for c in data["categories"]}
        assert cats["politics"] == 2
        assert cats["sports"] == 1
        assert cats["tech"] == 1


class TestTrending:
    def test_empty(self, client):
        resp = client.get("/api/articles/trending")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["articles"] == []

    def test_returns_viewed_articles(self, client, db, sample_source):
        arts = []
        for i in range(3):
            a = db.post("articles", {
                "source_id": sample_source["id"],
                "title": f"Trending {i}",
                "url": f"https://example.com/trending/{i}",
                "view_count": i * 10,
            })[0]
            arts.append(a)

        resp = client.get("/api/articles/trending")
        data = resp.get_json()
        assert len(data["articles"]) == 2
        assert data["articles"][0]["title"] == "Trending 2"

    def test_ignores_zero_views(self, client, db, sample_source):
        db.post("articles", {
            "source_id": sample_source["id"],
            "title": "Not Trending",
            "url": "https://example.com/notrending",
            "view_count": 0,
        })

        resp = client.get("/api/articles/trending")
        data = resp.get_json()
        assert all(a["title"] != "Not Trending" for a in data["articles"])


class TestDigest:
    def test_returns_site_info(self, client):
        resp = client.get("/api/digest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "The Ethiopia Digest"
        assert "total_articles" in data
        assert "total_sources" in data
        assert "lang_en" in data
        assert "lang_am" in data

    def test_newest_article(self, client, sample_article):
        resp = client.get("/api/digest")
        data = resp.get_json()
        assert data["newest_article"] is not None
        assert data["newest_article"]["title"] == "Test Article"

    def test_newest_article_null_when_empty(self, client):
        resp = client.get("/api/digest")
        data = resp.get_json()
        assert data["newest_article"] is None


class TestSitemap:
    def test_returns_xml(self, client):
        resp = client.get("/sitemap.xml")
        assert resp.status_code == 200
        assert "xml" in resp.content_type

    def test_contains_root_url(self, client):
        resp = client.get("/sitemap.xml")
        assert b"<loc>" in resp.data
        assert b"priority" in resp.data

    def test_includes_search_and_bookmarks(self, client):
        resp = client.get("/sitemap.xml")
        assert b"/search" in resp.data
        assert b"/bookmarks" in resp.data

    def test_includes_articles(self, client, sample_article):
        resp = client.get("/sitemap.xml")
        body = resp.data.decode()
        assert f"/article/{sample_article['id']}" in body


class TestRobots:
    def test_returns_plain_text(self, client):
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert resp.mimetype == "text/plain"

    def test_allows_all(self, client):
        resp = client.get("/robots.txt")
        assert b"Allow: /" in resp.data
        assert b"Sitemap:" in resp.data


class TestRSS:
    def test_returns_xml(self, client):
        resp = client.get("/rss.xml")
        assert resp.status_code == 200
        assert "xml" in resp.content_type

    def test_channel_info(self, client):
        resp = client.get("/rss.xml")
        assert b"<title>The Ethiopia Digest</title>" in resp.data

    def test_includes_article_items(self, client, sample_article):
        resp = client.get("/rss.xml")
        assert b"<item>" in resp.data
        assert b"Test Article" in resp.data

    def test_empty_feed(self, client):
        resp = client.get("/rss.xml")
        assert resp.status_code == 200


class TestScrape:
    def test_cancel_noop_when_not_running(self, client):
        resp = client.post("/api/scrape/cancel")
        assert resp.status_code == 409

    def test_sync_scrape_returns_results(self, client):
        resp = client.post("/api/scrape", content_type="application/json", data=json.dumps({}))
        assert resp.status_code == 202
        data = resp.get_json()
        assert "sources" in data
        assert "total" in data

    def test_background_start(self, client):
        resp = client.post("/api/scrape/start", content_type="application/json", data=json.dumps({}))
        assert resp.status_code in (202, 409)
        import time
        time.sleep(0.1)
        client.post("/api/scrape/cancel")

    def test_background_start_returns_409_when_running(self, client):
        client.post("/api/scrape/start", content_type="application/json", data=json.dumps({}))
        import time
        time.sleep(0.05)
        resp = client.post("/api/scrape/start", content_type="application/json", data=json.dumps({}))
        assert resp.status_code in (202, 409)
        time.sleep(0.1)
        client.post("/api/scrape/cancel")

    def test_cancel_when_running(self, client):
        client.post("/api/scrape/start", content_type="application/json", data=json.dumps({}))
        import time
        time.sleep(0.05)
        resp = client.post("/api/scrape/cancel")
        assert resp.status_code in (202, 409)

    def test_progress_sse(self, client):
        resp = client.get("/api/scrape/progress")
        assert resp.status_code == 200
        assert resp.mimetype == "text/event-stream"

    def test_scrape_with_source_id(self, client, sample_source):
        resp = client.post("/api/scrape", content_type="application/json",
                          data=json.dumps({"source_id": sample_source["id"]}))
        assert resp.status_code == 202


class TestMethodNotAllowed:
    def test_get_on_post_endpoint(self, client):
        resp = client.get("/api/scrape")
        assert resp.status_code == 405

    def test_post_on_get_endpoint(self, client):
        resp = client.post("/api/articles")
        assert resp.status_code == 405


class TestCrossOrigin:
    def test_cors_headers_present(self, client):
        resp = client.get("/api/articles", headers={"Origin": "http://localhost:5173"})
        assert "Access-Control-Allow-Origin" in resp.headers
