"""
NPS Park Alerts — fetches active alerts from the National Park Service API.
"""

import os
import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", ".env"))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nps", tags=["nps"])


class NPSAlert(BaseModel):
    title: str
    description: str
    category: str
    url: Optional[str] = None


class NPSAlertsResponse(BaseModel):
    alerts: List[NPSAlert]
    park_code: str
    error: Optional[str] = None


@router.get("/alerts", response_model=NPSAlertsResponse)
async def get_nps_alerts(
    park_code: str = Query("romo", description="NPS park code, e.g. romo for Rocky Mountain"),
):
    """Fetch active NPS park alerts."""
    api_key = os.getenv("NPS_API_KEY")
    if not api_key:
        return NPSAlertsResponse(
            alerts=[],
            park_code=park_code,
            error="NPS_API_KEY not configured. Add it to ai/.env to enable park alerts.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://developer.nps.gov/api/v1/alerts",
                params={"parkCode": park_code, "limit": 10},
                headers={"X-Api-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        alerts = []
        for item in data.get("data", []):
            alerts.append(
                NPSAlert(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    category=item.get("category", "Information"),
                    url=item.get("url") or None,
                )
            )

        return NPSAlertsResponse(alerts=alerts, park_code=park_code)

    except Exception as e:
        logger.warning(f"NPS alerts fetch error: {e}")
        return NPSAlertsResponse(
            alerts=[],
            park_code=park_code,
            error="Failed to fetch NPS alerts.",
        )
