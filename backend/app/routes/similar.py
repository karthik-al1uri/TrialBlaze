"""
Trail similarity — returns trails similar to a given trail using FAISS vector search.
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trails", tags=["similar"])


@router.get("/similar/{trail_name}")
async def get_similar_trails(trail_name: str, limit: int = 5):
    """Return trails similar to the given trail using FAISS vector similarity."""
    from backend.app.services.ai_service import _faiss_index

    if _faiss_index is None:
        raise HTTPException(status_code=503, detail="FAISS index not available")

    try:
        docs = _faiss_index.similarity_search(
            f"trail similar to {trail_name} Colorado hiking",
            k=limit + 2,
        )
    except Exception as e:
        logger.warning(f"FAISS similarity search failed: {e}")
        raise HTTPException(status_code=502, detail=f"Similarity search failed: {e}")

    db = get_db()
    results = []
    seen = set()
    for doc in docs:
        name = doc.metadata.get("name", "")
        if not name or name.lower() == trail_name.lower() or name in seen:
            continue
        seen.add(name)
        trail = await db.trails.find_one({"name": name}, {"_id": 0})
        if trail:
            results.append({
                "name": trail.get("name"),
                "difficulty": trail.get("difficulty"),
                "length_miles": trail.get("length_miles"),
                "elevation_gain_ft": trail.get("elevation_gain_ft"),
                "nearby_city": trail.get("nearby_city"),
                "location": trail.get("location"),
                "trailblaze_score": trail.get("trailblaze_score"),
                "surface": trail.get("surface"),
            })
        if len(results) >= limit:
            break

    return {"trail_name": trail_name, "similar_trails": results}
