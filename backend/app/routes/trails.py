"""Trail and Trailhead API routes."""

from typing import Optional, List
import requests
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models.trail import (
    TrailResponse,
    TrailListResponse,
    TrailheadResponse,
    TrailheadListResponse,
)
from backend.app.services.scoring import calculate_trailblaze_score
from backend.app.services.crowd_predictor import predict_crowd, parse_target_date
from backend.app.services.seasonal_analyzer import analyze_seasonal_scores

router = APIRouter(prefix="/api/trails", tags=["trails"])


class MapTrail(BaseModel):
    name: str
    difficulty: Optional[str] = None
    length_miles: Optional[float] = None
    elevation_gain_ft: Optional[float] = None
    manager: Optional[str] = None
    region: Optional[str] = None
    source: Optional[str] = None
    location: Optional[str] = None
    nearby_city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    hiking: Optional[bool] = None
    dogs: Optional[str] = None
    surface: Optional[str] = None
    avg_rating: Optional[float] = None
    review_count: int = 0
    hp_rating: Optional[float] = None
    hp_summary: Optional[str] = None
    hp_condition: Optional[str] = None
    trailblaze_score: Optional[float] = None
    wildlife_alert: Optional[bool] = None
    wildlife_alert_species: Optional[List[str]] = None


class MapTrailsResponse(BaseModel):
    trails: List[MapTrail]
    total: int


def _with_trailblaze_score(trail_doc: dict) -> dict:
    if trail_doc.get("trailblaze_score") is None:
        embedded_reviews = trail_doc.get("reviews", [])
        ratings = [
            r.get("rating", 0)
            for r in embedded_reviews
            if isinstance(r, dict) and r.get("rating")
        ]
        review_summary = {
            "average_rating": (sum(ratings) / len(ratings)) if ratings else 0,
            "total_reviews": len(ratings),
        }
        trail_doc["trailblaze_score"] = calculate_trailblaze_score(
            trail_doc,
            reviews=review_summary,
            weather=None,
        )
    return trail_doc


@router.get("/featured", response_model=MapTrailsResponse)
async def get_featured_trails(
    limit: int = Query(10000, ge=1, le=10000),
    difficulty: Optional[str] = Query(None),
):
    """Return ALL trails with coordinates from cached centroids."""
    from ai.services.geography import get_region_for_manager

    db = get_db()
    query = {
        "difficulty": {"$in": ["easy", "moderate", "hard"]},
    }
    if difficulty:
        query["difficulty"] = difficulty

    cursor = db.trails.find(query, {"_id": 0}).limit(limit)
    raw = await cursor.to_list(length=limit)

    # Batch-load cached COTREX centroids for all trail names
    trail_names = [t.get("name", "") for t in raw if t.get("name")]
    centroid_cursor = db.trail_centroids.find(
        {"name": {"$in": trail_names}}, {"_id": 0}
    )
    centroid_list = await centroid_cursor.to_list(length=len(trail_names))
    centroid_map = {c["name"]: (c["lat"], c["lng"]) for c in centroid_list}

    trails = []
    for t in raw:
        t = _with_trailblaze_score(t)
        name = t.get("name", "")
        manager = t.get("manager", "")
        region = get_region_for_manager(manager)
        reviews = t.get("reviews", [])
        ratings = [r.get("rating", 0) for r in reviews if isinstance(r, dict) and r.get("rating")]
        avg = sum(ratings) / len(ratings) if ratings else None

        # Prefer COTREX centroid, fall back to manager region center
        coords = centroid_map.get(name)
        if coords:
            lat, lng = coords
        elif region:
            lat, lng = region[2], region[3]
        else:
            lat, lng = None, None

        trails.append(MapTrail(
            name=name,
            difficulty=t.get("difficulty"),
            length_miles=t.get("length_miles"),
            elevation_gain_ft=t.get("elevation_gain_ft"),
            manager=manager,
            region=t.get("region") or (region[0] if region else None),
            source=t.get("source", "cotrex"),
            location=region[0] if region else t.get("region") or manager,
            nearby_city=region[1] if region else "",
            lat=lat,
            lng=lng,
            hiking=t.get("hiking"),
            dogs=t.get("dogs"),
            surface=t.get("surface"),
            avg_rating=round(avg, 1) if avg else None,
            review_count=len(reviews),
            hp_rating=t.get("hp_rating"),
            hp_summary=t.get("hp_summary"),
            hp_condition=t.get("hp_condition"),
            trailblaze_score=t.get("trailblaze_score"),
            wildlife_alert=t.get("wildlife_alert", False),
            wildlife_alert_species=t.get("wildlife_alert_species", []),
        ))

    # Filter to only trails that have coordinates
    trails = [t for t in trails if t.lat is not None]

    return MapTrailsResponse(trails=trails, total=len(trails))


