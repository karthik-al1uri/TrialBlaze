"""Refresh cached wildlife alerts on trail documents.

Usage:
    python -m backend.scripts.cache_wildlife_alerts
    python -m backend.scripts.cache_wildlife_alerts --max-trails 200
"""

import argparse
import logging
import os

from dotenv import load_dotenv
from pymongo import MongoClient

from backend.app.services.wildlife_alerts import refresh_wildlife_alert_cache

# Load shared env from ai/.env
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "ai", ".env")
load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main(max_trails: int | None = None):
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI not set in ai/.env")

    client = MongoClient(mongo_uri)
    db_name = os.getenv("MONGO_DB_NAME", "trailblaze")
    db = client[db_name]
    summary = refresh_wildlife_alert_cache(db, max_trails=max_trails)

    logger.info(
        "Wildlife alert cache refreshed: processed=%s alerted=%s",
        summary.get("processed", 0),
        summary.get("alerted", 0),
    )

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cache dangerous wildlife alerts on trails")
    parser.add_argument("--max-trails", type=int, default=None, help="Optional max trails to process")
    args = parser.parse_args()
    main(max_trails=args.max_trails)
