"""
Trail photos endpoint — serves cached Unsplash photos from MongoDB.
Photos are pre-fetched by the one-time pipeline:
    python -m backend.scripts.cache_trail_photos

Zero API calls at request time — instant responses.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photos", tags=["photos"])


class TrailPhoto(BaseModel):
    title: str
    url: str
    thumb_url: str
    description: str
    photographer: Optional[str] = None
    photographer_url: Optional[str] = None
    unsplash_link: Optional[str] = None


class PhotoResponse(BaseModel):
    trail_name: str
    photos: List[TrailPhoto]


@router.get("", response_model=PhotoResponse)
async def get_trail_photos(
    name: str = Query(..., description="Trail name to search photos for"),
    location: str = Query("", description="Optional location hint"),
):
    """
    Get trail photos from the MongoDB cache (pre-fetched from Unsplash).
    Run `python -m backend.scripts.cache_trail_photos` to populate the cache.
    """
    db = get_db()
    cached = await db.trail_photos.find_one({"trail_name": name}, {"_id": 0})

    if cached and cached.get("photos"):
        photos = [TrailPhoto(**p) for p in cached["photos"]]
        return PhotoResponse(trail_name=name, photos=photos)

    # No cached photos — return empty list (UI shows gradient placeholder)
    return PhotoResponse(trail_name=name, photos=[])
