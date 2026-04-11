"""
Itinerary persistence models.
Maps to the 'itineraries' MongoDB collection.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ItineraryTrail(BaseModel):
    """A trail entry within an itinerary."""
    name: str
    difficulty: Optional[str] = None
    length_miles: Optional[float] = None
    notes: Optional[str] = None
    order: int = 0


class ItineraryCreate(BaseModel):
    """Request body to create an itinerary."""
    title: str = Field(..., min_length=1, max_length=200)
    session_id: Optional[str] = None
    trails: List[ItineraryTrail] = []


class ItineraryResponse(BaseModel):
    """Itinerary record returned by the API."""
    itinerary_id: str
    title: str
    session_id: Optional[str] = None
    trails: List[ItineraryTrail] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItineraryListResponse(BaseModel):
    """List of itineraries."""
    itineraries: List[ItineraryResponse]
    total: int
