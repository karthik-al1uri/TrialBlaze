"""Itinerary persistence API routes."""

import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", ".env"))

logger = logging.getLogger(__name__)

from backend.app.database import get_db
from backend.app.models.itinerary import (
    ItineraryCreate,
    ItineraryResponse,
    ItineraryListResponse,
)

router = APIRouter(prefix="/api/itineraries", tags=["itineraries"])


@router.post("", response_model=ItineraryResponse, status_code=201)
async def create_itinerary(body: ItineraryCreate):
    """Create a new itinerary."""
    db = get_db()
    now = datetime.now(timezone.utc)
    itinerary = {
        "itinerary_id": str(uuid.uuid4()),
        "title": body.title,
        "session_id": body.session_id,
        "trails": [t.model_dump() for t in body.trails],
        "created_at": now,
        "updated_at": now,
    }
    await db.itineraries.insert_one(itinerary)
    return ItineraryResponse(**itinerary)


@router.get("", response_model=ItineraryListResponse)
async def list_itineraries():
    """List all itineraries."""
    db = get_db()
    cursor = db.itineraries.find({}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(length=100)
    return ItineraryListResponse(
        itineraries=[ItineraryResponse(**i) for i in items],
        total=len(items),
    )


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(itinerary_id: str):
    """Get a single itinerary."""
    db = get_db()
    item = await db.itineraries.find_one(
        {"itinerary_id": itinerary_id}, {"_id": 0}
    )
    if not item:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return ItineraryResponse(**item)


@router.delete("/{itinerary_id}", status_code=204)
async def delete_itinerary(itinerary_id: str):
    """Delete an itinerary."""
    db = get_db()
    result = await db.itineraries.delete_one({"itinerary_id": itinerary_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Itinerary not found")


class GenerateItineraryRequest(BaseModel):
    days: int = 3
    difficulty: Optional[str] = None
    region: Optional[str] = None
    interests: Optional[str] = None


@router.post("/generate")
async def generate_itinerary(req: GenerateItineraryRequest):
    """AI-powered itinerary generation using GPT-4o-mini."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"itinerary": "AI itinerary unavailable — OPENAI_API_KEY not configured.", "days": req.days}

    # Fetch a sample of trails from DB to ground the AI
    db = get_db()
    query: dict = {}
    if req.difficulty:
        query["difficulty"] = req.difficulty.lower()
    pipeline = [{"$match": query}, {"$sample": {"size": 15}}, {"$project": {"_id": 0, "name": 1, "difficulty": 1, "length_miles": 1, "elevation_gain_ft": 1, "nearby_city": 1, "surface": 1}}]
    sample_trails = await db.trails.aggregate(pipeline).to_list(length=15)

    trail_list = "\n".join(
        f"- {t['name']} ({t.get('difficulty','?')}, {t.get('length_miles','?')} mi, near {t.get('nearby_city','?')})"
        for t in sample_trails
    )

    try:
        import httpx

        prompt = (
            f"Create a {req.days}-day Colorado hiking itinerary.\n"
            f"Difficulty preference: {req.difficulty or 'any'}\n"
            f"Region: {req.region or 'anywhere in Colorado'}\n"
            f"Interests: {req.interests or 'general hiking'}\n\n"
            f"Use ONLY trails from this list:\n{trail_list}\n\n"
            "For each day, include: trail name, estimated time, what to pack, and a tip.\n"
            "Format with markdown. Be concise and practical."
        )

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.5,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            itinerary_text = data["choices"][0]["message"]["content"].strip()
            return {"itinerary": itinerary_text, "days": req.days}

    except Exception as e:
        logger.warning(f"Itinerary generation error: {e}")
        return {"itinerary": "Unable to generate itinerary at this time.", "days": req.days}
