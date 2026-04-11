"""
One-time script: Fetch real trail centroids from COTREX ArcGIS and cache
them in MongoDB so the /api/trails/featured endpoint can use accurate
lat/lng instead of manager-region approximations.

Usage:
    python -m backend.scripts.cache_trail_centroids

This queries COTREX in pages of 2000, computes the centroid of each trail
segment, groups by trail name (taking the average centroid when a trail
has multiple segments), and upserts a `trail_centroids` collection.
"""

import asyncio
import logging
import os
import sys
from collections import defaultdict

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env from ai/ directory (shared secrets)
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "ai", ".env")
load_dotenv(_env_path)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

COTREX_URL = (
    "https://services3.arcgis.com/0jWpHMuhmHsukKE3/arcgis/rest/services"
    "/CPW_Trails_08222024/FeatureServer/2/query"
)
PAGE_SIZE = 2000


def fetch_cotrex_page(offset: int) -> list:
    """Fetch one page of trail features with geometry from COTREX."""
    params = {
        "where": "1=1",
        "outFields": "name",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
        "resultRecordCount": PAGE_SIZE,
        "resultOffset": offset,
        "geometryPrecision": 5,
    }
    resp = requests.get(COTREX_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("features", []), data.get("exceededTransferLimit", False)


def compute_centroid(feature: dict) -> tuple:
    """Compute (lat, lng) centroid from a trail feature's geometry paths."""
    geom = feature.get("geometry", {})
    paths = geom.get("paths", [])
    all_pts = [pt for p in paths for pt in p]
    if not all_pts:
        return None, None
    avg_lng = sum(p[0] for p in all_pts) / len(all_pts)
    avg_lat = sum(p[1] for p in all_pts) / len(all_pts)
    return round(avg_lat, 6), round(avg_lng, 6)


async def main():
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.error("MONGO_URI not set in environment.")
        sys.exit(1)

    # Phase 1: Fetch all trail centroids from COTREX
    logger.info("Fetching trail centroids from COTREX ArcGIS...")
    trail_coords = defaultdict(list)  # name -> [(lat, lng), ...]
    offset = 0
    total_features = 0

    while True:
        features, exceeded = fetch_cotrex_page(offset)
        if not features:
            break
        total_features += len(features)
        logger.info(f"  Page at offset {offset}: {len(features)} features (total: {total_features})")

        for feat in features:
            name = (feat.get("attributes", {}).get("name") or "").strip()
            if not name:
                continue
            lat, lng = compute_centroid(feat)
            if lat is not None:
                trail_coords[name].append((lat, lng))

        if not exceeded:
            break
        offset += PAGE_SIZE

    logger.info(f"Fetched {total_features} total features, {len(trail_coords)} unique trail names")

    # Phase 2: Average centroids for trails with multiple segments
    centroids = {}
    for name, coords in trail_coords.items():
        avg_lat = sum(c[0] for c in coords) / len(coords)
        avg_lng = sum(c[1] for c in coords) / len(coords)
        centroids[name] = (round(avg_lat, 6), round(avg_lng, 6))

    logger.info(f"Computed centroids for {len(centroids)} trails")

    # Phase 3: Upsert into MongoDB
    client = AsyncIOMotorClient(mongo_uri)
    db_name = os.getenv("MONGO_DB_NAME", "trailblaze")
    db = client[db_name]
    coll = db["trail_centroids"]

    # Build bulk operations
    from pymongo import UpdateOne
    ops = []
    for name, (lat, lng) in centroids.items():
        ops.append(UpdateOne(
            {"name": name},
            {"$set": {"name": name, "lat": lat, "lng": lng}},
            upsert=True,
        ))

    if ops:
        # Process in chunks of 500
        for i in range(0, len(ops), 500):
            chunk = ops[i:i+500]
            result = await coll.bulk_write(chunk)
            logger.info(f"  Chunk {i//500+1}: upserted {result.upserted_count}, modified {result.modified_count}")

    # Create index on name for fast lookups
    await coll.create_index("name", unique=True)

    total = await coll.count_documents({})
    logger.info(f"Done! {total} trail centroids cached in '{db_name}.trail_centroids'")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
