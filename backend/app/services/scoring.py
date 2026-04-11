"""TrailBlaze score calculation service."""

from typing import Any, Dict, Optional


SOURCE_SCORES = {
    "NPS": 10,
    "USFS": 8,
    "COTREX": 7,
    "OSM": 5,
}


def calculate_weather_safety(weather: Optional[Dict[str, Any]]) -> float:
    if not weather:
        return 50.0

    score = 100.0
    temp_f = float(weather.get("temp_f", 60))
    wind_mph = float(weather.get("wind_mph", 0))
    precip_in = float(weather.get("precipitation_in", 0))

    if temp_f < 20 or temp_f > 95:
        score -= 35
    elif temp_f < 32 or temp_f > 90:
        score -= 20
    elif temp_f < 40 or temp_f > 85:
        score -= 10

    if wind_mph > 45:
        score -= 30
    elif wind_mph > 30:
        score -= 20
    elif wind_mph > 20:
        score -= 10

    score -= min(25, precip_in * 40)

    return max(0.0, min(100.0, score))


def calculate_trailblaze_score(
    trail: Dict[str, Any],
    reviews: Optional[Dict[str, Any]] = None,
    weather: Optional[Dict[str, Any]] = None,
) -> float:
    score = 50.0

    length = float(trail.get("length_miles") or 0)
    if length > 0:
        score += min(10, length * 1.5)

    elev_gain = float(trail.get("elevation_gain_ft") or 0)
    if elev_gain > 0:
        score += min(10, elev_gain / 200)

    surface = (trail.get("surface") or "").lower()
    if surface in {"paved", "gravel"}:
        score += 5

    dogs = (trail.get("dogs") or "").lower()
    if dogs in {"yes", "on leash", "allowed", "true"}:
        score += 5

    weather_score = calculate_weather_safety(weather)
    score += (weather_score / 100.0) * 20 - 10

    if reviews:
        avg_rating = float(reviews.get("average_rating") or 0)
        total_reviews = int(reviews.get("total_reviews") or 0)
        if avg_rating > 0:
            score += (avg_rating / 5.0) * 15
        if total_reviews > 10:
            score += 5

    source = (trail.get("source") or "").upper()
    score += SOURCE_SCORES.get(source, 5)

    return round(max(0.0, min(100.0, score)), 1)
