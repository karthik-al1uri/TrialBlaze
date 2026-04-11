"""
One-time pipeline: Fetch real trail photos from Unsplash and cache them
in MongoDB so the /api/photos endpoint serves instantly with zero API calls.

Usage:
    python -m backend.scripts.cache_trail_photos            # full run
    python -m backend.scripts.cache_trail_photos --dry-run   # preview only

Requires UNSPLASH_ACCESS_KEY in ai/.env
Rate limit: 50 requests/hour on free tier.
Strategy: build a filtered nature-only photo pool, then assign to trails.
High-value trails get contextual searches for better photo relevance.
"""

import argparse
import asyncio
import hashlib
import logging
import os
import sys
import time
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env from ai/ directory (shared secrets)
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "ai", ".env")
load_dotenv(_env_path)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

UNSPLASH_BASE = "https://api.unsplash.com"
PHOTOS_PER_TRAIL = 3

# ── Nature-specific search queries ──────────────────────────────
SEARCH_QUERIES = [
    "Colorado mountain trail hiking nature",
    "Rocky Mountain hiking path wilderness",
    "Colorado forest trail trees",
    "alpine trail Colorado mountain peaks",
    "Colorado hiking scenic wilderness",
    "mountain wilderness hiking path",
    "Colorado national forest trail",
    "Colorado trail wildflowers meadow",
    "Colorado mountain peaks alpine hiking",
    "aspen forest trail Colorado autumn",
    "Colorado rocky mountain scenery",
    "hiking trail mountain stream Colorado",
    "Colorado wilderness backpacking trail",
    "mountain lake hiking Colorado",
    "Colorado fourteener hiking summit",
]

# ── Photo quality filter keywords ───────────────────────────────
REJECT_KEYWORDS = [
    "city", "urban", "downtown", "skyline", "building",
    "street", "office", "architecture", "skyscraper",
    "apartment", "highway", "traffic", "business",
    "commercial", "plaza", "hotel", "restaurant",
    "interior", "indoor", "people", "crowd", "portrait",
    "person", "man", "woman", "food", "drink",
]

REQUIRE_KEYWORDS = [
    "mountain", "trail", "hiking", "forest", "nature",
    "landscape", "wilderness", "outdoor", "scenic",
    "trees", "lake", "river", "peak", "alpine",
    "colorado", "rocky", "path", "meadow", "summit",
    "canyon", "waterfall", "backpack", "adventure",
]

# ── High-value trails that get contextual searches ──────────────
HIGH_VALUE_TRAILS = [
    "Bear Lake", "Emerald Lake", "Rocky Mountain",
    "Maroon Bells", "Garden of the Gods", "Hanging Lake",
    "Lost Creek", "Continental Divide", "Colorado Trail",
    "Mount Evans", "Pikes Peak", "Longs Peak",
    "Flat Tops", "Black Canyon", "Great Sand Dunes",
]

MAX_SPECIFIC_SEARCHES = 30  # stay within rate limits per run


def is_valid_nature_photo(photo: dict) -> bool:
    """Filter out non-nature photos using keyword matching."""
    desc = (photo.get("description") or "").lower()
    alt = (photo.get("alt_description") or "").lower()
    combined = desc + " " + alt

    # Reject if any urban keyword found
    if any(kw in combined for kw in REJECT_KEYWORDS):
        return False

    # Accept if any nature keyword found
    if any(kw in combined for kw in REQUIRE_KEYWORDS):
        return True

    # If no keywords match either way, accept by default
    # (better to include than exclude good photos)
    return True


def needs_specific_search(trail_name: str) -> bool:
    """Check if a trail should get its own contextual Unsplash search."""
    return any(
        keyword.lower() in trail_name.lower()
        for keyword in HIGH_VALUE_TRAILS
    )


def build_trail_query(trail: dict) -> str:
    """Build an Unsplash search query tailored to a specific trail."""
    name = trail.get("name", "")
    region = trail.get("region", "Colorado")
    return f"{name} {region} hiking trail scenic"


