"""
Chat request/response models for the AI orchestration endpoint.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User chat query sent to the AI pipeline."""
    query: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    language: Optional[str] = Field("en", description="Response language: 'en' or 'es'")


class TrailReference(BaseModel):
    """A trail referenced in the AI response."""
    name: str
    difficulty: Optional[str] = None
    length_miles: Optional[float] = None
    location: Optional[str] = None
    nearby_city: Optional[str] = None


class ChatResponse(BaseModel):
    """AI-generated response to a chat query."""
    answer: str
    route: Optional[str] = None
    trails_referenced: List[TrailReference] = []
    weather_context: Optional[str] = None
    session_id: Optional[str] = None
    quality_check: Optional[Dict[str, Any]] = None
