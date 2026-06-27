import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "",
)
SUPABASE_SERVICE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY",
    "",
)

SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "15"))
SOURCES_CONFIG_PATH = os.environ.get(
    "SOURCES_CONFIG_PATH",
    os.path.join(BASE_DIR, "sources.yaml"),
)
