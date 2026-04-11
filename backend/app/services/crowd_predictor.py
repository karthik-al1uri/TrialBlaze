"""Rule-based crowd prediction service."""

from datetime import date, datetime
from typing import Any, Dict


US_FEDERAL_HOLIDAYS_2026 = {
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 10, 12),
    date(2026, 11, 11),
    date(2026, 11, 26),
    date(2026, 12, 25),
}


def _is_holiday(target: date) -> bool:
    return target in US_FEDERAL_HOLIDAYS_2026


def _weather_is_good(forecast_day: Dict[str, Any]) -> bool:
    if not forecast_day:
        return False
    temp_high = float(forecast_day.get("temp_high_f", 0))
    precip = float(forecast_day.get("precipitation_sum_in", 0))
    wind = float(forecast_day.get("wind_max_mph", 0))
    return 45 <= temp_high <= 85 and precip < 0.2 and wind < 20


def predict_crowd(trail: Dict[str, Any], target_date: date, forecast_day: Dict[str, Any] | None = None) -> Dict[str, Any]:
    score = 0

    dow = target_date.weekday()
    if dow in (5, 6):
        score += 40
    elif dow == 4:
        score += 15

    month = target_date.month
    if month in (6, 7, 8):
        score += 25
    elif month in (9, 10):
        score += 15
    elif month in (12, 1, 2):
        score += 5

    difficulty = (trail.get("difficulty") or "").lower()
    length = float(trail.get("length_miles") or 0)
    if difficulty == "easy":
        score += 20
    if 0 < length < 5:
        score += 10

    if _is_holiday(target_date):
        score += 30

    if _weather_is_good(forecast_day or {}):
        score += 15

    score = min(100, score)
    level = (
        "Very Busy" if score >= 75 else
        "Busy" if score >= 50 else
        "Moderate" if score >= 25 else
        "Quiet"
    )

    return {
        "score": score,
        "level": level,
        "best_time": "Before 8am or after 4pm" if score >= 50 else "Anytime",
    }


def parse_target_date(raw: str | None) -> date:
    if not raw:
        return datetime.now().date()
    return datetime.fromisoformat(raw).date()
