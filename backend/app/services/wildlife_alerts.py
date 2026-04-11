"""Wildlife alert caching service.

Caches dangerous wildlife observations near trail centroids so map loads
can read from MongoDB without hitting iNaturalist per page request.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import requests

DANGEROUS_TAXA = {
    "Ursus americanus": "Black Bear",
    "Puma concolor": "Mountain Lion",
    "Alces alces": "Moose",
}

INATURALIST_URL = "https://api.inaturalist.org/v1/observations"


def _fetch_recent_species(lat: float, lng: float) -> List[str]:
    """Fetch dangerous species observed within 1 mile in last 14 days."""
    found: List[str] = []
    fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()

    for taxon, label in DANGEROUS_TAXA.items():
        params = {
            "lat": lat,
            "lng": lng,
            "radius": 1,
            "taxon_name": taxon,
            "quality_grade": "research",
            "d1": fourteen_days_ago,
            "per_page": 1,
            "order_by": "observed_on",
            "order": "desc",
        }
        try:
            resp = requests.get(INATURALIST_URL, params=params, timeout=8)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("total_results", 0) > 0:
                found.append(label)
        except Exception:
            continue

    return found


def compute_alert_for_point(lat: float, lng: float) -> Tuple[bool, List[str]]:
    species = _fetch_recent_species(lat, lng)
    return len(species) > 0, species


def refresh_wildlife_alert_cache(db, max_trails: int | None = None) -> Dict[str, int]:
    """Refresh cached wildlife alerts for all trails with centroids.

    Persists on trail documents:
      - wildlife_alert: bool
      - wildlife_alert_species: list[str]
      - wildlife_alert_updated_at: datetime
    """
    centroid_cursor = db.trail_centroids.find({}, {"_id": 0, "name": 1, "lat": 1, "lng": 1})
    centroids = centroid_cursor.limit(max_trails) if max_trails else centroid_cursor

    processed = 0
    alerted = 0

    now = datetime.now(timezone.utc)
    for c in centroids:
        name = c.get("name")
        lat = c.get("lat")
        lng = c.get("lng")
        if not name or lat is None or lng is None:
            continue

        has_alert, species = compute_alert_for_point(float(lat), float(lng))
        if has_alert:
            alerted += 1

        db.trails.update_one(
            {"name": name},
            {
                "$set": {
                    "wildlife_alert": has_alert,
                    "wildlife_alert_species": species,
                    "wildlife_alert_updated_at": now,
                }
            },
        )
        processed += 1

    return {
        "processed": processed,
        "alerted": alerted,
    }
