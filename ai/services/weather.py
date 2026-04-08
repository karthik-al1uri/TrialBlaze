"""
Live weather service using Open-Meteo API (100% free, no API key needed).
Fetches current conditions and hourly forecast for Colorado locations.
"""

import logging
from typing import Dict, Any, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Common Colorado hiking locations with coordinates
COLORADO_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "boulder": (40.015, -105.270),
    "denver": (39.739, -104.990),
    "colorado springs": (38.834, -104.821),
    "fort collins": (40.585, -105.084),
    "estes park": (40.377, -105.522),
    "rocky mountain national park": (40.343, -105.688),
    "rmnp": (40.343, -105.688),
    "aspen": (39.191, -106.818),
    "vail": (39.640, -106.374),
    "breckenridge": (39.482, -106.038),
    "telluride": (37.938, -107.812),
    "durango": (37.275, -107.880),
    "glenwood springs": (39.551, -107.325),
    "silverton": (37.812, -107.662),
    "steamboat springs": (40.485, -106.832),
    "crested butte": (38.870, -106.988),
    "leadville": (39.251, -106.293),
    "buena vista": (38.842, -106.131),
    "salida": (38.535, -105.999),
    "pagosa springs": (37.269, -107.010),
    "ouray": (38.023, -107.671),
    "golden": (39.756, -105.221),
    "idaho springs": (39.743, -105.514),
    "evergreen": (39.633, -105.317),
}

# Default: central Colorado
DEFAULT_COORDS = (39.55, -105.55)

# WMO weather code descriptions
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _extract_location(query: str) -> Tuple[float, float, str]:
    """Extract coordinates from query by matching known Colorado locations."""
    q_lower = query.lower()
    for name, coords in COLORADO_LOCATIONS.items():
        if name in q_lower:
            return coords[0], coords[1], name.title()
    return DEFAULT_COORDS[0], DEFAULT_COORDS[1], "Central Colorado"


