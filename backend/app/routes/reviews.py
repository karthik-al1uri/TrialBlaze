"""User reviews and trip reports for trails."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.database import get_db

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

#if not trail_id:
#    raise HTTPException(status_code=400, detail="trail_id is required")

class ReviewCreate(BaseModel):
    trail_name: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=80)
    body: Optional[str] = Field(None, max_length=500)
    hike_date: Optional[str] = None
    difficulty_felt: Optional[str] = None


VALID_DIFFICULTY_FELT = [
    "Easier than expected",
    "As expected",
    "Harder than expected",
]


async def _fetch_sentiment_summary(db, trail_name: str):
    trail_doc = await db.trails.find_one(
        {"name": trail_name},
        {"_id": 0, "sentiment_summary": 1},
    )
    if trail_doc and trail_doc.get("sentiment_summary"):
        return trail_doc["sentiment_summary"]

    trail_doc = await db.trails.find_one(
        {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
        {"_id": 0, "sentiment_summary": 1},
    )
    return trail_doc.get("sentiment_summary") if trail_doc else None


@router.post("")
async def submit_review(review: ReviewCreate):
    if review.difficulty_felt and review.difficulty_felt not in VALID_DIFFICULTY_FELT:
        raise HTTPException(
            status_code=400,
            detail=f"difficulty_felt must be one of: {VALID_DIFFICULTY_FELT}",
        )
    db = get_db()
    doc = {
        "trail_name": review.trail_name,
        "rating": review.rating,
        "title": review.title or "",
        "body": review.body or "",
        "hike_date": review.hike_date or "",
        "difficulty_felt": review.difficulty_felt or "",
        "reported_at": datetime.now(timezone.utc),
    }
    result = await db.reviews.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@router.get("/{trail_name}")
async def get_reviews(
    trail_name: str,
    limit: int = Query(10, ge=1, le=50),
    sort: str = Query("newest"),
):
    db = get_db()
    sort_dir = -1 if sort == "newest" else 1
    reviews = (
        await db.reviews.find({"trail_name": trail_name})
        .sort("reported_at", sort_dir)
        .limit(limit)
        .to_list(limit)
    )
    for r in reviews:
        r["id"] = str(r.pop("_id"))
    return reviews


@router.get("/{trail_name}/summary")
async def get_review_summary(trail_name: str):
    db = get_db()
    reviews = await db.reviews.find(
        {"trail_name": trail_name}
    ).to_list(None)
    sentiment_summary = await _fetch_sentiment_summary(db, trail_name)

    total = len(reviews)
    if total == 0:
        return {
            "average_rating": 0,
            "total_reviews": 0,
            "rating_breakdown": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "difficulty_breakdown": {
                "easier": 0,
                "as_expected": 0,
                "harder": 0,
            },
            "sentiment_summary": sentiment_summary,
        }

    rating_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    difficulty_breakdown = {"easier": 0, "as_expected": 0, "harder": 0}
    total_rating = 0

    for r in reviews:
        rating = r.get("rating", 0)
        total_rating += rating
        if rating in rating_breakdown:
            rating_breakdown[rating] += 1

        felt = r.get("difficulty_felt", "")
        if felt == "Easier than expected":
            difficulty_breakdown["easier"] += 1
        elif felt == "As expected":
            difficulty_breakdown["as_expected"] += 1
        elif felt == "Harder than expected":
            difficulty_breakdown["harder"] += 1

    return {
        "average_rating": round(total_rating / total, 1),
        "total_reviews": total,
        "rating_breakdown": rating_breakdown,
        "difficulty_breakdown": difficulty_breakdown,
        "sentiment_summary": sentiment_summary,
    }
