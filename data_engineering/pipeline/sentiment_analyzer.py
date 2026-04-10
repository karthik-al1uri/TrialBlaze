"""Analyze review sentiment and themes, then cache summary on trail documents.

Usage:
    python -m data_engineering.pipeline.sentiment_analyzer
"""

import argparse
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List

from dotenv import load_dotenv
from pymongo import MongoClient

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover
    pipeline = None


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


THEME_KEYWORDS = {
    "stunning views": ["view", "vista", "scenic", "panorama", "summit"],
    "crowded parking": ["parking", "crowded", "lot", "trailhead"],
    "wildlife sightings": ["bear", "elk", "deer", "eagle", "wildlife"],
    "steep in places": ["steep", "hard", "easy", "challenging"],
    "trail conditions": ["muddy", "snow", "icy", "dry", "wet"],
    "great for dogs": ["dog", "dogs", "pup", "leash"],
}


def _load_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "ai", ".env")
    load_dotenv(env_path)


def _connect_db() -> MongoClient:
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI not found in ai/.env")
    return MongoClient(mongo_uri)


def _build_classifier():
    if pipeline is None:
        raise RuntimeError(
            "transformers is not installed. Install backend dependencies before running sentiment analyzer."
        )
    return pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
    )


def _extract_theme_counts(texts: List[str]) -> Dict[str, int]:
    counter = Counter()
    for text in texts:
        t = text.lower()
        for theme, keywords in THEME_KEYWORDS.items():
            if any(k in t for k in keywords):
                counter[theme] += 1
    return dict(counter.most_common(4))


def analyze_reviews(limit: int | None = None) -> Dict[str, int]:
    _load_env()
    client = _connect_db()
    db_name = os.getenv("MONGO_DB_NAME", "trailblaze")
    db = client[db_name]

    classifier = _build_classifier()

    query = {"body": {"$type": "string", "$ne": ""}}
    cursor = db.reviews.find(query)
    if limit is not None and limit > 0:
        cursor = cursor.limit(limit)

    grouped: Dict[str, List[dict]] = {}
    for review in cursor:
        trail_name = review.get("trail_name")
        if not trail_name:
            continue
        grouped.setdefault(trail_name, []).append(review)

    trails_processed = 0
    reviews_processed = 0

    for trail_name, reviews in grouped.items():
        texts = [r.get("body", "") for r in reviews if r.get("body")]
        if not texts:
            continue

        outputs = classifier(texts, truncation=True)
        positive = sum(1 for o in outputs if o.get("label") == "POSITIVE")
        total = len(outputs)
        positive_pct = round((positive / total) * 100) if total else 0

        themes = _extract_theme_counts(texts)

        sentiment_summary = {
            "positive_pct": positive_pct,
            "themes": themes,
            "last_analyzed": datetime.now(timezone.utc),
            "review_count_analyzed": total,
        }

        update_result = db.trails.update_one(
            {"name": trail_name},
            {"$set": {"sentiment_summary": sentiment_summary}},
        )

        if update_result.matched_count == 0:
            db.trails.update_one(
                {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
                {"$set": {"sentiment_summary": sentiment_summary}},
            )

        trails_processed += 1
        reviews_processed += total

    logger.info("Sentiment analysis complete")
    logger.info(f"Trails processed: {trails_processed}")
    logger.info(f"Reviews analyzed: {reviews_processed}")

    client.close()
    return {
        "trails_processed": trails_processed,
        "reviews_processed": reviews_processed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze sentiment for trail reviews")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of reviews to process",
    )
    args = parser.parse_args()
    analyze_reviews(limit=args.limit)


if __name__ == "__main__":
    main()