def fetch_weather(query: str) -> Dict[str, Any]:
    """
    Fetch live weather data from Open-Meteo for a Colorado location.
    Returns a dict with current conditions and safety notes.
    """
    lat, lon, location_name = _extract_location(query)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m",
            "uv_index",
        ],
        "hourly": [
            "temperature_2m",
            "precipitation_probability",
            "weather_code",
            "uv_index",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "forecast_days": 1,
        "timezone": "America/Denver",
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Open-Meteo API error: {e}")
        return {
            "location": location_name,
            "error": str(e),
            "summary": f"Unable to fetch weather for {location_name}. Please check conditions before heading out.",
        }

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    temp_f = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    weather_code = current.get("weather_code", 0)
    wind_speed = current.get("wind_speed_10m")
    wind_gusts = current.get("wind_gusts_10m")
    uv_index = current.get("uv_index")

    sky = WMO_CODES.get(weather_code, "Unknown")

    # Analyze hourly data for afternoon thunderstorm risk
    precip_probs = hourly.get("precipitation_probability", [])
    hourly_codes = hourly.get("weather_code", [])

    # Check afternoon hours (12pm-6pm = indices 12-18)
    afternoon_precip = precip_probs[12:18] if len(precip_probs) > 18 else []
    afternoon_codes = hourly_codes[12:18] if len(hourly_codes) > 18 else []

    max_precip = max(afternoon_precip) if afternoon_precip else 0
    has_thunderstorm = any(c >= 95 for c in afternoon_codes)

    # Build safety notes
    safety_notes = []
    if has_thunderstorm or max_precip > 60:
        safety_notes.append("HIGH lightning risk this afternoon. Plan to be below treeline by noon.")
    elif max_precip > 40:
        safety_notes.append("Moderate rain chance this afternoon. Bring rain gear.")

    if uv_index and uv_index >= 8:
        safety_notes.append(f"Very high UV index ({uv_index}). Wear sunscreen and a hat.")
    elif uv_index and uv_index >= 6:
        safety_notes.append(f"High UV index ({uv_index}). Sunscreen recommended.")

    if wind_gusts and wind_gusts > 40:
        safety_notes.append(f"Strong wind gusts up to {wind_gusts:.0f} mph. Avoid exposed ridges.")
    elif wind_gusts and wind_gusts > 25:
        safety_notes.append(f"Gusty winds up to {wind_gusts:.0f} mph on exposed terrain.")

    if temp_f and temp_f < 32:
        safety_notes.append("Below freezing. Watch for ice on trails.")
    elif temp_f and temp_f > 90:
        safety_notes.append("Very hot. Carry extra water and take shade breaks.")

    # Build summary
    summary_parts = [
        f"Current conditions in {location_name}: {sky}, {temp_f:.0f}°F (feels like {feels_like:.0f}°F).",
        f"Humidity: {humidity:.0f}%. Wind: {wind_speed:.0f} mph.",
    ]

    if max_precip > 0:
        summary_parts.append(f"Afternoon precipitation chance: up to {max_precip}%.")

    if safety_notes:
        summary_parts.append("Safety: " + " ".join(safety_notes))
    else:
        summary_parts.append("Conditions look good for hiking. Stay hydrated!")

    return {
        "location": location_name,
        "temperature_f": temp_f,
        "feels_like_f": feels_like,
        "humidity_pct": humidity,
        "sky_condition": sky,
        "wind_speed_mph": wind_speed,
        "wind_gusts_mph": wind_gusts,
        "uv_index": uv_index,
        "afternoon_precip_max_pct": max_precip,
        "thunderstorm_risk": has_thunderstorm,
        "safety_notes": safety_notes,
        "summary": " ".join(summary_parts),
    }


def fetch_weather_by_coords(lat: float, lng: float, location_name: str = "trail area") -> Dict[str, Any]:
    """
    Fetch live weather for specific coordinates (used when trail location is known).
    Same logic as fetch_weather but skips the location parsing step.
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m",
            "uv_index",
        ],
        "hourly": [
            "temperature_2m",
            "precipitation_probability",
            "weather_code",
            "uv_index",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "forecast_days": 1,
        "timezone": "America/Denver",
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Open-Meteo API error for coords ({lat}, {lng}): {e}")
        return {
            "location": location_name,
            "error": str(e),
            "summary": f"Unable to fetch weather for {location_name}.",
        }

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    temp_f = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    weather_code = current.get("weather_code", 0)
    wind_speed = current.get("wind_speed_10m")
    wind_gusts = current.get("wind_gusts_10m")
    uv_index = current.get("uv_index")

    sky = WMO_CODES.get(weather_code, "Unknown")

    precip_probs = hourly.get("precipitation_probability", [])
    hourly_codes = hourly.get("weather_code", [])
    afternoon_precip = precip_probs[12:18] if len(precip_probs) > 18 else []
    afternoon_codes = hourly_codes[12:18] if len(hourly_codes) > 18 else []
    max_precip = max(afternoon_precip) if afternoon_precip else 0
    has_thunderstorm = any(c >= 95 for c in afternoon_codes)

    safety_notes = []
    if has_thunderstorm or max_precip > 60:
        safety_notes.append("HIGH lightning risk this afternoon. Plan to be below treeline by noon.")
    elif max_precip > 40:
        safety_notes.append("Moderate rain chance this afternoon. Bring rain gear.")
    if uv_index and uv_index >= 8:
        safety_notes.append(f"Very high UV index ({uv_index}). Wear sunscreen and a hat.")
    elif uv_index and uv_index >= 6:
        safety_notes.append(f"High UV index ({uv_index}). Sunscreen recommended.")
    if wind_gusts and wind_gusts > 40:
        safety_notes.append(f"Strong wind gusts up to {wind_gusts:.0f} mph. Avoid exposed ridges.")
    elif wind_gusts and wind_gusts > 25:
        safety_notes.append(f"Gusty winds up to {wind_gusts:.0f} mph on exposed terrain.")
    if temp_f and temp_f < 32:
        safety_notes.append("Below freezing. Watch for ice on trails.")
    elif temp_f and temp_f > 90:
        safety_notes.append("Very hot. Carry extra water and take shade breaks.")

    summary_parts = [
        f"Current conditions near {location_name}: {sky}, {temp_f:.0f}°F (feels like {feels_like:.0f}°F).",
        f"Humidity: {humidity:.0f}%. Wind: {wind_speed:.0f} mph.",
    ]
    if max_precip > 0:
        summary_parts.append(f"Afternoon precipitation chance: up to {max_precip}%.")
    if safety_notes:
        summary_parts.append("Safety: " + " ".join(safety_notes))
    else:
        summary_parts.append("Conditions look good for hiking. Stay hydrated!")

    return {
        "location": location_name,
        "temperature_f": temp_f,
        "feels_like_f": feels_like,
        "humidity_pct": humidity,
        "sky_condition": sky,
        "wind_speed_mph": wind_speed,
        "wind_gusts_mph": wind_gusts,
        "uv_index": uv_index,
        "afternoon_precip_max_pct": max_precip,
        "thunderstorm_risk": has_thunderstorm,
        "safety_notes": safety_notes,
        "summary": " ".join(summary_parts),
    }
