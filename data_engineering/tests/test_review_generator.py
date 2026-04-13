"""Tests for the trail review generator."""

from data_engineering.scrapers.review_generator import (
    generate_reviews,
    enrich_trails_with_reviews,
    _pick_rating,
)


SAMPLE_TRAIL = {
    "name": "Test Trail",
    "trail_type": "Trail",
    "surface": "dirt",
    "difficulty": "moderate",
    "length_miles": 4.0,
    "elevation_gain_ft": 1200,
    "hiking": True,
    "bike": True,
    "horse": False,
    "dogs": "leashed",
    "manager": "USFS",
    "winter_activities": {"snowshoe": True, "ski": False, "snowmobile": False},
}


def test_generate_reviews_returns_correct_count():
    reviews = generate_reviews(SAMPLE_TRAIL, num_reviews=3, seed=42)
    assert len(reviews) == 3


def test_generate_reviews_structure():
    reviews = generate_reviews(SAMPLE_TRAIL, num_reviews=2, seed=42)
    for r in reviews:
        assert "text" in r
        assert "rating" in r
        assert "source" in r
        assert r["source"] == "synthetic"
        assert 1 <= r["rating"] <= 5
        assert len(r["text"]) > 10


def test_generate_reviews_uses_trail_attributes():
    reviews = generate_reviews(SAMPLE_TRAIL, num_reviews=5, seed=42)
    all_text = " ".join(r["text"] for r in reviews)
    # At least some reviews should reference trail attributes
    assert len(all_text) > 50


def test_generate_reviews_deterministic_with_seed():
    r1 = generate_reviews(SAMPLE_TRAIL, num_reviews=3, seed=99)
    r2 = generate_reviews(SAMPLE_TRAIL, num_reviews=3, seed=99)
    assert r1 == r2


def test_pick_rating_range():
    for _ in range(100):
        rating = _pick_rating("moderate")
        assert 1 <= rating <= 5


def test_enrich_trails_with_reviews():
    trails = [
        {"name": "Trail A", "difficulty": "easy", "trail_type": "Trail", "surface": "paved"},
        {"name": "Trail B", "difficulty": "hard", "trail_type": "Trail", "surface": "rock"},
    ]
    enriched = enrich_trails_with_reviews(trails, reviews_per_trail=2, seed=42)
    assert len(enriched) == 2
    for t in enriched:
        assert "reviews" in t
        assert len(t["reviews"]) == 2


def test_enrich_preserves_existing_fields():
    trails = [{"name": "Keep Me", "difficulty": "easy", "custom_field": "hello"}]
    enriched = enrich_trails_with_reviews(trails, reviews_per_trail=1, seed=42)
    assert enriched[0]["custom_field"] == "hello"
    assert enriched[0]["name"] == "Keep Me"
