import json
import logging
import os
import threading
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app, Flask, jsonify, request, Response
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import config
from scraper_runner import ScrapeOrchestrator, progress
from supabase_db import SupabaseDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(test_config=None, db=None):
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)

    CORS(app)

    service_key = app.config.get("SUPABASE_SERVICE_KEY", "")
    supabase_url = app.config.get("SUPABASE_URL", "")

    if not db:
        if not supabase_url or not service_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set, "
                "or pass a `db` instance"
            )
        db = SupabaseDB(supabase_url, service_key)

    app.supabase = db

    with app.app_context():
        _seed_sources(db)

    app.register_blueprint(_get_blueprint())
    return app


_source_descriptions: dict[str, str] = {}


def _load_source_config():
    import yaml
    if not os.path.exists(config.SOURCES_CONFIG_PATH):
        logger.warning("Sources config not found at %s", config.SOURCES_CONFIG_PATH)
        return []
    with open(config.SOURCES_CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        return []
    return data.get("sources", [])


def _seed_sources(db):
    global _source_descriptions
    source_defs = _load_source_config()
    for sd in source_defs:
        name = sd["name"]
        if not db.source_exists(name):
            db.add_source(name, sd["url"], sd["scraper_type"])
        if "description" in sd:
            _source_descriptions[name] = sd["description"]


# ---------- routes ----------


def _get_blueprint():
    from flask import Blueprint
    bp = Blueprint("main", __name__)

    @bp.route("/")
    def index():
        return jsonify({
            "name": "The Ethiopia Digest API",
            "endpoints": {
                "GET /api/articles": "Paginated article list (?source=&page=&per_page=)",
                "GET /api/articles/<id>": "Single article detail",
                "GET /api/articles/<id>/related": "Related articles",
                "GET /api/articles/search": "Full-text search (?q=&page=&per_page=)",
                "GET /api/articles/trending": "Most viewed articles",
                "GET /api/categories": "All article categories",
                "GET /api/sources": "List all sources",
                "GET /api/dashboard": "Dashboard stats",
                "GET /api/digest": "Site info and metadata",
                "POST /api/scrape": "Trigger manual scrape",
                "POST /api/scrape/start": "Background scrape",
                "POST /api/scrape/cancel": "Cancel scrape",
                "GET /api/scrape/progress": "SSE progress stream",
                "GET /sitemap.xml": "XML sitemap",
                "GET /robots.txt": "Robots exclusion",
                "GET /rss.xml": "RSS feed",
            },
        })

    @bp.route("/api/articles")
    def list_articles():
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        source_id = request.args.get("source", type=int)
        per_page = min(per_page, 100)

        result = current_app.supabase.list_articles(
            page=page, per_page=per_page, source_id=source_id
        )

        return jsonify({
            "articles": [_serialize_article(a) for a in result["items"]],
            "page": result["page"],
            "pages": result["pages"],
            "total": result["total"],
        })

    @bp.route("/api/articles/<int:article_id>")
    def get_article(article_id):
        article = current_app.supabase.get_article_with_source(article_id)
        if not article:
            return jsonify({"error": "not found"}), 404

        words = len((article.get("body") or "").split())
        reading_time = max(1, round(words / 200))

        current_app.supabase.increment_view_count(article_id)

        source_name = _get_source_name(article)

        result = _serialize_article(article)
        result["reading_time"] = reading_time
        result["source_description"] = _source_descriptions.get(source_name, "")
        return jsonify(result)

    @bp.route("/api/articles/<int:article_id>/related")
    def related_articles(article_id):
        related = current_app.supabase.get_related_articles(article_id)
        if related is None:
            return jsonify({"error": "not found"}), 404
        return jsonify({
            "articles": [
                {
                    "id": a["id"],
                    "title": a["title"],
                    "url": a["url"],
                    "summary": a["summary"],
                    "image_url": a["image_url"],
                    "source": _get_source_name(a),
                    "published_at": a.get("published_at"),
                }
                for a in related
            ],
        })

    @bp.route("/api/sources")
    def list_sources():
        sources = current_app.supabase.list_sources()
        en_count = current_app.supabase.count_articles(language="en")
        am_count = current_app.supabase.count_articles(language="am")
        return jsonify({
            "sources": sources,
            "lang_en": en_count,
            "lang_am": am_count,
        })

    @bp.route("/api/articles/search")
    def search_articles():
        q = request.args.get("q", "").strip()
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 30, type=int)
        per_page = min(per_page, 100)

        if not q:
            return jsonify({"articles": [], "total": 0, "page": 1, "pages": 0})

        result = current_app.supabase.search_articles(q, page=page, per_page=per_page)

        return jsonify({
            "articles": [
                {
                    "id": a["id"],
                    "title": a["title"],
                    "url": a["url"],
                    "summary": a["summary"],
                    "image_url": a["image_url"],
                    "source": _get_source_name(a),
                    "source_id": a.get("source_id"),
                    "author": a.get("author"),
                    "category": a.get("category"),
                    "language": a.get("language"),
                    "published_at": a.get("published_at"),
                }
                for a in result["items"]
            ],
            "page": result["page"],
            "pages": result["pages"],
            "total": result["total"],
        })

    @bp.route("/api/categories")
    def list_categories():
        categories = current_app.supabase.get_categories()
        return jsonify({
            "categories": [
                {"name": name, "count": count}
                for name, count in categories
            ],
        })

    @bp.route("/api/articles/trending")
    def trending_articles():
        articles = current_app.supabase.get_trending()
        return jsonify({
            "articles": [
                {
                    "id": a["id"],
                    "title": a["title"],
                    "url": a["url"],
                    "summary": a["summary"],
                    "image_url": a["image_url"],
                    "source": _get_source_name(a),
                    "view_count": a.get("view_count"),
                    "published_at": a.get("published_at"),
                }
                for a in articles
            ],
        })

    @bp.route("/api/digest")
    def site_digest():
        total = current_app.supabase.count_articles()
        en = current_app.supabase.count_articles(language="en")
        am = current_app.supabase.count_articles(language="am")
        source_count = current_app.supabase.count_sources()
        newest = current_app.supabase.get_latest_article()
        return jsonify({
            "name": "The Ethiopia Digest",
            "description": "Curated news from across Ethiopia's media landscape. English and Amharic articles from independent sources.",
            "total_articles": total,
            "total_sources": source_count,
            "lang_en": en,
            "lang_am": am,
            "newest_article": _serialize_article(newest) if newest else None,
        })

    @bp.route("/sitemap.xml")
    def sitemap():
        articles = current_app.supabase.get_sitemap_articles()
        site_url = request.host_url.rstrip("/")

        urls = [{"loc": site_url, "priority": "1.0"}]
        urls.append({"loc": f"{site_url}/search", "priority": "0.8"})
        urls.append({"loc": f"{site_url}/bookmarks", "priority": "0.3"})

        for a in articles:
            pub = a.get("published_at") or datetime.now(timezone.utc).isoformat()
            urls.append({
                "loc": f"{site_url}/article/{a['id']}",
                "lastmod": pub,
                "priority": "0.9",
            })

        root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for u in urls:
            url_el = ET.SubElement(root, "url")
            loc_el = ET.SubElement(url_el, "loc")
            loc_el.text = u["loc"]
            if "lastmod" in u:
                lm = ET.SubElement(url_el, "lastmod")
                lm.text = u["lastmod"]
            pri = ET.SubElement(url_el, "priority")
            pri.text = u.get("priority", "0.5")

        return Response(ET.tostring(root, encoding="unicode"), mimetype="application/xml")

    @bp.route("/robots.txt")
    def robots():
        site_url = request.host_url.rstrip("/")
        return Response(
            f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n",
            mimetype="text/plain",
        )

    @bp.route("/rss.xml")
    def rss_feed():
        articles = current_app.supabase.get_rss_articles()
        site_url = request.host_url.rstrip("/")
        now_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        items = []
        for a in articles:
            pub = _parse_dt(a.get("published_at"))
            pub_str = pub.strftime("%a, %d %b %Y %H:%M:%S +0000") if pub else now_str
            desc = (a.get("summary") or a.get("body") or "")[:500]
            desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            title = (a.get("title") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            source_name = _get_source_name(a)
            items.append(f"""    <item>
      <title>{title}</title>
      <link>{site_url}/article/{a['id']}</link>
      <guid>{site_url}/article/{a['id']}</guid>
      <pubDate>{pub_str}</pubDate>
      <description>{desc}</description>
      <source>{source_name}</source>
    </item>""")

        rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The Ethiopia Digest</title>
    <link>{site_url}</link>
    <description>Curated news from across Ethiopia's media landscape</description>
    <language>en</language>
    <lastBuildDate>{now_str}</lastBuildDate>
    <atom:link href="{site_url}/rss.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""
        return Response(rss, mimetype="application/rss+xml")

    @bp.route("/api/dashboard")
    def dashboard():
        sources = current_app.supabase.list_sources()
        total_articles = current_app.supabase.count_articles()
        en_count = current_app.supabase.count_articles(language="en")
        am_count = current_app.supabase.count_articles(language="am")

        return jsonify({
            "total_articles": total_articles,
            "total_sources": len(sources),
            "lang_en": en_count,
            "lang_am": am_count,
            "sources": sources,
        })

    @bp.route("/api/scrape/start", methods=["POST"])
    def trigger_scrape_background():
        if progress.is_running():
            return jsonify({"error": "Scrape already in progress"}), 409

        source_id = request.json.get("source_id") if request.is_json else None
        progress.reset()

        thread = threading.Thread(
            target=_run_scrape_background,
            args=(source_id, current_app.supabase),
            daemon=True,
        )
        thread.start()
        return jsonify({"status": "started"}), 202

    @bp.route("/api/scrape/cancel", methods=["POST"])
    def cancel_scrape():
        if not progress.is_running():
            return jsonify({"error": "No scrape in progress"}), 409
        progress.cancel()
        return jsonify({"status": "cancelling"}), 202

    @bp.route("/api/scrape/progress")
    def scrape_progress_sse():
        def generate():
            while True:
                data = progress.data
                yield f"data: {json.dumps(data)}\n\n"
                if not data.get("running") and data.get("current", 0) >= data.get("total", 0) > 0:
                    break
                if not data.get("running") and data.get("total", 0) == 0:
                    break
                import time
                time.sleep(0.5)
        return Response(generate(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })

    @bp.route("/api/scrape", methods=["POST"])
    def trigger_scrape():
        source_id = request.json.get("source_id") if request.is_json else None
        obs = ScrapeOrchestrator(db=current_app.supabase)
        results = obs.run(source_id)
        return jsonify(results), 202

    return bp


def _run_scrape_background(source_id=None, db=None):
    obs = ScrapeOrchestrator(progress_observer=progress, db=db)
    obs.run(source_id)


# ---------- helpers ----------


def _serialize_article(a):
    src = _get_source_name(a)
    return {
        "id": a["id"],
        "title": a["title"],
        "url": a["url"],
        "summary": a.get("summary"),
        "body": a.get("body"),
        "image_url": a.get("image_url"),
        "author": a.get("author"),
        "category": a.get("category"),
        "language": a.get("language"),
        "view_count": a.get("view_count", 0),
        "source": src or "",
        "source_id": a.get("source_id"),
        "published_at": a.get("published_at"),
        "updated_at": a.get("updated_at"),
    }


def _get_source_name(article):
    src = article.get("source")
    if isinstance(src, dict):
        return src.get("name", "")
    return src or ""


def _parse_dt(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            return datetime.strptime(val.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            continue
    return None


# ---------- start (only when env vars are set) ----------

if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"):
    app = create_app()
    orchestrator = ScrapeOrchestrator(db=app.supabase)

    def scheduled_scrape():
        orchestrator.run()

    if not app.config.get("TESTING", False):
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            scheduled_scrape,
            "interval",
            minutes=config.SCRAPE_INTERVAL_MINUTES,
            id="scrape_articles",
        )
        scheduler.start()

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5001))
        app.run(debug=True, port=port)
