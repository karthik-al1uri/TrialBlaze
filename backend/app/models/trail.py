"""
Trail and Trailhead Pydantic models.
Maps to the 'trails' and 'trailheads' MongoDB collections.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class Review(BaseModel):
    text: str
    rating: int = Field(ge=1, le=5)
    source: str = "synthetic"


class WinterActivities(BaseModel):
    snowmobile: Optional[bool] = None
    ski: Optional[bool] = None
    snowshoe: Optional[bool] = None


class TrailResponse(BaseModel):
    """Trail record returned by the API."""
    cotrex_fid: Optional[int] = None
    feature_id: Optional[Any] = None
    name: str
    trail_type: Optional[str] = None
    surface: Optional[str] = None
    difficulty: Optional[str] = None
    length_miles: Optional[float] = None
    min_elevation_ft: Optional[float] = None
    max_elevation_ft: Optional[float] = None
    elevation_gain_ft: Optional[float] = None
    hiking: Optional[bool] = None
    horse: Optional[bool] = None
    bike: Optional[bool] = None
    motorcycle: Optional[bool] = None
    atv: Optional[bool] = None
    dogs: Optional[str] = None
    access: Optional[str] = None
    manager: Optional[str] = None
    region: Optional[str] = None
    url: Optional[str] = None
    winter_activities: Optional[WinterActivities] = None
    reviews: List[Review] = []
    source: str = "cotrex"
    hp_rating: Optional[float] = None
    hp_summary: Optional[str] = None
    hp_condition: Optional[str] = None
    hp_url: Optional[str] = None
    osm_id: Optional[str] = None
    nps_id: Optional[str] = None
    trailblaze_score: Optional[float] = None
    wildlife_alert: Optional[bool] = None
    wildlife_alert_species: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class TrailListResponse(BaseModel):
    """Paginated list of trails."""
    trails: List[TrailResponse]
    total: int
    page: int
    page_size: int


class TrailheadResponse(BaseModel):
    """Trailhead record returned by the API."""
    cotrex_fid: Optional[int] = None
    feature_id: Optional[Any] = None
    place_id: Optional[int] = None
    name: str
    alt_name: Optional[str] = None
    type: Optional[str] = None
    bathrooms: Optional[bool] = None
    fee: Optional[bool] = None
    water: Optional[bool] = None
    manager: Optional[str] = None
    winter_activities: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    source: str = "cotrex"

    model_config = ConfigDict(from_attributes=True)


class TrailheadListResponse(BaseModel):
    """Paginated list of trailheads."""
    trailheads: List[TrailheadResponse]
    total: int
    page: int
    page_size: int
