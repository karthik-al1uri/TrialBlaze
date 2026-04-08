"""
Weather API route — provides current conditions + 4-day forecast for trail locations.
Uses Open-Meteo API (100% free, no API key needed).
"""

import logging
from typing import Optional, List

import requests
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weather", tags=["weather"])

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Light snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Moderate showers", 82: "Heavy showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Severe thunderstorm",
}

WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️", 77: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️", 85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


class DayForecast(BaseModel):
    date: str
    weather_code: int
    weather_desc: str
    weather_icon: str
    temp_high_f: float
    temp_low_f: float
    precipitation_sum_in: float
    snowfall_sum_in: float
    wind_max_mph: float
    precipitation_prob: int


class CurrentWeather(BaseModel):
    temp_f: float
    feels_like_f: float
    humidity_pct: float
    weather_code: int
    weather_desc: str
    weather_icon: str
    wind_mph: float
    wind_gusts_mph: float
    uv_index: float


class WeatherResponse(BaseModel):
    location: str
    lat: float
    lng: float
    current: Optional[CurrentWeather] = None
    forecast: List[DayForecast] = []
    safety_notes: List[str] = []
    hiking_advisory: str = ""
    error: Optional[str] = None


@router.get("", response_model=WeatherResponse)
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    location: str = Query("Trail area", description="Location name"),
):
    """Get current weather + 4-day forecast for a trail location."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": [
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "weather_code", "wind_speed_10m", "wind_gusts_10m", "uv_index",
        ],
        "daily": [
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "snowfall_sum", "wind_speed_10m_max",
            "precipitation_probability_max",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": 4,
        "timezone": "America/Denver",
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Open-Meteo API error: {e}")
        return WeatherResponse(
            location=location, lat=lat, lng=lng,
            error=str(e), hiking_advisory="Weather data unavailable."
        )

    # Parse current
    cur = data.get("current", {})
    wc = cur.get("weather_code", 0)
    current = CurrentWeather(
        temp_f=cur.get("temperature_2m", 0),
        feels_like_f=cur.get("apparent_temperature", 0),
        humidity_pct=cur.get("relative_humidity_2m", 0),
        weather_code=wc,
        weather_desc=WMO_CODES.get(wc, "Unknown"),
        weather_icon=WMO_ICONS.get(wc, "🌤️"),
        wind_mph=cur.get("wind_speed_10m", 0),
        wind_gusts_mph=cur.get("wind_gusts_10m", 0),
        uv_index=cur.get("uv_index", 0),
    )

    # Parse daily forecast
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    forecast = []
    for i, date in enumerate(dates):
        dwc = daily["weather_code"][i] if i < len(daily.get("weather_code", [])) else 0
        forecast.append(DayForecast(
            date=date,
            weather_code=dwc,
            weather_desc=WMO_CODES.get(dwc, "Unknown"),
            weather_icon=WMO_ICONS.get(dwc, "🌤️"),
            temp_high_f=daily["temperature_2m_max"][i] if i < len(daily.get("temperature_2m_max", [])) else 0,
            temp_low_f=daily["temperature_2m_min"][i] if i < len(daily.get("temperature_2m_min", [])) else 0,
            precipitation_sum_in=daily["precipitation_sum"][i] if i < len(daily.get("precipitation_sum", [])) else 0,
            snowfall_sum_in=daily["snowfall_sum"][i] if i < len(daily.get("snowfall_sum", [])) else 0,
            wind_max_mph=daily["wind_speed_10m_max"][i] if i < len(daily.get("wind_speed_10m_max", [])) else 0,
            precipitation_prob=daily["precipitation_probability_max"][i] if i < len(daily.get("precipitation_probability_max", [])) else 0,
        ))

    # Safety notes
    safety_notes = []
    if current.temp_f < 32:
        safety_notes.append("Below freezing — watch for ice on trails.")
    if current.temp_f < 20:
        safety_notes.append("Extreme cold — frostbite risk on exposed skin.")
    if current.temp_f > 95:
        safety_notes.append("Extreme heat — carry extra water, avoid midday hiking.")
    if current.wind_gusts_mph > 40:
        safety_notes.append(f"Dangerous wind gusts ({current.wind_gusts_mph:.0f} mph) — avoid exposed ridges.")
    elif current.wind_gusts_mph > 25:
        safety_notes.append(f"Gusty winds ({current.wind_gusts_mph:.0f} mph) on exposed terrain.")
    if current.uv_index >= 8:
        safety_notes.append(f"Very high UV ({current.uv_index:.0f}) — sunscreen essential.")
    if current.weather_code >= 95:
        safety_notes.append("Active thunderstorms — seek shelter immediately!")
    if current.weather_code in (71, 73, 75, 77, 85, 86):
        safety_notes.append("Snow falling — trails may be slippery, limited visibility.")

    # Check forecast for snow/harsh conditions
    recent_snow = sum(f.snowfall_sum_in for f in forecast[:2])
    recent_precip = sum(f.precipitation_sum_in for f in forecast[:2])
    cold_days = sum(1 for f in forecast[:2] if f.temp_low_f < 20)

    # Hiking advisory
    if recent_snow > 3:
        advisory = f"⚠️ Heavy snow ({recent_snow:.1f}\" in last 2 days) near {location}. Trails likely snow-covered and hazardous. Consider alternatives in lower elevations."
    elif recent_snow > 1:
        advisory = f"❄️ Recent snowfall ({recent_snow:.1f}\") near {location}. Trails may be icy — bring traction devices."
    elif current.weather_code >= 95:
        advisory = f"⛈️ Active storms near {location}. Postpone hiking until conditions clear."
    elif cold_days >= 2 and current.temp_f < 25:
        advisory = f"🥶 Extended cold snap near {location} (below 20°F). Dress in layers, watch for hypothermia."
    elif current.wind_gusts_mph > 50:
        advisory = f"💨 Dangerous winds near {location}. Avoid exposed trails today."
    elif recent_precip > 1:
        advisory = f"🌧️ Heavy recent rainfall near {location}. Trails may be muddy or flooded."
    else:
        advisory = f"✅ Conditions look good for hiking near {location}!"

    return WeatherResponse(
        location=location, lat=lat, lng=lng,
        current=current, forecast=forecast,
        safety_notes=safety_notes, hiking_advisory=advisory,
    )
