"""
Trail geometry endpoint — fetches polyline data from COTREX ArcGIS API on demand.
Returns GeoJSON-style coordinates for rendering on the frontend map.
"""

import logging
import math
from typing import List, Optional

import httpx
import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geometry", tags=["geometry"])

COTREX_URL = (
    "https://services3.arcgis.com/0jWpHMuhmHsukKE3/arcgis/rest/services"
    "/CPW_Trails_08222024/FeatureServer"
)
LAYER_TRAILS = 2
LAYER_TRAILHEADS = 0


class ElevationPoint(BaseModel):
    distance_mi: float
    elev_ft: float


class TrailGeometry(BaseModel):
    name: str
    feature_id: Optional[int] = None
    coordinates: List[List[float]]  # [[lng, lat], ...]
    elevation_profile: List[ElevationPoint] = []


class TrailheadPoint(BaseModel):
    name: str
    latitude: float
    longitude: float


class GeometryResponse(BaseModel):
    trails: List[TrailGeometry]
    trailheads: List[TrailheadPoint]


def _fetch_trail_geometry(trail_name: str) -> Optional[TrailGeometry]:
    """Fetch polyline geometry for a trail from COTREX."""
    try:
        params = {
            "where": f"name = '{trail_name.replace(chr(39), chr(39)+chr(39))}'",
            "outFields": "FID,name,feature_id",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
            "resultRecordCount": 1,
        }
        resp = requests.get(
            f"{COTREX_URL}/{LAYER_TRAILS}/query",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            return None

        feat = features[0]
        attrs = feat.get("attributes", {})
        geom = feat.get("geometry", {})
        paths = geom.get("paths", [])

        # Flatten all paths into one coordinate list
        coords = []
        for path in paths:
            coords.extend(path)

        if not coords:
            return None

        return TrailGeometry(
            name=attrs.get("name", trail_name),
            feature_id=attrs.get("feature_id"),
            coordinates=coords,
        )
    except Exception as e:
        logger.warning(f"Failed to fetch geometry for '{trail_name}': {e}")
        return None


def _fetch_trailheads_near(trail_name: str) -> List[TrailheadPoint]:
    """Fetch trailhead points matching a trail name from COTREX."""
    try:
        # Search trailheads with matching name
        search = trail_name.replace("Trail", "").replace("Loop", "").strip()
        params = {
            "where": f"name LIKE '%{search.replace(chr(39), chr(39)+chr(39))}%'",
            "outFields": "name,FID",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
            "resultRecordCount": 5,
        }
        resp = requests.get(
            f"{COTREX_URL}/{LAYER_TRAILHEADS}/query",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        points = []
        for feat in data.get("features", []):
            geom = feat.get("geometry", {})
            if geom and "x" in geom and "y" in geom:
                points.append(TrailheadPoint(
                    name=feat["attributes"].get("name", "Trailhead"),
                    longitude=geom["x"],
                    latitude=geom["y"],
                ))
        return points
    except Exception as e:
        logger.warning(f"Failed to fetch trailheads for '{trail_name}': {e}")
        return []


USGS_ELEV_URL = "https://epqs.nationalmap.gov/v1/json"


def _haversine_mi(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in miles."""
    R = 3959.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _sample_points(coords: List[List[float]], n: int = 10) -> List[dict]:
    """Sample n evenly-spaced points along a polyline. coords are [lng, lat]."""
    if len(coords) < 2:
        return []
    # Build cumulative distance array
    cum_dist = [0.0]
    for i in range(1, len(coords)):
        d = _haversine_mi(coords[i - 1][1], coords[i - 1][0], coords[i][1], coords[i][0])
        cum_dist.append(cum_dist[-1] + d)
    total = cum_dist[-1]
    if total < 0.01:
        return []
    # Sample at even intervals
    step = total / (n - 1) if n > 1 else total
    samples = []
    seg = 0
    for i in range(n):
        target = i * step
        while seg < len(cum_dist) - 2 and cum_dist[seg + 1] < target:
            seg += 1
        seg_len = cum_dist[seg + 1] - cum_dist[seg]
        if seg_len > 0:
            frac = (target - cum_dist[seg]) / seg_len
        else:
            frac = 0
        lat = coords[seg][1] + frac * (coords[seg + 1][1] - coords[seg][1])
        lng = coords[seg][0] + frac * (coords[seg + 1][0] - coords[seg][0])
        samples.append({"lat": lat, "lng": lng, "distance_mi": round(target, 2)})
    return samples


async def _fetch_elevation_profile(coords: List[List[float]]) -> List[ElevationPoint]:
    """Fetch elevation for sampled points along a trail polyline using USGS API."""
    samples = _sample_points(coords, 10)
    if not samples:
        return []
    profile = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for pt in samples:
                try:
                    r = await client.get(USGS_ELEV_URL, params={
                        "x": pt["lng"], "y": pt["lat"],
                        "wkid": 4326, "units": "Feet", "includeDate": "false",
                    })
                    data = r.json()
                    elev = float(data.get("value", -1))
                    if elev < -100:
                        continue
                    profile.append(ElevationPoint(
                        distance_mi=pt["distance_mi"],
                        elev_ft=round(elev, 0),
                    ))
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"WARNING: USGS elevation API slow — skipping profile: {e}")
        return []
    return profile


@router.get("/gpx")
async def get_gpx_export(
    names: str = Query(..., description="Trail name for GPX export"),
):
    """Export trail geometry as GPX XML file for download."""
    from fastapi.responses import Response

    trail_name = names.strip()
    if not trail_name:
        raise HTTPException(status_code=400, detail="No trail name provided")

    geom = _fetch_trail_geometry(trail_name)
    if not geom or not geom.coordinates:
        raise HTTPException(status_code=404, detail="Trail geometry not found")

    # Build elevation profile for GPX
    elev_profile = await _fetch_elevation_profile(geom.coordinates)
    elev_map = {(ep.distance_mi): ep.elev_ft for ep in elev_profile}

    # Build GPX XML
    trkpts = []
    for coord in geom.coordinates:
        lng, lat = coord[0], coord[1]
        ele_val = coord[2] if len(coord) > 2 else None
        ele_xml = f"\n        <ele>{ele_val:.0f}</ele>" if ele_val else ""
        trkpts.append(
            f'      <trkpt lat="{lat:.6f}" lon="{lng:.6f}">{ele_xml}\n      </trkpt>'
        )

    gpx_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="TrailBlaze AI"
     xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>{trail_name}</name>
    <trkseg>
{chr(10).join(trkpts)}
    </trkseg>
  </trk>
</gpx>"""

    safe_name = trail_name.replace(" ", "_").replace("/", "-")
    return Response(
        content=gpx_xml,
        media_type="application/gpx+xml",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.gpx"'
        },
    )


@router.get("", response_model=GeometryResponse)
async def get_trail_geometries(
    names: str = Query(..., description="Comma-separated trail names"),
):
    """
    Fetch trail polyline geometries and nearby trailhead points from COTREX.
    Example: /api/geometry?names=Royal Arch Trail,Bear Lake Loop
    """
    trail_names = [n.strip() for n in names.split(",") if n.strip()]
    if not trail_names:
        raise HTTPException(status_code=400, detail="No trail names provided")

    trails = []
    trailheads = []
    seen_trailheads = set()

    for name in trail_names[:5]:  # Limit to 5 trails per request
        geom = _fetch_trail_geometry(name)
        if geom:
            # Fetch elevation profile for the first trail only (to keep response fast)
            if len(trails) == 0 and geom.coordinates:
                geom.elevation_profile = await _fetch_elevation_profile(geom.coordinates)
            trails.append(geom)

        for th in _fetch_trailheads_near(name):
            key = (th.latitude, th.longitude)
            if key not in seen_trailheads:
                seen_trailheads.add(key)
                trailheads.append(th)

    return GeometryResponse(trails=trails, trailheads=trailheads)
