"""
AI Trail Narrator — generates a personalized 2-3 sentence hike preview
using GPT-4o-mini based on current weather, season, and trail characteristics.
"""

import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", ".env"))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trails", tags=["narrate"])


class NarrateRequest(BaseModel):
    trail_name: str
    weather_summary: str = ""
    season: str = ""


class NarrateResponse(BaseModel):
    narrative: str


@router.post("/narrate", response_model=NarrateResponse)
async def narrate_trail(req: NarrateRequest):
    """Generate an AI-powered 2-3 sentence hike preview."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return NarrateResponse(
            narrative="AI narrative unavailable — OPENAI_API_KEY not configured."
        )

    try:
        import httpx

        prompt = (
            f"Write a 2-3 sentence hiking preview for {req.trail_name}. "
            f"Current conditions: {req.weather_summary or 'unknown'}. "
            f"Season: {req.season or 'unknown'}. "
            "Be specific, practical, and safety-aware. "
            "Mention what makes today a good or bad day for this trail. "
            "Do not use generic phrases."
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            narrative = data["choices"][0]["message"]["content"].strip()
            return NarrateResponse(narrative=narrative)

    except Exception as e:
        logger.warning(f"Narrate endpoint error: {e}")
        return NarrateResponse(
            narrative="Unable to generate AI preview at this time."
        )