@router.get("", response_model=TrailListResponse)
async def list_trails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    difficulty: Optional[str] = Query(None, pattern="^(easy|moderate|hard|unknown)$"),
    hiking: Optional[bool] = None,
    bike: Optional[bool] = None,
    dogs: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List trails with pagination and optional filters.
    """
    db = get_db()
    query = {}

    if difficulty:
        query["difficulty"] = difficulty
    if hiking is not None:
        query["hiking"] = hiking
    if bike is not None:
        query["bike"] = bike
    if dogs:
        query["dogs"] = {"$regex": dogs, "$options": "i"}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    total = await db.trails.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.trails.find(query, {"_id": 0}).skip(skip).limit(page_size)
    trails = await cursor.to_list(length=page_size)
    trails = [_with_trailblaze_score(t) for t in trails]

    return TrailListResponse(
        trails=[TrailResponse(**t) for t in trails],
        total=total,
        page=page,
        page_size=page_size,
    )


def _score_forecast_day(temp_max_f: float, rain_in: float, snow_in: float, wind_mph: float) -> int:
    score = 100.0

    if temp_max_f < 30 or temp_max_f > 90:
        score -= 30
    elif temp_max_f < 40 or temp_max_f > 85:
        score -= 15

    score -= rain_in * 40
    score -= snow_in * 60

    if wind_mph > 30:
        score -= 25
    elif wind_mph > 20:
        score -= 10

    return int(max(0, round(score)))


def _build_best_day_reason(day: dict) -> str:
    reasons: List[str] = []
    temp_max = day["temp_max_f"]
    rain = day["rain_in"]
    snow = day["snow_in"]
    wind = day["wind_mph"]

    if 45 <= temp_max <= 80:
        reasons.append("mild temperatures")
    elif temp_max < 45:
        reasons.append("cool but manageable temperatures")
    else:
        reasons.append("warm conditions")

    if rain < 0.1 and snow == 0:
        reasons.append("dry trails expected")
    elif rain < 0.25 and snow < 0.25:
        reasons.append("low precipitation risk")

    if wind < 15:
        reasons.append("light winds")
    elif wind < 25:
        reasons.append("moderate winds")

    if not reasons:
        return "best balance of forecast conditions this week"
    return ", ".join(reasons)


@router.get("/best-day/{trail_name}")
async def get_best_day_for_trail(trail_name: str):
    """Find the best hiking day in the next 7 days for a trail."""
    db = get_db()

    centroid = await db.trail_centroids.find_one({"name": trail_name}, {"_id": 0, "lat": 1, "lng": 1})
    if not centroid:
        centroid = await db.trail_centroids.find_one(
            {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
            {"_id": 0, "lat": 1, "lng": 1},
        )
    if not centroid:
        raise HTTPException(status_code=404, detail="Trail coordinates not found")

    params = {
        "latitude": centroid["lat"],
        "longitude": centroid["lng"],
        "daily": [
            "temperature_2m_max",
            "precipitation_sum",
            "snowfall_sum",
            "wind_speed_10m_max",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": 7,
        "timezone": "America/Denver",
    }

    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather service error: {e}")

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if not dates:
        raise HTTPException(status_code=502, detail="No forecast data available")

    scored_days = []
    for i, date in enumerate(dates):
        day = {
            "date": date,
            "temp_max_f": daily.get("temperature_2m_max", [0] * len(dates))[i],
            "rain_in": daily.get("precipitation_sum", [0] * len(dates))[i],
            "snow_in": daily.get("snowfall_sum", [0] * len(dates))[i],
            "wind_mph": daily.get("wind_speed_10m_max", [0] * len(dates))[i],
        }
        day["score"] = _score_forecast_day(
            day["temp_max_f"],
            day["rain_in"],
            day["snow_in"],
            day["wind_mph"],
        )
        scored_days.append(day)

    best = max(scored_days, key=lambda d: d["score"])
    reason = _build_best_day_reason(best)

    return {
        "trail_name": trail_name,
        "best_date": best["date"],
        "score": best["score"],
        "reason": reason,
        "daily_scores": [{"date": d["date"], "score": d["score"]} for d in scored_days],
    }


@router.get("/crowd/{trail_name}")
async def get_crowd_prediction(trail_name: str, date: Optional[str] = None):
    """Predict trail crowd level for target date and next 7 days."""
    db = get_db()

    trail = await db.trails.find_one({"name": trail_name}, {"_id": 0})
    if not trail:
        trail = await db.trails.find_one(
            {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
            {"_id": 0},
        )
    if not trail:
        raise HTTPException(status_code=404, detail="Trail not found")

    centroid = await db.trail_centroids.find_one({"name": trail.get("name")}, {"_id": 0, "lat": 1, "lng": 1})
    if not centroid:
        centroid = await db.trail_centroids.find_one(
            {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
            {"_id": 0, "lat": 1, "lng": 1},
        )
    if not centroid:
        raise HTTPException(status_code=404, detail="Trail coordinates not found")

    params = {
        "latitude": centroid["lat"],
        "longitude": centroid["lng"],
        "daily": [
            "temperature_2m_max",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": 7,
        "timezone": "America/Denver",
    }

    forecast_days = []
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("daily", {})
        dates = data.get("time", [])
        temps = data.get("temperature_2m_max", [])
        prec = data.get("precipitation_sum", [])
        winds = data.get("wind_speed_10m_max", [])

        for i, day in enumerate(dates):
            forecast_days.append({
                "date": day,
                "temp_high_f": temps[i] if i < len(temps) else 0,
                "precipitation_sum_in": prec[i] if i < len(prec) else 0,
                "wind_max_mph": winds[i] if i < len(winds) else 0,
            })
    except Exception:
        forecast_days = []

    target_date = parse_target_date(date)
    target_date_iso = target_date.isoformat()
    target_forecast = next((d for d in forecast_days if d["date"] == target_date_iso), None)
    today_prediction = predict_crowd(trail, target_date, target_forecast)

    weekly = []
    for d in forecast_days:
        pred = predict_crowd(trail, parse_target_date(d["date"]), d)
        weekly.append({
            "date": d["date"],
            "score": pred["score"],
            "level": pred["level"],
        })

    return {
        "trail_name": trail.get("name", trail_name),
        "target_date": target_date_iso,
        "score": today_prediction["score"],
        "level": today_prediction["level"],
        "best_time": today_prediction["best_time"],
        "weekly_forecast": weekly,
    }


@router.get("/seasonal/{trail_name}")
async def get_seasonal_heatmap(trail_name: str):
    """Return monthly trail quality scores from weather + review seasonality."""
    db = get_db()

    trail = await db.trails.find_one({"name": trail_name}, {"_id": 0, "name": 1})
    if not trail:
        trail = await db.trails.find_one(
            {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
            {"_id": 0, "name": 1},
        )
    if not trail:
        raise HTTPException(status_code=404, detail="Trail not found")

    centroid = await db.trail_centroids.find_one({"name": trail.get("name")}, {"_id": 0, "lat": 1, "lng": 1})
    if not centroid:
        centroid = await db.trail_centroids.find_one(
            {"name": {"$regex": f"^{trail_name}$", "$options": "i"}},
            {"_id": 0, "lat": 1, "lng": 1},
        )
    if not centroid:
        raise HTTPException(status_code=404, detail="Trail coordinates not found")

    try:
        seasonal = analyze_seasonal_scores(
            db,
            trail_name=trail.get("name", trail_name),
            lat=float(centroid["lat"]),
            lng=float(centroid["lng"]),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Seasonal analysis failed: {e}")

    await db.trails.update_one(
        {"name": trail.get("name", trail_name)},
        {"$set": {
            "best_months": seasonal["best_months"],
            "worst_months": seasonal["worst_months"],
            "monthly_scores": seasonal["monthly_scores"],
        }},
    )

    return {
        "trail_name": trail.get("name", trail_name),
        **seasonal,
    }


@router.get("/nearby")
async def get_nearby_trails(
    lat: float,
    lng: float,
    radius_miles: float = 5.0,
    limit: int = 5,
    exclude_name: Optional[str] = None,
):
    """Returns trails within radius_miles of lat/lng using trail_centroids collection."""
    from math import radians, sin, cos, sqrt, atan2

    deg_radius = radius_miles / 69.0
    db = get_db()

    # Query centroids collection for nearby coordinates
    centroid_query: dict = {
        "lat": {"$gte": lat - deg_radius, "$lte": lat + deg_radius},
        "lng": {"$gte": lng - deg_radius, "$lte": lng + deg_radius},
    }
    if exclude_name:
        centroid_query["name"] = {"$ne": exclude_name}

    centroid_cursor = db.trail_centroids.find(centroid_query, {"_id": 0}).limit(limit * 5)
    centroids = await centroid_cursor.to_list(length=limit * 5)

    if not centroids:
        return []

    def haversine(lat1, lng1, lat2, lng2):
        R = 3959  # Earth radius in miles
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))

    # Filter by actual haversine distance and sort
    nearby_centroids = []
    for c in centroids:
        dist = haversine(lat, lng, c["lat"], c["lng"])
        if dist <= radius_miles:
            nearby_centroids.append({"name": c["name"], "lat": c["lat"], "lng": c["lng"], "dist": round(dist, 1)})
    nearby_centroids.sort(key=lambda x: x["dist"])
    nearby_centroids = nearby_centroids[:limit]

    if not nearby_centroids:
        return []

    # Fetch full trail docs for the nearby names
    names = [c["name"] for c in nearby_centroids]
    trail_cursor = db.trails.find({"name": {"$in": names}}, {"_id": 0})
    trail_docs = await trail_cursor.to_list(length=len(names))
    trail_docs = [_with_trailblaze_score(t) for t in trail_docs]
    trail_map = {t["name"]: t for t in trail_docs}

    # Build response with distance field as plain dicts
    results = []
    for c in nearby_centroids:
        t = trail_map.get(c["name"])
        if t:
            resp = TrailResponse(**t).model_dump()
            resp["distance_from_here_miles"] = c["dist"]
            results.append(resp)
    return results


@router.get("/by-region/{region}")
async def get_trails_by_region(
    region: str,
    difficulty: Optional[str] = None,
    limit: int = 50,
    source: Optional[str] = None,
):
    """Return trails filtered by region, with optional difficulty and source filters."""
    db = get_db()
    query: dict = {"region": region}
    if difficulty:
        query["difficulty"] = difficulty
    if source:
        query["source"] = source
    cursor = db.trails.find(query, {"_id": 0}).limit(limit)
    trails = await cursor.to_list(length=limit)
    trails = [_with_trailblaze_score(t) for t in trails]
    return [TrailResponse(**t) for t in trails]


@router.get("/search/{name}", response_model=TrailListResponse)
async def search_trails_by_name(
    name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Search trails by name (case-insensitive partial match)."""
    db = get_db()
    query = {"name": {"$regex": name, "$options": "i"}}
    total = await db.trails.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.trails.find(query, {"_id": 0}).skip(skip).limit(page_size)
    trails = await cursor.to_list(length=page_size)
    trails = [_with_trailblaze_score(t) for t in trails]

    return TrailListResponse(
        trails=[TrailResponse(**t) for t in trails],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{cotrex_fid}", response_model=TrailResponse)
async def get_trail(cotrex_fid: int):
    """Get a single trail by its COTREX FID."""
    db = get_db()
    trail = await db.trails.find_one({"cotrex_fid": cotrex_fid}, {"_id": 0})
    if not trail:
        raise HTTPException(status_code=404, detail="Trail not found")
    trail = _with_trailblaze_score(trail)
    return TrailResponse(**trail)


@router.post("/surprise")
async def surprise_trail(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
):
    """Return a random 'hidden gem' trail — prefers trails with good scores."""
    import random

    db = get_db()
    query: dict = {}
    if difficulty:
        query["difficulty"] = difficulty.lower()

    pipeline = [
        {"$match": query},
        {"$sample": {"size": 5}},
        {"$project": {"_id": 0}},
    ]
    results = await db.trails.aggregate(pipeline).to_list(length=5)
    if not results:
        raise HTTPException(status_code=404, detail="No trails found")

    # Pick the one with the best trailblaze score, or random if no scores
    scored = [_with_trailblaze_score(t) for t in results]
    scored.sort(key=lambda t: t.get("trailblaze_score") or 0, reverse=True)
    pick = scored[0]

    return {
        "trail": {
            "name": pick.get("name", "Unknown"),
            "difficulty": pick.get("difficulty"),
            "length_miles": pick.get("length_miles"),
            "elevation_gain_ft": pick.get("elevation_gain_ft"),
            "location": pick.get("location"),
            "nearby_city": pick.get("nearby_city"),
            "trailblaze_score": pick.get("trailblaze_score"),
            "surface": pick.get("surface"),
            "manager": pick.get("manager"),
        },
        "tagline": "Hidden gem picked just for you!",
    }


# --- Trailheads ---

trailheads_router = APIRouter(prefix="/api/trailheads", tags=["trailheads"])


@trailheads_router.get("", response_model=TrailheadListResponse)
async def list_trailheads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    """List trailheads with pagination."""
    db = get_db()
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    total = await db.trailheads.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.trailheads.find(query, {"_id": 0}).skip(skip).limit(page_size)
    trailheads = await cursor.to_list(length=page_size)

    return TrailheadListResponse(
        trailheads=[TrailheadResponse(**th) for th in trailheads],
        total=total,
        page=page,
        page_size=page_size,
    )


@trailheads_router.get("/{cotrex_fid}", response_model=TrailheadResponse)
async def get_trailhead(cotrex_fid: int):
    """Get a single trailhead by its COTREX FID."""
    db = get_db()
    th = await db.trailheads.find_one({"cotrex_fid": cotrex_fid}, {"_id": 0})
    if not th:
        raise HTTPException(status_code=404, detail="Trailhead not found")
    return TrailheadResponse(**th)