def fetch_unsplash_photos(query: str, access_key: str, per_page: int = 30, page: int = 1) -> list:
    """Fetch photos from Unsplash search API."""
    resp = requests.get(
        f"{UNSPLASH_BASE}/search/photos",
        params={
            "query": query,
            "per_page": per_page,
            "page": page,
            "orientation": "landscape",
            "content_filter": "high",
        },
        headers={"Authorization": f"Client-ID {access_key}"},
        timeout=15,
    )
    if resp.status_code in (403, 429):
        logger.warning(f"WARNING: Unsplash rate limit reached. Waiting 60 seconds...")
        time.sleep(60)
        return fetch_unsplash_photos(query, access_key, per_page, page)
    resp.raise_for_status()
    data = resp.json()

    photos = []
    for result in data.get("results", []):
        urls = result.get("urls", {})
        user = result.get("user", {})
        desc = result.get("description") or ""
        alt = result.get("alt_description") or ""
        photos.append({
            "url": urls.get("regular", ""),       # 1080px wide
            "thumb_url": urls.get("small", ""),    # 400px wide
            "full_url": urls.get("full", ""),      # original
            "photographer": user.get("name", "Unknown"),
            "photographer_url": user.get("links", {}).get("html", ""),
            "unsplash_link": result.get("links", {}).get("html", ""),
            "description": desc[:200],
            "alt_description": alt[:200],
        })
    return photos


