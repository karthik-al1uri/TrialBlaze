"""
Trail data normalizer.
Cleans and standardizes raw COTREX API records into a consistent schema
ready for downstream embedding and MongoDB storage.
"""

from typing import Dict, Any, Optional, List


def _clean_string(value: Any) -> str:
    """Strip whitespace; return empty string for None or whitespace-only."""
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s in ("None", "null") else s


def _to_bool_flag(value: Any) -> Optional[bool]:
    """Convert COTREX yes/no/ /blank fields to True/False/None."""
    s = _clean_string(value).lower()
    if s in ("yes",):
        return True
    if s in ("no",):
        return False
    return None


def _meters_to_feet(meters: Optional[float]) -> Optional[float]:
    """Convert meters to feet, rounded to nearest integer."""
    if meters is None or meters == 0:
        return None
    return round(meters * 3.28084)


def _estimate_difficulty(
    elevation_gain_ft: Optional[float],
    length_miles: Optional[float],
) -> str:
    """
    Estimate trail difficulty from elevation gain and distance.
    Simple heuristic — will be refined with more data in later phases.
    """
    if elevation_gain_ft is None or length_miles is None:
        return "unknown"

    if elevation_gain_ft <= 500 and length_miles <= 3:
        return "easy"
    elif elevation_gain_ft <= 1500 and length_miles <= 7:
        return "moderate"
    elif elevation_gain_ft > 1500 or length_miles > 7:
        return "hard"
    return "moderate"


def normalize_trail(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a raw COTREX trail record into standardized schema.

    Input: raw dict from COTREX API (attributes only).
    Output: cleaned dict matching the TrailBlaze schema.
    """
    name = _clean_string(raw.get("name"))
    if not name:
        return {}  # Skip unnamed trails

    min_elev_m = raw.get("min_elevat")
    max_elev_m = raw.get("max_elevat")
    min_elev_ft = _meters_to_feet(min_elev_m)
    max_elev_ft = _meters_to_feet(max_elev_m)

    elevation_gain_ft = None
    if min_elev_ft is not None and max_elev_ft is not None:
        elevation_gain_ft = abs(max_elev_ft - min_elev_ft)

    length_miles = raw.get("length_mi_")
    if length_miles is not None and length_miles <= 0:
        length_miles = None

    difficulty = _estimate_difficulty(elevation_gain_ft, length_miles)

    return {
        "source": "cotrex",
        "cotrex_fid": raw.get("FID"),
        "feature_id": raw.get("feature_id"),
        "name": name,
        "trail_type": _clean_string(raw.get("type")),
        "surface": _clean_string(raw.get("surface")),
        "difficulty": difficulty,
        "length_miles": length_miles,
        "min_elevation_ft": min_elev_ft,
        "max_elevation_ft": max_elev_ft,
        "elevation_gain_ft": elevation_gain_ft,
        "hiking": _to_bool_flag(raw.get("hiking")),
        "horse": _to_bool_flag(raw.get("horse")),
        "bike": _to_bool_flag(raw.get("bike")),
        "motorcycle": _to_bool_flag(raw.get("motorcycle")),
        "atv": _to_bool_flag(raw.get("atv")),
        "dogs": _clean_string(raw.get("dogs")),
        "access": _clean_string(raw.get("access")),
        "manager": _clean_string(raw.get("manager")),
        "url": _clean_string(raw.get("url")),
        "winter_activities": {
            "snowmobile": _to_bool_flag(raw.get("snowmobile")),
            "ski": _to_bool_flag(raw.get("ski")),
            "snowshoe": _to_bool_flag(raw.get("snowshoe")),
        },
        "reviews": [],  # Placeholder for scraped reviews (Task 2 scraper)
    }


def normalize_trailhead(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a raw COTREX trailhead record into standardized schema.
    """
    name = _clean_string(raw.get("name"))
    if not name:
        return {}

    geometry = raw.get("geometry", {})

    return {
        "source": "cotrex",
        "cotrex_fid": raw.get("FID"),
        "feature_id": raw.get("feature_id"),
        "place_id": raw.get("place_id"),
        "name": name,
        "alt_name": _clean_string(raw.get("alt_name")),
        "type": _clean_string(raw.get("type")),
        "bathrooms": _to_bool_flag(raw.get("bathrooms")),
        "fee": _to_bool_flag(raw.get("fee")),
        "water": _to_bool_flag(raw.get("water")),
        "manager": _clean_string(raw.get("manager")),
        "winter_activities": _clean_string(raw.get("winter_act")),
        "geometry": geometry if geometry else None,
    }


def normalize_batch(
    raw_records: List[Dict[str, Any]],
    record_type: str = "trail",
) -> List[Dict[str, Any]]:
    """
    Normalize a batch of raw records. Skips invalid/unnamed records.

    Args:
        raw_records: List of raw COTREX dicts.
        record_type: "trail" or "trailhead".

    Returns:
        List of normalized dicts (empty ones filtered out).
    """
    normalizer = normalize_trail if record_type == "trail" else normalize_trailhead
    results = []
    for raw in raw_records:
        normalized = normalizer(raw)
        if normalized:
            results.append(normalized)
    return results
