"""
Sunrise/Sunset Calculator — uses sunrise-sunset.org free API.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sun", tags=["sun"])


class SunTimesResponse(BaseModel):
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    solar_noon: Optional[str] = None
    day_length: Optional[str] = None
    golden_hour_start: Optional[str] = None
    error: Optional[str] = None


@router.get("", response_model=SunTimesResponse)
async def get_sun_times(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    """Fetch sunrise/sunset times for a given location using sunrise-sunset.org."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.sunrise-sunset.org/json",
                params={"lat": lat, "lng": lng, "formatted": 0},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK":
            return SunTimesResponse(error="API returned non-OK status")

        results = data["results"]
        return SunTimesResponse(
            sunrise=results.get("sunrise"),
            sunset=results.get("sunset"),
            solar_noon=results.get("solar_noon"),
            day_length=str(results.get("day_length", "")),
            golden_hour_start=results.get("golden_hour"),
        )

    except Exception as e:
        logger.warning(f"Sun times fetch error: {e}")
        return SunTimesResponse(error="Failed to fetch sun times.")