async def main():
    parser = argparse.ArgumentParser(description="Cache trail photos from Unsplash")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview photo pool quality without writing to MongoDB")
    args = parser.parse_args()

    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        logger.error(
            "UNSPLASH_ACCESS_KEY not found in environment.\n"
            "Add it to ai/.env:\n"
            "  UNSPLASH_ACCESS_KEY=your_key_here\n\n"
            "Get your free key at https://unsplash.com/developers"
        )
        sys.exit(1)

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.error("MONGO_URI not set in environment.")
        sys.exit(1)

    client = AsyncIOMotorClient(mongo_uri)
    db_name = os.getenv("MONGO_DB_NAME", "trailblaze")
    db = client[db_name]

    # ── Step 1: Build filtered nature photo pool ────────────────
    print("Building photo pool from Unsplash...")
    raw_pool: List[dict] = []
    seen_urls: set = set()
    rejected_count = 0

    for i, query in enumerate(SEARCH_QUERIES):
        logger.info(f"  [{i+1}/{len(SEARCH_QUERIES)}] Searching: '{query}'")
        try:
            results = fetch_unsplash_photos(query, access_key, per_page=30, page=1)
            for p in results:
                if p["url"] and p["url"] not in seen_urls:
                    seen_urls.add(p["url"])
                    raw_pool.append(p)
            logger.info(f"    Got {len(results)} results, raw pool: {len(raw_pool)}")
        except Exception as e:
            logger.warning(f"    Failed: {e}")

        time.sleep(2.5)

    print(f"Fetched {len(raw_pool)} photos. Filtering for nature content...")

    # Apply nature filter
    photo_pool: List[dict] = []
    for p in raw_pool:
        if is_valid_nature_photo(p):
            photo_pool.append(p)
        else:
            rejected_count += 1

    print(f"Pool size after filtering: {len(photo_pool)} photos (removed {rejected_count} non-nature)")

    if len(photo_pool) < 10:
        logger.error("Too few nature photos in pool. Check API key or adjust filters.")
        sys.exit(1)

    # ── Dry run mode: report and exit ───────────────────────────
    if args.dry_run:
        print("\n=== DRY RUN — PHOTO QUALITY REPORT ===")
        print(f"Total fetched:          {len(raw_pool)}")
        print(f"Rejected (non-nature):  {rejected_count}")
        print(f"Final pool size:        {len(photo_pool)}")
        print(f"\nSample pool photos (first 10 alt_descriptions):")
        for j, p in enumerate(photo_pool[:10]):
            alt = p.get("alt_description", "no description")
            desc = p.get("description", "")
            print(f"  {j+1}. alt: {alt}")
            if desc:
                print(f"     desc: {desc}")
        print("\n=== DRY RUN COMPLETE — no data written to MongoDB ===")
        client.close()
        return

    # ── Step 2: Clear existing bad photo cache ──────────────────
    photo_coll = db["trail_photos"]
    print("Clearing existing photo cache...")
    del_result = await photo_coll.delete_many({})
    print(f"Cleared {del_result.deleted_count} cached photo sets")

    # ── Step 3: Get all trails from MongoDB ─────────────────────
    trail_cursor = db.trails.find(
        {"difficulty": {"$in": ["easy", "moderate", "hard"]}},
        {"_id": 0, "name": 1, "manager": 1, "region": 1},
    )
    trails = await trail_cursor.to_list(length=6000)
    trail_list = [t for t in trails if t.get("name")]
    print(f"Assigning photos to {len(trail_list)} trails...")

    # ── Step 4: Assign photos to trails ─────────────────────────
    from pymongo import UpdateOne

    ops: List = []
    pool_size = len(photo_pool)
    specific_count = 0
    pool_count = 0
    specific_searches_done = 0

    for idx, trail in enumerate(trail_list):
        trail_name = trail["name"]
        assigned: List[dict] = []

        # Try specific search for high-value trails
        if needs_specific_search(trail_name) and specific_searches_done < MAX_SPECIFIC_SEARCHES:
            query = build_trail_query(trail)
            logger.info(f"  Specific search for: {trail_name}")
            try:
                results = fetch_unsplash_photos(query, access_key, per_page=10, page=1)
                valid = [p for p in results if is_valid_nature_photo(p)]
                if len(valid) >= PHOTOS_PER_TRAIL:
                    for j in range(PHOTOS_PER_TRAIL):
                        photo = valid[j]
                        assigned.append({
                            "title": f"{trail_name} - View {j+1}",
                            "url": photo["url"],
                            "thumb_url": photo["thumb_url"],
                            "description": photo.get("description") or "Colorado trail hiking photo",
                            "alt_description": photo.get("alt_description", ""),
                            "photographer": photo["photographer"],
                            "photographer_url": photo["photographer_url"],
                            "unsplash_link": photo["unsplash_link"],
                        })
                    specific_count += 1
                specific_searches_done += 1
                time.sleep(1.5)
            except Exception as e:
                logger.warning(f"    Specific search failed for {trail_name}: {e}")

        # Fall back to pool assignment if no specific photos
        if not assigned:
            seed = int(hashlib.md5(trail_name.encode()).hexdigest(), 16)
            for j in range(PHOTOS_PER_TRAIL):
                pidx = (seed + j * 37) % pool_size
                photo = photo_pool[pidx]
                assigned.append({
                    "title": f"{trail_name} - View {j+1}",
                    "url": photo["url"],
                    "thumb_url": photo["thumb_url"],
                    "description": photo.get("description") or "Colorado trail hiking photo",
                    "alt_description": photo.get("alt_description", ""),
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                    "unsplash_link": photo["unsplash_link"],
                })
            pool_count += 1

        ops.append(UpdateOne(
            {"trail_name": trail_name},
            {"$set": {"trail_name": trail_name, "photos": assigned}},
            upsert=True,
        ))

        if (idx + 1) % 500 == 0:
            logger.info(f"  Prepared {idx + 1}/{len(trail_list)} trails...")

    # ── Step 5: Bulk write to MongoDB ───────────────────────────
    for i in range(0, len(ops), 500):
        chunk = ops[i:i+500]
        result = await photo_coll.bulk_write(chunk)
        logger.info(f"  Chunk {i//500+1}: upserted {result.upserted_count}, modified {result.modified_count}")

    await photo_coll.create_index("trail_name", unique=True)
    total = await photo_coll.count_documents({})

    # ── Quality report ──────────────────────────────────────────
    print("\n=== PHOTO QUALITY REPORT ===")
    print(f"Total trails with photos:      {total}")
    print(f"Trails with specific photos:   {specific_count}")
    print(f"Trails using pool photos:      {pool_count}")
    print(f"Photos rejected (non-nature):  {rejected_count}")
    print(f"Sample pool photos (first 5 alt_descriptions):")
    for j, p in enumerate(photo_pool[:5]):
        alt = p.get("alt_description", "no description")
        print(f"  {j+1}. {alt}")
    print(f"\nDone. {total} trails have photos. {specific_count} used specific search.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
