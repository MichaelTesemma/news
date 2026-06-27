import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'news.db')}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "15"))
SOURCES_CONFIG_PATH = os.environ.get(
    "SOURCES_CONFIG_PATH",
    os.path.join(BASE_DIR, "sources.yaml"),
)
