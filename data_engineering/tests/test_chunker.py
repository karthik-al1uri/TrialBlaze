"""Tests for the text chunker."""

from data_engineering.cleaning_chunking.chunker import (
    trail_to_text,
    create_chunk,
    chunk_batch,
)


def test_trail_to_text_basic():
    trail = {
        "name": "Test Trail",
        "trail_type": "Trail",
        "surface": "dirt",
        "difficulty": "moderate",
        "length_miles": 3.0,
        "elevation_gain_ft": 800,
        "min_elevation_ft": 6000,
        "max_elevation_ft": 6800,
        "hiking": True,
        "bike": False,
        "horse": None,
        "dogs": "leashed",
        "manager": "USFS",
        "reviews": [],
    }
    text = trail_to_text(trail)
    assert "Test Trail" in text
    assert "moderate" in text
    assert "3.0 miles" in text
    assert "800 ft" in text
    assert "Hiking: yes" in text
    assert "Biking: no" in text
    assert "USFS" in text


def test_trail_to_text_with_reviews():
    trail = {
        "name": "Review Trail",
        "difficulty": "easy",
        "reviews": ["Great trail!", "Very scenic."],
    }
    text = trail_to_text(trail)
    assert "Great trail!" in text
    assert "Very scenic." in text


def test_create_chunk_has_text_and_metadata():
    trail = {
        "source": "cotrex",
        "cotrex_fid": 1,
        "feature_id": 123,
        "name": "Chunk Trail",
        "difficulty": "hard",
        "length_miles": 5.0,
        "elevation_gain_ft": 2000,
        "surface": "rock",
        "manager": "BLM",
        "hiking": True,
        "bike": False,
        "dogs": "no",
    }
    chunk = create_chunk(trail)
    assert "text" in chunk
    assert "metadata" in chunk
    assert chunk["metadata"]["name"] == "Chunk Trail"
    assert chunk["metadata"]["difficulty"] == "hard"
    assert len(chunk["text"]) > 30


def test_chunk_batch_filters_short():
    trails = [
        {"name": "Good Trail", "difficulty": "easy", "length_miles": 2.0, "manager": "NPS"},
        {"name": "X"},  # Will produce very short text, but still > 30 chars
    ]
    chunks = chunk_batch(trails)
    assert len(chunks) >= 1
    assert all(len(c["text"]) >= 30 for c in chunks)
