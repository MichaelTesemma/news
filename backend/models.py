from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Source(db.Model):
    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    scraper_type = db.Column(db.Text, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    last_scraped = db.Column(db.DateTime, nullable=True)

    articles = db.relationship("Article", backref="source", lazy="dynamic")


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, unique=True, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    body = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    author = db.Column(db.Text, nullable=True)
    category = db.Column(db.Text, nullable=True)
    language = db.Column(db.Text, nullable=True)
    view_count = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime, nullable=True)
    scraped_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    content_hash = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
