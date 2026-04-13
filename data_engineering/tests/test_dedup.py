"""Tests for trail deduplication logic."""

from data_engineering.pipeline.full_pipeline import deduplicate_trails


def test_no_duplicates_unchanged():
    trails = [
        {"name": "Trail A", "length_miles": 2.0, "min_elevation_ft": 6000, "max_elevation_ft": 7000},
        {"name": "Trail B", "length_miles": 3.0, "min_elevation_ft": 7000, "max_elevation_ft": 8000},
    ]
    result = deduplicate_trails(trails)
    assert len(result) == 2


def test_duplicates_merged_by_name():
    trails = [
        {"name": "Shared Trail", "length_miles": 1.0, "min_elevation_ft": 6000, "max_elevation_ft": 6500, "surface": "dirt"},
        {"name": "Shared Trail", "length_miles": 2.0, "min_elevation_ft": 6200, "max_elevation_ft": 7000, "surface": ""},
    ]
    result = deduplicate_trails(trails)
    assert len(result) == 1
    merged = result[0]
    assert merged["length_miles"] == 3.0  # sum of segments
    assert merged["min_elevation_ft"] == 6000  # min of mins
    assert merged["max_elevation_ft"] == 7000  # max of maxs
    assert merged["elevation_gain_ft"] == 1000
    assert merged["surface"] == "dirt"  # non-empty preferred
    assert merged["segment_count"] == 2


def test_case_insensitive_dedup():
    trails = [
        {"name": "Bear Lake Trail", "length_miles": 1.0},
        {"name": "bear lake trail", "length_miles": 0.5},
    ]
    result = deduplicate_trails(trails)
    assert len(result) == 1
    assert result[0]["name"] == "Bear Lake Trail"  # keeps original case


def test_empty_name_excluded():
    trails = [
        {"name": "", "length_miles": 1.0},
        {"name": "Real Trail", "length_miles": 2.0},
    ]
    result = deduplicate_trails(trails)
    assert len(result) == 1
    assert result[0]["name"] == "Real Trail"


def test_bool_fields_prefer_true():
    trails = [
        {"name": "Multi Seg", "hiking": None, "bike": False},
        {"name": "Multi Seg", "hiking": True, "bike": True},
    ]
    result = deduplicate_trails(trails)
    assert len(result) == 1
    assert result[0]["hiking"] is True
    assert result[0]["bike"] is True
