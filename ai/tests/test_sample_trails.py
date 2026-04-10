"""Tests for sample trail data integrity."""

from ai.vector_store.sample_trails import SAMPLE_TRAIL_DOCUMENTS


def test_sample_documents_exist():
    assert len(SAMPLE_TRAIL_DOCUMENTS) >= 10


def test_each_document_has_required_fields():
    required_fields = {"id", "name", "location", "difficulty", "distance_miles", "elevation_gain_ft", "text"}
    for doc in SAMPLE_TRAIL_DOCUMENTS:
        missing = required_fields - set(doc.keys())
        assert not missing, f"Document {doc.get('id', '?')} missing fields: {missing}"


def test_difficulty_values_valid():
    valid = {"easy", "moderate", "hard"}
    for doc in SAMPLE_TRAIL_DOCUMENTS:
        assert doc["difficulty"] in valid, f"{doc['id']} has invalid difficulty: {doc['difficulty']}"


def test_text_is_nonempty():
    for doc in SAMPLE_TRAIL_DOCUMENTS:
        assert len(doc["text"].strip()) > 50, f"{doc['id']} has too-short text"
