"""
COTREX (Colorado Trail Explorer) ArcGIS REST API connector.

Fetches trail and trailhead data from the public COTREX FeatureServer.
The API uses ArcGIS REST conventions with paginated queries.

Endpoints:
  - Layer 0: Trailheads (points)
  - Layer 1: CPW Designated Trails (polylines)
  - Layer 2: All COTREX Trails (polylines)

No API key required — this is a public dataset from Colorado Parks & Wildlife.
"""

import time
import logging
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://services3.arcgis.com/0jWpHMuhmHsukKE3/arcgis/rest/services"
    "/CPW_Trails_08222024/FeatureServer"
)

LAYER_TRAILHEADS = 0
LAYER_DESIGNATED_TRAILS = 1
LAYER_ALL_TRAILS = 2

# Fields we care about for trails
TRAIL_FIELDS = [
    "FID", "feature_id", "name", "type", "surface",
    "hiking", "horse", "bike", "motorcycle", "atv", "dogs",
    "min_elevat", "max_elevat", "length_mi_",
    "manager", "access", "url",
    "snowmobile", "ski", "snowshoe",
    "seasonalit", "seasonal_1", "seasonal_2", "seasonal_3",
]

# Fields we care about for trailheads
TRAILHEAD_FIELDS = [
    "FID", "feature_id", "place_id", "name", "alt_name",
    "type", "bathrooms", "fee", "water", "manager", "winter_act",
]

# ArcGIS max record count per request
PAGE_SIZE = 2000
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class CotrexAPIError(Exception):
    """Raised when the COTREX API returns an error."""
    pass


def _query_layer(
    layer_id: int,
    out_fields: List[str],
    where: str = "1=1",
    return_geometry: bool = False,
    result_offset: int = 0,
    result_record_count: int = PAGE_SIZE,
) -> Dict[str, Any]:
    """
    Execute a single paginated query against a COTREX FeatureServer layer.
    """
    url = f"{BASE_URL}/{layer_id}/query"
    params = {
        "where": where,
        "outFields": ",".join(out_fields),
        "returnGeometry": str(return_geometry).lower(),
        "resultOffset": result_offset,
        "resultRecordCount": result_record_count,
        "f": "json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise CotrexAPIError(
                    f"COTREX API error: {data['error'].get('message', data['error'])}"
                )
            return data

        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise CotrexAPIError(f"Failed after {MAX_RETRIES} retries: {e}")


def fetch_all_trails(
    where: str = "name <> ' ' AND name <> ''",
    return_geometry: bool = False,
    max_records: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all trail records from COTREX Layer 2, paginating automatically.

    Args:
        where: SQL WHERE clause to filter trails. Default excludes unnamed trails.
        return_geometry: Whether to include polyline geometry (large payload).
        max_records: Optional cap on total records to fetch.

    Returns:
        List of trail attribute dicts.
    """
    all_features = []
    offset = 0

    logger.info(f"Fetching COTREX trails (where={where})...")

    while True:
        count = PAGE_SIZE
        if max_records is not None:
            remaining = max_records - len(all_features)
            if remaining <= 0:
                break
            count = min(PAGE_SIZE, remaining)

        data = _query_layer(
            layer_id=LAYER_ALL_TRAILS,
            out_fields=TRAIL_FIELDS,
            where=where,
            return_geometry=return_geometry,
            result_offset=offset,
            result_record_count=count,
        )

        features = data.get("features", [])
        if not features:
            break

        for f in features:
            all_features.append(f["attributes"])

        logger.info(f"  Fetched {len(all_features)} trails so far...")

        # Check if there are more records
        if not data.get("exceededTransferLimit", False):
            break

        offset += len(features)

    logger.info(f"Total trails fetched: {len(all_features)}")
    return all_features


def fetch_all_trailheads(
    where: str = "name <> ' ' AND name <> ''",
    return_geometry: bool = True,
    max_records: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all trailhead records from COTREX Layer 0, paginating automatically.

    Args:
        where: SQL WHERE clause to filter trailheads.
        return_geometry: Include point geometry (lat/lon) — useful for mapping.
        max_records: Optional cap on total records.

    Returns:
        List of trailhead dicts (attributes + optional geometry).
    """
    all_features = []
    offset = 0

    logger.info(f"Fetching COTREX trailheads (where={where})...")

    while True:
        count = PAGE_SIZE
        if max_records is not None:
            remaining = max_records - len(all_features)
            if remaining <= 0:
                break
            count = min(PAGE_SIZE, remaining)

        data = _query_layer(
            layer_id=LAYER_TRAILHEADS,
            out_fields=TRAILHEAD_FIELDS,
            where=where,
            return_geometry=return_geometry,
            result_offset=offset,
            result_record_count=count,
        )

        features = data.get("features", [])
        if not features:
            break

        for f in features:
            record = f["attributes"]
            if return_geometry and "geometry" in f:
                record["geometry"] = f["geometry"]
            all_features.append(record)

        logger.info(f"  Fetched {len(all_features)} trailheads so far...")

        if not data.get("exceededTransferLimit", False):
            break

        offset += len(features)

    logger.info(f"Total trailheads fetched: {len(all_features)}")
    return all_features


def fetch_trail_count(where: str = "name <> ' ' AND name <> ''") -> int:
    """Return total number of trail records matching the filter."""
    url = f"{BASE_URL}/{LAYER_ALL_TRAILS}/query"
    params = {
        "where": where,
        "returnCountOnly": "true",
        "f": "json",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("count", 0)
