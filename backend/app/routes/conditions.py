"""Trail condition reports — crowdsourced trail status."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.database import get_db

router = APIRouter(prefix="/api/conditions", tags=["conditions"])

VALID_CONDITIONS = [
    "Clear", "Muddy", "Snow", "Icy",
    "Downed Tree", "Washed Out",
]


class ConditionReport(BaseModel):
    trail_name: str
    condition: str
    note: Optional[str] = None


@router.post("/report")
async def submit_condition(report: ConditionReport):
    if report.condition not in VALID_CONDITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition. Must be one of: {VALID_CONDITIONS}",
        )
    if report.note and len(report.note) > 200:
        raise HTTPException(
            status_code=400,
            detail="Note must be 200 characters or less",
        )
    db = get_db()
    doc = {
        "trail_name": report.trail_name,
        "condition": report.condition,
        "note": report.note or "",
        "reported_at": datetime.now(timezone.utc),
    }
    result = await db.conditions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@router.get("/recent")
async def get_recent_conditions(limit: int = 20):
    db = get_db()
    reports = (
        await db.conditions.find({})
        .sort("reported_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    for r in reports:
        r["id"] = str(r.pop("_id"))
        if hasattr(r.get("reported_at"), "isoformat"):
            r["reported_at"] = r["reported_at"].isoformat()
    return reports


@router.get("/{trail_name}")
async def get_conditions(trail_name: str, limit: int = 5):
    db = get_db()
    reports = (
        await db.conditions.find({"trail_name": trail_name})
        .sort("reported_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    for r in reports:
        r["id"] = str(r.pop("_id"))
    return reports
