"""
MongoDB loader for trail data.

Loads normalized and enriched trail/trailhead JSON into MongoDB collections.
Supports upsert to avoid duplicates on re-runs.

Requires a running MongoDB instance. Connection string defaults to localhost
but can be configured via MONGO_URI environment variable.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from ai/ directory (shared across project)
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "ai", ".env")
load_dotenv(_env_path)

# Default connection — overridden via MONGO_URI in .env
DEFAULT_MONGO_URI = "mongodb://localhost:27017"
DEFAULT_DB_NAME = "trailblaze"


def get_mongo_client():
    """Create and return a pymongo MongoClient."""
    from pymongo import MongoClient

    uri = os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)
    logger.info(f"Connecting to MongoDB: {uri[:40]}...")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    # Test the connection
    client.admin.command("ping")
    logger.info("MongoDB connection successful.")
    return client


def load_trails_to_mongo(
    trails: List[Dict[str, Any]],
    db_name: str = DEFAULT_DB_NAME,
    collection_name: str = "trails",
    client=None,
) -> Dict[str, int]:
    """
    Upsert trail records into MongoDB.

    Uses cotrex_fid as the unique key for upsert.

    Returns:
        Dict with counts of inserted, updated, and skipped records.
    """
    if client is None:
        client = get_mongo_client()

    db = client[db_name]
    collection = db[collection_name]

    stats = {"inserted": 0, "updated": 0, "errors": 0}

    for trail in trails:
        try:
            fid = trail.get("cotrex_fid")
            if fid is None:
                stats["errors"] += 1
                continue

            result = collection.update_one(
                {"cotrex_fid": fid},
                {"$set": trail},
                upsert=True,
            )

            if result.upserted_id:
                stats["inserted"] += 1
            elif result.modified_count > 0:
                stats["updated"] += 1

        except Exception as e:
            logger.warning(f"Error upserting trail {trail.get('name')}: {e}")
            stats["errors"] += 1

    logger.info(
        f"MongoDB load complete: {stats['inserted']} inserted, "
        f"{stats['updated']} updated, {stats['errors']} errors"
    )
    return stats


def load_trailheads_to_mongo(
    trailheads: List[Dict[str, Any]],
    db_name: str = DEFAULT_DB_NAME,
    collection_name: str = "trailheads",
    client=None,
) -> Dict[str, int]:
    """
    Upsert trailhead records into MongoDB.

    Uses cotrex_fid as the unique key for upsert.
    """
    if client is None:
        client = get_mongo_client()

    db = client[db_name]
    collection = db[collection_name]

    stats = {"inserted": 0, "updated": 0, "errors": 0}

    for th in trailheads:
        try:
            fid = th.get("cotrex_fid")
            if fid is None:
                stats["errors"] += 1
                continue

            result = collection.update_one(
                {"cotrex_fid": fid},
                {"$set": th},
                upsert=True,
            )

            if result.upserted_id:
                stats["inserted"] += 1
            elif result.modified_count > 0:
                stats["updated"] += 1

        except Exception as e:
            logger.warning(f"Error upserting trailhead {th.get('name')}: {e}")
            stats["errors"] += 1

    logger.info(
        f"MongoDB trailheads load: {stats['inserted']} inserted, "
        f"{stats['updated']} updated, {stats['errors']} errors"
    )
    return stats


def load_json_file_to_mongo(
    json_path: str,
    db_name: str = DEFAULT_DB_NAME,
    collection_name: str = "trails",
    record_type: str = "trail",
) -> Dict[str, int]:
    """
    Load a JSON file directly into MongoDB.

    Args:
        json_path: Path to the JSON file.
        db_name: MongoDB database name.
        collection_name: Target collection name.
        record_type: "trail" or "trailhead".
    """
    with open(json_path, "r") as f:
        records = json.load(f)

    logger.info(f"Loading {len(records)} {record_type}s from {json_path}")

    if record_type == "trailhead":
        return load_trailheads_to_mongo(records, db_name, collection_name)
    return load_trails_to_mongo(records, db_name, collection_name)
