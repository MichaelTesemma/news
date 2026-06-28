"""Standalone scraper entrypoint for GitHub Actions cron.

Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from environment,
creates a SupabaseDB, and runs the ScrapeOrchestrator.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase_db import SupabaseDB
from scraper_runner import ScrapeOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not service_key:
        print("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    db = SupabaseDB(supabase_url, service_key)
    orchestrator = ScrapeOrchestrator(db=db)
    results = orchestrator.run()
    print(json.dumps(results, indent=2))
    total = results.get("total", 0)
    logger.info("Scrape complete: %d new/updated articles", total)


if __name__ == "__main__":
    main()
