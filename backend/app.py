import json
import logging
import os
import threading
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Blueprint, Flask, jsonify, request, Response
from flask_cors import CORS
from sqlalchemy import func, or_

import config

from models import Article, Source, db
from scraper_runner import ScrapeOrchestrator, progress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)
    CORS(app)
    db.init_app(app)

    with app.app_context():
        _ensure_db(app)
        if not app.config.get("TESTING", False):
            _seed_sources()

    app.register_blueprint(bp)
    return app


def _ensure_db(app):
    db.create_all()


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


SOURCE_DESCRIPTIONS: dict[str, str] = {}


def _seed_sources():
    global SOURCE_DESCRIPTIONS
    source_defs = _load_source_config()
    for sd in source_defs:
        name = sd["name"]
        existing = Source.query.filter_by(name=name).first()
        if existing is None:
            db.session.add(Source(
                name=name,
                url=sd["url"],
                scraper_type=sd["scraper_type"],
            ))
        if "description" in sd:
            SOURCE_DESCRIPTIONS[name] = sd["description"]
    db.session.commit()


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

    query = Article.query.order_by(Article.published_at.desc().nullslast(), Article.id.desc())
    if source_id:
        query = query.filter_by(source_id=source_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "articles": [
            _serialize_article(a)
            for a in pagination.items
        ],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@bp.route("/api/articles/<int:article_id>")
def get_article(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        return jsonify({"error": "not found"}), 404

    words = len((article.body or "").split())
    reading_time = max(1, round(words / 200))

    article.view_count = (article.view_count or 0) + 1
    db.session.commit()

    result = _serialize_article(article)
    result["reading_time"] = reading_time
    result["source_description"] = SOURCE_DESCRIPTIONS.get(article.source.name, "")
    return jsonify(result)


@bp.route("/api/articles/<int:article_id>/related")
def related_articles(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        return jsonify({"error": "not found"}), 404

    related = (
        Article.query
        .filter(
            Article.source_id == article.source_id,
            Article.id != article_id,
            Article.body.isnot(None),
            Article.body != "",
        )
        .order_by(Article.published_at.desc().nullslast(), Article.id.desc())
        .limit(4)
        .all()
    )

    return jsonify({
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "summary": a.summary,
                "image_url": a.image_url,
                "source": a.source.name,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in related
        ],
    })


@bp.route("/api/sources")
def list_sources():
    sources = Source.query.order_by(Source.name).all()
    en_count = Article.query.filter(Article.language == "en").count()
    am_count = Article.query.filter(Article.language == "am").count()
    return jsonify({
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "enabled": s.enabled,
                "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
                "article_count": Article.query.filter_by(source_id=s.id).count(),
            }
            for s in sources
        ],
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

    query = Article.query.filter(
        or_(
            Article.title.ilike(f"%{q}%"),
            Article.summary.ilike(f"%{q}%"),
            Article.body.ilike(f"%{q}%"),
            Article.author.ilike(f"%{q}%"),
            Article.category.ilike(f"%{q}%"),
        )
    ).order_by(Article.published_at.desc().nullslast(), Article.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "summary": a.summary,
                "image_url": a.image_url,
                "source": a.source.name,
                "source_id": a.source_id,
                "author": a.author,
                "category": a.category,
                "language": a.language,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in pagination.items
        ],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@bp.route("/api/categories")
def list_categories():
    rows = (
        db.session.query(Article.category, func.count(Article.id))
        .filter(Article.category.isnot(None), Article.category != "")
        .group_by(Article.category)
        .order_by(func.count(Article.id).desc())
        .all()
    )
    categories = [
        {"name": name, "count": count}
        for name, count in rows
    ]
    return jsonify({"categories": categories})


@bp.route("/api/articles/trending")
def trending_articles():
    articles = (
        Article.query
        .filter(Article.view_count > 0)
        .order_by(Article.view_count.desc(), Article.published_at.desc().nullslast())
        .limit(10)
        .all()
    )
    return jsonify({
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "summary": a.summary,
                "image_url": a.image_url,
                "source": a.source.name,
                "view_count": a.view_count,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in articles
        ],
    })


@bp.route("/api/digest")
def site_digest():
    total = Article.query.count()
    en = Article.query.filter(Article.language == "en").count()
    am = Article.query.filter(Article.language == "am").count()
    source_count = Source.query.count()
    newest = (
        Article.query.order_by(Article.published_at.desc().nullslast())
        .first()
    )
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
    articles = Article.query.order_by(Article.published_at.desc().nullslast()).limit(5000).all()
    site_url = request.host_url.rstrip("/")

    urls = [{"loc": site_url, "priority": "1.0"}]
    urls.append({"loc": f"{site_url}/search", "priority": "0.8"})
    urls.append({"loc": f"{site_url}/bookmarks", "priority": "0.3"})

    for a in articles:
        pub = a.published_at.isoformat() if a.published_at else datetime.now(timezone.utc).isoformat()
        urls.append({
            "loc": f"{site_url}/article/{a.id}",
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
    articles = Article.query.order_by(Article.published_at.desc().nullslast()).limit(50).all()
    site_url = request.host_url.rstrip("/")
    now_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = []
    for a in articles:
        pub = a.published_at.strftime("%a, %d %b %Y %H:%M:%S +0000") if a.published_at else now_str
        desc = (a.summary or a.body or "")[:500]
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        title = (a.title or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        items.append(f"""    <item>
      <title>{title}</title>
      <link>{site_url}/article/{a.id}</link>
      <guid>{site_url}/article/{a.id}</guid>
      <pubDate>{pub}</pubDate>
      <description>{desc}</description>
      <source>{a.source.name}</source>
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
    sources = Source.query.order_by(Source.name).all()
    total_articles = Article.query.count()
    en_count = Article.query.filter(Article.language == "en").count()
    am_count = Article.query.filter(Article.language == "am").count()

    source_data = []
    for s in sources:
        count = Article.query.filter_by(source_id=s.id).count()
        source_data.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "enabled": s.enabled,
            "article_count": count,
            "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
        })

    return jsonify({
        "total_articles": total_articles,
        "total_sources": len(sources),
        "lang_en": en_count,
        "lang_am": am_count,
        "sources": source_data,
    })


@bp.route("/api/scrape/start", methods=["POST"])
def trigger_scrape_background():
    if progress.is_running():
        return jsonify({"error": "Scrape already in progress"}), 409

    source_id = request.json.get("source_id") if request.is_json else None

    progress.reset()

    thread = threading.Thread(
        target=_run_scrape_background,
        args=(source_id,),
        daemon=True,
    )
    thread.start()
    return jsonify({"status": "started"}), 202


def _run_scrape_background(source_id=None):
    with app.app_context():
        obs = ScrapeOrchestrator(progress_observer=progress)
        obs.run(source_id)


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
    obs = ScrapeOrchestrator()
    results = obs.run(source_id)
    return jsonify(results), 202


def _serialize_article(a):
    return {
        "id": a.id,
        "title": a.title,
        "url": a.url,
        "summary": a.summary,
        "body": a.body,
        "image_url": a.image_url,
        "author": a.author,
        "category": a.category,
        "language": a.language,
        "view_count": a.view_count,
        "source": a.source.name,
        "source_id": a.source_id,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


app = create_app()

orchestrator = ScrapeOrchestrator()


def scheduled_scrape():
    with app.app_context():
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
    app.run(debug=True, port=5001)
