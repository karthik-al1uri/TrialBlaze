"""Isochrone / Drive-Time Filter API route."""

import logging
import math
import os
from typing import Optional

import requests
from fastapi import APIRouter, Query, HTTPException
from dotenv import load_dotenv

# Load env from ai/.env
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", ".env")
load_dotenv(_env_path)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/isochrone", tags=["isochrone"])


def approximate_isochrone(lat: float, lng: float, duration_minutes: int):
    """Return approximate drive-time polygon as a circle (32 points)."""
    miles = (duration_minutes / 60) * 35
    deg_lat = miles / 69.0
    deg_lng = miles / (69.0 * math.cos(math.radians(lat)))
    points = []
    for i in range(33):
        angle = (i / 32) * 2 * math.pi
        points.append([
            lng + deg_lng * math.cos(angle),
            lat + deg_lat * math.sin(angle),
        ])
    return {
        "type": "Polygon",
        "coordinates": [points],
    }


@router.get("/")
async def get_isochrone(
    lat: float = Query(..., description="Latitude of origin"),
    lng: float = Query(..., description="Longitude of origin"),
    duration_minutes: int = Query(60, description="Drive time in minutes (30/60/90/120)"),
):
    """
    Return a GeoJSON polygon representing the area reachable by car
    within `duration_minutes` from the given lat/lng origin.
    Uses the OpenRouteService Isochrones API.
    """
    ors_key = os.environ.get("ORS_API_KEY", "")
    if not ors_key:
        logger.info("ORS_API_KEY not set — using driving distance approximation")
        return {
            "polygon": approximate_isochrone(lat, lng, duration_minutes),
            "duration_minutes": duration_minutes,
            "center": {"lat": lat, "lng": lng},
            "approximate": True,
            "message": "Drive time filter requires ORS API key. Using distance approximation.",
        }

    url = "https://api.openrouteservice.org/v2/isochrones/driving-car"
    headers = {
        "Authorization": ors_key,
        "Content-Type": "application/json",
    }
    body = {
        "locations": [[lng, lat]],
        "range": [duration_minutes * 60],
        "range_type": "time",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        logger.warning(f"ORS API error: {e} — using driving distance approximation")
        return {
            "polygon": approximate_isochrone(lat, lng, duration_minutes),
            "duration_minutes": duration_minutes,
            "center": {"lat": lat, "lng": lng},
            "approximate": True,
            "message": "ORS API unavailable. Using distance approximation.",
        }
    except Exception as e:
        logger.warning(f"Isochrone request failed: {e} — using approximation")
        return {
            "polygon": approximate_isochrone(lat, lng, duration_minutes),
            "duration_minutes": duration_minutes,
            "center": {"lat": lat, "lng": lng},
            "approximate": True,
            "message": "Isochrone service unavailable. Using distance approximation.",
        }

    # Extract GeoJSON polygon from ORS response
    features = data.get("features", [])
    if not features:
        raise HTTPException(status_code=502, detail="No isochrone polygon returned")

    polygon = features[0].get("geometry")

    return {
        "polygon": polygon,
        "duration_minutes": duration_minutes,
        "center": {"lat": lat, "lng": lng},
    }
