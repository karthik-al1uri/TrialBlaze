"""Tests for the trail data normalizer."""

from data_engineering.cleaning_chunking.normalizer import (
    normalize_trail,
    normalize_trailhead,
    normalize_batch,
    _clean_string,
    _to_bool_flag,
    _meters_to_feet,
    _estimate_difficulty,
)


# --- Helper function tests ---

def test_clean_string_normal():
    assert _clean_string("  Boulder  ") == "Boulder"


def test_clean_string_none():
    assert _clean_string(None) == ""


def test_clean_string_whitespace():
    assert _clean_string("   ") == ""


def test_to_bool_flag_yes():
    assert _to_bool_flag("yes") is True


def test_to_bool_flag_no():
    assert _to_bool_flag("no") is False


def test_to_bool_flag_blank():
    assert _to_bool_flag(" ") is None


def test_meters_to_feet():
    assert _meters_to_feet(1000) == 3281


def test_meters_to_feet_none():
    assert _meters_to_feet(None) is None


def test_meters_to_feet_zero():
    assert _meters_to_feet(0) is None


def test_estimate_difficulty_easy():
    assert _estimate_difficulty(300, 2) == "easy"


def test_estimate_difficulty_moderate():
    assert _estimate_difficulty(1000, 5) == "moderate"


def test_estimate_difficulty_hard():
    assert _estimate_difficulty(2000, 10) == "hard"


def test_estimate_difficulty_unknown():
    assert _estimate_difficulty(None, None) == "unknown"


# --- Trail normalization ---

def test_normalize_trail_valid():
    raw = {
        "FID": 1,
        "feature_id": 12345,
        "name": "Royal Arch Trail",
        "type": "Trail",
        "surface": "dirt",
        "hiking": "yes",
        "horse": "no",
        "bike": "no",
        "motorcycle": " ",
        "atv": " ",
        "dogs": "leashed",
        "min_elevat": 1700.0,
        "max_elevat": 2100.0,
        "length_mi_": 3.4,
        "manager": "City of Boulder",
        "access": " ",
        "url": " ",
        "snowmobile": "no",
        "ski": "no",
        "snowshoe": "no",
        "seasonalit": " ",
        "seasonal_1": " ",
        "seasonal_2": " ",
        "seasonal_3": " ",
    }
    result = normalize_trail(raw)
    assert result["name"] == "Royal Arch Trail"
    assert result["source"] == "cotrex"
    assert result["hiking"] is True
    assert result["horse"] is False
    assert result["dogs"] == "leashed"
    assert result["length_miles"] == 3.4
    assert result["elevation_gain_ft"] is not None
    assert result["difficulty"] in ("easy", "moderate", "hard")


def test_normalize_trail_unnamed_returns_empty():
    raw = {"name": " ", "FID": 1}
    assert normalize_trail(raw) == {}


def test_normalize_trail_no_name_returns_empty():
    raw = {"FID": 1}
    assert normalize_trail(raw) == {}


# --- Trailhead normalization ---

def test_normalize_trailhead_valid():
    raw = {
        "FID": 10,
        "feature_id": 99999,
        "place_id": 55,
        "name": "Bear Lake Trailhead",
        "alt_name": " ",
        "type": "Trailhead",
        "bathrooms": "yes",
        "fee": "no",
        "water": "yes",
        "manager": "NPS",
        "winter_act": "snowshoe",
        "geometry": {"x": -105.5, "y": 40.3},
    }
    result = normalize_trailhead(raw)
    assert result["name"] == "Bear Lake Trailhead"
    assert result["bathrooms"] is True
    assert result["fee"] is False
    assert result["geometry"] == {"x": -105.5, "y": 40.3}


# --- Batch normalization ---

def test_normalize_batch_filters_empty():
    raw_list = [
        {"name": "Trail A", "FID": 1, "min_elevat": 2000, "max_elevat": 2500, "length_mi_": 2.0},
        {"name": " ", "FID": 2},
        {"name": "Trail B", "FID": 3, "min_elevat": 1800, "max_elevat": 2200, "length_mi_": 4.0},
    ]
    results = normalize_batch(raw_list, record_type="trail")
    assert len(results) == 2
    assert results[0]["name"] == "Trail A"
    assert results[1]["name"] == "Trail B"
