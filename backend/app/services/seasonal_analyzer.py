"""Seasonal heatmap analysis service."""

from datetime import date
from typing import Any, Dict

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _month_score(temp_f: float, precip_in: float) -> int:
    score = 100.0

    if temp_f < 20 or temp_f > 95:
        score -= 50
    elif temp_f < 32 or temp_f > 90:
        score -= 30
    elif temp_f < 40 or temp_f > 85:
        score -= 15

    score -= _clamp(precip_in * 25, 0, 35)

    return int(round(_clamp(score, 0, 100)))


def _fetch_weather_monthly(lat: float, lng: float, year: int) -> Dict[int, Dict[str, float]]:
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "daily": ["temperature_2m_mean", "precipitation_sum"],
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Denver",
    }

    resp = requests.get(ARCHIVE_URL, params=params, timeout=20)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})

    times = daily.get("time", [])
    temps = daily.get("temperature_2m_mean", [])
    precs = daily.get("precipitation_sum", [])

    by_month: Dict[int, Dict[str, float]] = {
        m: {"temp_sum": 0.0, "prec_sum": 0.0, "count": 0.0}
        for m in range(1, 13)
    }

    for i, d in enumerate(times):
        month = int(d.split("-")[1])
        by_month[month]["temp_sum"] += float(temps[i]) if i < len(temps) and temps[i] is not None else 0.0
        by_month[month]["prec_sum"] += float(precs[i]) if i < len(precs) and precs[i] is not None else 0.0
        by_month[month]["count"] += 1.0

    out: Dict[int, Dict[str, float]] = {}
    for month, agg in by_month.items():
        days = max(1.0, agg["count"])
        out[month] = {
            "temp_f": agg["temp_sum"] / days,
            "precip_in": agg["prec_sum"] / days,
        }
    return out


def _apply_review_seasonality(monthly_scores: Dict[int, int], review_month_counts: Dict[int, int]) -> Dict[int, int]:
    if not review_month_counts:
        return monthly_scores

    max_count = max(review_month_counts.values())
    adjusted = dict(monthly_scores)
    for month, count in review_month_counts.items():
        boost = round((count / max_count) * 12)
        adjusted[month] = int(_clamp(adjusted[month] + boost, 0, 100))
    return adjusted


async def analyze_seasonal_scores(db, trail_name: str, lat: float, lng: float) -> Dict[str, Any]:
    weather_monthly = _fetch_weather_monthly(lat, lng, year=date.today().year - 1)

    base_scores: Dict[int, int] = {}
    for month in range(1, 13):
        w = weather_monthly[month]
        base_scores[month] = _month_score(w["temp_f"], w["precip_in"])

    review_counts: Dict[int, int] = {}
    review_cursor = db.reviews.find(
        {"trail_name": trail_name, "hike_date": {"$type": "string", "$ne": ""}},
        {"_id": 0, "hike_date": 1},
    )
    reviews = await review_cursor.to_list(length=None)
    for r in reviews:
        hike_date = r.get("hike_date", "")
        try:
            month = int(hike_date.split("-")[1])
            review_counts[month] = review_counts.get(month, 0) + 1
        except Exception:
            continue

    scores = _apply_review_seasonality(base_scores, review_counts)
    sorted_months = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    best_months = [m for m, _ in sorted_months[:4]]
    worst_months = [m for m, _ in sorted_months[-3:]]

    return {
        "best_months": best_months,
        "worst_months": worst_months,
        "monthly_scores": {str(m): scores[m] for m in range(1, 13)},
    }
