"""
COTREX data fetch pipeline.
Pulls trail + trailhead data from the COTREX API, normalizes it,
chunks it for embedding, and saves to JSON files.

Usage:
    cd TrailBlaze-AI
    python -m data_engineering.pipeline.fetch_cotrex [--max-records 1000]
"""

import argparse
import json
import logging
import os
import sys

from data_engineering.connectors.cotrex_api import (
    fetch_all_trails,
    fetch_all_trailheads,
    fetch_trail_count,
)
from data_engineering.cleaning_chunking.normalizer import normalize_batch
from data_engineering.cleaning_chunking.chunker import chunk_batch

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")


def run_pipeline(max_records: int = None) -> dict:
    """
    Execute the full COTREX fetch -> normalize -> chunk pipeline.

    Returns summary stats dict.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Step 1: Check total available records ---
    total_available = fetch_trail_count()
    logger.info(f"Total named trails available in COTREX: {total_available}")

    # --- Step 2: Fetch raw trails ---
    logger.info("Fetching trails from COTREX API...")
    raw_trails = fetch_all_trails(max_records=max_records)
    logger.info(f"Raw trails fetched: {len(raw_trails)}")

    # --- Step 3: Fetch raw trailheads ---
    logger.info("Fetching trailheads from COTREX API...")
    raw_trailheads = fetch_all_trailheads(max_records=max_records)
    logger.info(f"Raw trailheads fetched: {len(raw_trailheads)}")

    # --- Step 4: Normalize ---
    logger.info("Normalizing trail records...")
    normalized_trails = normalize_batch(raw_trails, record_type="trail")
    logger.info(f"Normalized trails: {len(normalized_trails)}")

    normalized_trailheads = normalize_batch(raw_trailheads, record_type="trailhead")
    logger.info(f"Normalized trailheads: {len(normalized_trailheads)}")

    # --- Step 5: Chunk for embedding ---
    logger.info("Chunking trails for embedding...")
    chunks = chunk_batch(normalized_trails)
    logger.info(f"Embedding-ready chunks: {len(chunks)}")

    # --- Step 6: Save to JSON ---
    trails_path = os.path.join(OUTPUT_DIR, "cotrex_trails.json")
    trailheads_path = os.path.join(OUTPUT_DIR, "cotrex_trailheads.json")
    chunks_path = os.path.join(OUTPUT_DIR, "cotrex_chunks.json")

    with open(trails_path, "w") as f:
        json.dump(normalized_trails, f, indent=2)
    logger.info(f"Saved trails to {trails_path}")

    with open(trailheads_path, "w") as f:
        json.dump(normalized_trailheads, f, indent=2)
    logger.info(f"Saved trailheads to {trailheads_path}")

    with open(chunks_path, "w") as f:
        json.dump(chunks, f, indent=2)
    logger.info(f"Saved chunks to {chunks_path}")

    summary = {
        "total_available": total_available,
        "raw_trails_fetched": len(raw_trails),
        "raw_trailheads_fetched": len(raw_trailheads),
        "normalized_trails": len(normalized_trails),
        "normalized_trailheads": len(normalized_trailheads),
        "embedding_chunks": len(chunks),
    }
    logger.info(f"\nPipeline Summary: {json.dumps(summary, indent=2)}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Fetch COTREX trail data")
    parser.add_argument(
        "--max-records", type=int, default=None,
        help="Max records to fetch (default: all available)",
    )
    args = parser.parse_args()
    run_pipeline(max_records=args.max_records)


if __name__ == "__main__":
    main()
