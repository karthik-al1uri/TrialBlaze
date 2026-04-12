"""
AI Trail Narrator — generates a personalized 2-3 sentence hike preview
using GPT-4o-mini based on current weather, season, and trail characteristics.
"""

import os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from multiple likely locations
_this_dir = Path(__file__).resolve().parent
for _candidate in [
    _this_dir / ".." / ".." / ".." / "ai" / ".env",
    _this_dir / ".." / ".." / ".." / ".env",
    Path.cwd() / "ai" / ".env",
]:
    _resolved = _candidate.resolve()
    if _resolved.is_file():
        load_dotenv(_resolved, override=True)
        break

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
        logger.warning("OPENAI_API_KEY not found in env")
        return NarrateResponse(
            narrative="AI narrative unavailable — OPENAI_API_KEY not configured."
        )

    prompt = (
        f"Write a 2-3 sentence hiking preview for {req.trail_name}. "
        f"Current conditions: {req.weather_summary or 'unknown'}. "
        f"Season: {req.season or 'unknown'}. "
        "Be specific, practical, and safety-aware. "
        "Mention what makes today a good or bad day for this trail. "
        "Do not use generic phrases."
    )
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    # Try openai SDK first (more reliable), fall back to httpx
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        completion = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4,
        )
        narrative = completion.choices[0].message.content.strip()
        return NarrateResponse(narrative=narrative)
    except ImportError:
        pass  # openai SDK not installed, try httpx
    except Exception as e:
        logger.warning(f"Narrate (openai SDK) error: {e}")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            narrative = data["choices"][0]["message"]["content"].strip()
            return NarrateResponse(narrative=narrative)
    except Exception as e:
        logger.warning(f"Narrate (httpx) error: {e}")

    return NarrateResponse(
        narrative="Unable to generate AI preview at this time."
    )
