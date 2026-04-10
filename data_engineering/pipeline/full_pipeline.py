"""
Full data engineering pipeline.

Orchestrates:
  1. Fetch trails + trailheads from COTREX API
  2. Normalize raw records
  3. Deduplicate by trail name
  4. Enrich with synthetic reviews
  5. Chunk for embedding
  6. Save to JSON
  7. (Optional) Load into MongoDB

Usage:
    cd TrailBlaze-AI
    python -m data_engineering.pipeline.full_pipeline [--max-records 2000] [--mongo]
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict

from data_engineering.connectors.cotrex_api import (
    fetch_all_trails,
    fetch_all_trailheads,
    fetch_trail_count,
)
from data_engineering.cleaning_chunking.normalizer import normalize_batch
from data_engineering.cleaning_chunking.chunker import chunk_batch
from data_engineering.scrapers.review_generator import enrich_trails_with_reviews

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")


def deduplicate_trails(trails: list) -> list:
    """
    Deduplicate trail records by name.
    When multiple segments share the same name, merge their attributes:
    - Keep the longest segment's length
    - Combine elevation ranges (min of mins, max of maxs)
    - Recalculate elevation gain
    - Prefer non-empty values for other fields
    """
    grouped = defaultdict(list)
    for trail in trails:
        name = trail.get("name", "").strip().lower()
        if name:
            grouped[name].append(trail)

    deduplicated = []
    for name, segments in grouped.items():
        if len(segments) == 1:
            deduplicated.append(segments[0])
            continue

        # Merge segments
        merged = dict(segments[0])  # Start with first segment

        # Aggregate length (sum all segments)
        lengths = [s.get("length_miles") for s in segments if s.get("length_miles")]
        if lengths:
            merged["length_miles"] = round(sum(lengths), 1)

        # Min/max elevation across all segments
        min_elevs = [s.get("min_elevation_ft") for s in segments if s.get("min_elevation_ft")]
        max_elevs = [s.get("max_elevation_ft") for s in segments if s.get("max_elevation_ft")]
        if min_elevs:
            merged["min_elevation_ft"] = min(min_elevs)
        if max_elevs:
            merged["max_elevation_ft"] = max(max_elevs)
        if min_elevs and max_elevs:
            merged["elevation_gain_ft"] = max(max_elevs) - min(min_elevs)

        # Re-estimate difficulty with merged values
        from data_engineering.cleaning_chunking.normalizer import _estimate_difficulty
        merged["difficulty"] = _estimate_difficulty(
            merged.get("elevation_gain_ft"), merged.get("length_miles")
        )

        # Prefer non-empty values for string fields
        for field in ("surface", "manager", "dogs", "access", "url"):
            for seg in segments:
                val = seg.get(field, "")
                if val:
                    merged[field] = val
                    break

        # Prefer True for boolean activity fields
        for field in ("hiking", "bike", "horse", "motorcycle", "atv"):
            for seg in segments:
                if seg.get(field) is True:
                    merged[field] = True
                    break

        # Use the original-cased name from the first segment
        merged["name"] = segments[0]["name"]
        merged["segment_count"] = len(segments)

        deduplicated.append(merged)

    return deduplicated


def run_full_pipeline(max_records: int = None, load_mongo: bool = False) -> dict:
    """
    Execute the complete data engineering pipeline.

    Returns summary stats dict.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Step 1: Count ---
    total_available = fetch_trail_count()
    logger.info(f"Total named trails in COTREX: {total_available}")

    # --- Step 2: Fetch ---
    logger.info("Fetching trails...")
    raw_trails = fetch_all_trails(max_records=max_records)
    logger.info(f"Raw trails: {len(raw_trails)}")

    logger.info("Fetching trailheads...")
    raw_trailheads = fetch_all_trailheads(max_records=max_records)
    logger.info(f"Raw trailheads: {len(raw_trailheads)}")

    # --- Step 3: Normalize ---
    logger.info("Normalizing...")
    normalized_trails = normalize_batch(raw_trails, record_type="trail")
    logger.info(f"Normalized trails: {len(normalized_trails)}")

    normalized_trailheads = normalize_batch(raw_trailheads, record_type="trailhead")
    logger.info(f"Normalized trailheads: {len(normalized_trailheads)}")

    # --- Step 4: Deduplicate ---
    logger.info("Deduplicating trails by name...")
    unique_trails = deduplicate_trails(normalized_trails)
    logger.info(f"Unique trails after dedup: {len(unique_trails)}")

    # --- Step 5: Enrich with reviews ---
    logger.info("Enriching with synthetic reviews...")
    enriched_trails = enrich_trails_with_reviews(unique_trails, reviews_per_trail=3, seed=42)
    logger.info(f"Enriched trails with reviews: {len(enriched_trails)}")

    # --- Step 6: Chunk for embedding ---
    logger.info("Chunking for embedding...")
    chunks = chunk_batch(enriched_trails)
    logger.info(f"Embedding-ready chunks: {len(chunks)}")

    # --- Step 7: Save JSON ---
    trails_path = os.path.join(OUTPUT_DIR, "trails_enriched.json")
    trailheads_path = os.path.join(OUTPUT_DIR, "trailheads.json")
    chunks_path = os.path.join(OUTPUT_DIR, "chunks_enriched.json")

    with open(trails_path, "w") as f:
        json.dump(enriched_trails, f, indent=2)
    logger.info(f"Saved {len(enriched_trails)} trails -> {trails_path}")

    with open(trailheads_path, "w") as f:
        json.dump(normalized_trailheads, f, indent=2)
    logger.info(f"Saved {len(normalized_trailheads)} trailheads -> {trailheads_path}")

    with open(chunks_path, "w") as f:
        json.dump(chunks, f, indent=2)
    logger.info(f"Saved {len(chunks)} chunks -> {chunks_path}")

    # --- Step 8: Optional MongoDB load ---
    mongo_stats = None
    if load_mongo:
        try:
            from data_engineering.connectors.mongo_loader import (
                load_trails_to_mongo,
                load_trailheads_to_mongo,
            )
            logger.info("Loading into MongoDB...")
            trail_stats = load_trails_to_mongo(enriched_trails)
            th_stats = load_trailheads_to_mongo(normalized_trailheads)
            mongo_stats = {"trails": trail_stats, "trailheads": th_stats}
            logger.info(f"MongoDB: {mongo_stats}")
        except Exception as e:
            logger.warning(f"MongoDB load failed (is MongoDB running?): {e}")

    summary = {
        "total_available": total_available,
        "raw_trails_fetched": len(raw_trails),
        "raw_trailheads_fetched": len(raw_trailheads),
        "normalized_trails": len(normalized_trails),
        "unique_trails_after_dedup": len(unique_trails),
        "enriched_with_reviews": len(enriched_trails),
        "embedding_chunks": len(chunks),
        "mongo_stats": mongo_stats,
    }
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Full TrailBlaze data pipeline")
    parser.add_argument(
        "--max-records", type=int, default=None,
        help="Max records to fetch (default: all)",
    )
    parser.add_argument(
        "--mongo", action="store_true",
        help="Also load results into MongoDB",
    )
    args = parser.parse_args()
    run_full_pipeline(max_records=args.max_records, load_mongo=args.mongo)


if __name__ == "__main__":
    main()
