"""
Geographic region mapping for Colorado trail managers.
Maps BLM/USFS/city managers to human-readable regions and coordinates
so FAISS can match user queries like "Rocky Mountains" or "near Boulder".
"""

from typing import Optional, Dict, Tuple

# Manager → (region name, nearby city/landmark, lat, lng)
MANAGER_REGIONS: Dict[str, Tuple[str, str, float, float]] = {
    # BLM offices
    "BLM Colorado River Valley Field Office": (
        "Central Colorado Mountains, Glenwood Springs area",
        "Glenwood Springs", 39.55, -107.32,
    ),
    "BLM Grand Junction Field Office": (
        "Western Colorado, Grand Junction and Colorado National Monument area",
        "Grand Junction", 39.06, -108.55,
    ),
    "BLM Gunnison Field Office": (
        "Central Colorado high country, Gunnison and Crested Butte area",
        "Gunnison", 38.55, -106.93,
    ),
    "BLM Kremmling Field Office": (
        "North-central Colorado, near Kremmling and Gore Range",
        "Kremmling", 40.06, -106.39,
    ),
    "BLM Little Snake Field Office": (
        "Northwest Colorado, near Craig and Steamboat Springs area",
        "Craig", 40.52, -107.55,
    ),
    "BLM Royal Gorge Field Office": (
        "South-central Colorado, Canon City and Royal Gorge area",
        "Canon City", 38.44, -105.24,
    ),
    "BLM San Luis Valley Field Office": (
        "Southern Colorado, San Luis Valley and Great Sand Dunes area",
        "Alamosa", 37.47, -105.87,
    ),
    "BLM Tres Rios Field Office": (
        "Southwest Colorado, Durango and Mesa Verde area",
        "Durango", 37.28, -107.88,
    ),
    "BLM Uncompahgre Field Office": (
        "Western Colorado, Montrose and Black Canyon of the Gunnison area",
        "Montrose", 38.48, -107.88,
    ),
    "BLM White River Field Office": (
        "Northwest Colorado, Meeker and White River National Forest area",
        "Meeker", 40.04, -107.91,
    ),
    # USFS Ranger Districts
    "USFS Aspen-Sopris Ranger District": (
        "Central Colorado, Aspen and Maroon Bells area",
        "Aspen", 39.19, -106.82,
    ),
    "USFS Boulder Ranger District": (
        "Front Range, Boulder and Indian Peaks Wilderness area",
        "Boulder", 40.01, -105.54,
    ),
    "USFS Columbine Ranger District": (
        "Central Colorado, Dillon and Summit County area",
        "Silverthorne", 39.63, -106.07,
    ),
    "USFS Dillon Ranger District": (
        "Central Colorado, Dillon Reservoir and Tenmile Range area",
        "Dillon", 39.63, -106.04,
    ),
    "USFS Eagle-Holy Cross Ranger District": (
        "Central Colorado, Vail and Holy Cross Wilderness area",
        "Vail", 39.64, -106.37,
    ),
    "USFS Grand Valley Ranger District": (
        "West-central Colorado, Grand Mesa area",
        "Grand Junction", 39.06, -108.10,
    ),
    "USFS Gunnison Ranger District": (
        "Central Colorado high country, Gunnison National Forest",
        "Gunnison", 38.55, -106.93,
    ),
    "USFS Norwood Ranger District": (
        "Southwest Colorado, Norwood and Lizard Head Wilderness area",
        "Norwood", 38.13, -108.29,
    ),
    "USFS Ouray Ranger District": (
        "Southwest Colorado, Ouray and San Juan Mountains area",
        "Ouray", 38.02, -107.67,
    ),
    "USFS Pagosa Ranger District": (
        "Southern Colorado, Pagosa Springs and San Juan Mountains area",
        "Pagosa Springs", 37.27, -107.01,
    ),
    "USFS Paonia Ranger District": (
        "West-central Colorado, North Fork Valley and West Elk Mountains area",
        "Paonia", 38.87, -107.59,
    ),
    "USFS Pikes Peak Ranger District": (
        "Front Range, Pikes Peak and Colorado Springs area",
        "Colorado Springs", 38.84, -105.04,
    ),
    "USFS Rifle Ranger District": (
        "Western Colorado, Rifle and Flat Tops Wilderness area",
        "Rifle", 39.53, -107.78,
    ),
    "USFS Saguache Ranger District": (
        "South-central Colorado, Saguache and Sangre de Cristo Range area",
        "Saguache", 38.09, -106.14,
    ),
    "USFS Salida Ranger District": (
        "Central Colorado, Salida and Arkansas River Valley area",
        "Salida", 38.53, -106.00,
    ),
    "USFS Sulphur Ranger District": (
        "North-central Colorado, near Granby and Winter Park area",
        "Granby", 40.09, -105.94,
    ),
    # Cities / Parks
    "City of Boulder Open Space and Mountain Parks": (
        "Front Range, Boulder Flatirons and foothills area",
        "Boulder", 40.00, -105.27,
    ),
    "City of Boulder Parks and Recreation": (
        "Front Range, Boulder area",
        "Boulder", 40.01, -105.27,
    ),
    "City of Boulder Transportation": (
        "Front Range, Boulder area",
        "Boulder", 40.01, -105.27,
    ),
    "City of Colorado Springs Parks, Recreation, and Cultural Services": (
        "Front Range, Colorado Springs and Garden of the Gods area",
        "Colorado Springs", 38.83, -104.82,
    ),
    "City of Durango": (
        "Southwest Colorado, Durango and Animas River area",
        "Durango", 37.27, -107.88,
    ),
    "City of Fort Collins": (
        "Northern Front Range, Fort Collins and Horsetooth area",
        "Fort Collins", 40.59, -105.08,
    ),
    "City of Salida": (
        "Central Colorado, Salida and Arkansas River Valley",
        "Salida", 38.53, -106.00,
    ),
    "Jefferson County Open Space Parks and Trails": (
        "Front Range, Jefferson County foothills west of Denver",
        "Golden", 39.76, -105.22,
    ),
    "City and County of Denver": (
        "Front Range, Denver metro area",
        "Denver", 39.74, -104.99,
    ),
    "City and County of Broomfield": (
        "Front Range, Broomfield between Denver and Boulder",
        "Broomfield", 39.92, -105.09,
    ),
    "Arkansas Headwaters Recreation Area": (
        "Central Colorado, Arkansas River corridor",
        "Salida", 38.53, -106.00,
    ),
    "Canon City Area Recreation and Park District": (
        "South-central Colorado, Canon City and Royal Gorge area",
        "Canon City", 38.44, -105.24,
    ),
    "Cherry Creek State Park": (
        "Denver metro, Cherry Creek State Park",
        "Denver", 39.64, -104.83,
    ),
    "El Paso County Park Operations Division": (
        "Front Range, El Paso County near Colorado Springs",
        "Colorado Springs", 38.83, -104.82,
    ),
    "Highline Lake State Park": (
        "Western Colorado, near Loma and Grand Junction",
        "Grand Junction", 39.12, -108.75,
    ),
    "San Juan County": (
        "Southwest Colorado, San Juan Mountains and Silverton area",
        "Silverton", 37.81, -107.66,
    ),
    "St. Vrain State Park": (
        "Northern Front Range, Longmont area",
        "Longmont", 40.17, -105.07,
    ),
    "Town of Crested Butte": (
        "Central Colorado high country, Crested Butte ski area",
        "Crested Butte", 38.87, -106.99,
    ),
    "CPW State Wildlife Areas": (
        "Colorado Parks and Wildlife managed area",
        "Denver", 39.74, -104.99,
    ),
    "Private Owner": (
        "Colorado, privately managed trail",
        "Denver", 39.74, -104.99,
    ),
    "Weld County GIS and Mapping": (
        "Northern Colorado plains, Weld County",
        "Greeley", 40.42, -104.71,
    ),
}

# User query location keywords → nearby region descriptions to boost retrieval
LOCATION_ALIASES: Dict[str, list] = {
    "rocky mountains": [
        "USFS Boulder Ranger District",
        "USFS Sulphur Ranger District",
        "USFS Columbine Ranger District",
        "USFS Dillon Ranger District",
        "USFS Eagle-Holy Cross Ranger District",
        "BLM Kremmling Field Office",
        "Jefferson County Open Space Parks and Trails",
    ],
    "rocky mountain national park": [
        "USFS Boulder Ranger District",
        "USFS Sulphur Ranger District",
    ],
    "rmnp": [
        "USFS Boulder Ranger District",
        "USFS Sulphur Ranger District",
    ],
    "boulder": [
        "City of Boulder Open Space and Mountain Parks",
        "City of Boulder Parks and Recreation",
        "City of Boulder Transportation",
        "USFS Boulder Ranger District",
    ],
    "denver": [
        "City and County of Denver",
        "Cherry Creek State Park",
        "Jefferson County Open Space Parks and Trails",
        "City and County of Broomfield",
    ],
    "colorado springs": [
        "City of Colorado Springs Parks, Recreation, and Cultural Services",
        "USFS Pikes Peak Ranger District",
        "El Paso County Park Operations Division",
    ],
    "pikes peak": [
        "USFS Pikes Peak Ranger District",
        "City of Colorado Springs Parks, Recreation, and Cultural Services",
    ],
    "vail": [
        "USFS Eagle-Holy Cross Ranger District",
    ],
    "aspen": [
        "USFS Aspen-Sopris Ranger District",
    ],
    "durango": [
        "City of Durango",
        "BLM Tres Rios Field Office",
    ],
    "gunnison": [
        "BLM Gunnison Field Office",
        "USFS Gunnison Ranger District",
    ],
    "crested butte": [
        "Town of Crested Butte",
        "USFS Gunnison Ranger District",
    ],
    "grand junction": [
        "BLM Grand Junction Field Office",
        "Highline Lake State Park",
    ],
    "glenwood springs": [
        "BLM Colorado River Valley Field Office",
    ],
    "san juan": [
        "San Juan County",
        "USFS Ouray Ranger District",
        "USFS Pagosa Ranger District",
    ],
    "silverton": [
        "San Juan County",
    ],
    "ouray": [
        "USFS Ouray Ranger District",
    ],
    "steamboat": [
        "BLM Little Snake Field Office",
    ],
    "fort collins": [
        "City of Fort Collins",
    ],
    "salida": [
        "City of Salida",
        "USFS Salida Ranger District",
    ],
    "front range": [
        "City of Boulder Open Space and Mountain Parks",
        "USFS Boulder Ranger District",
        "Jefferson County Open Space Parks and Trails",
        "USFS Pikes Peak Ranger District",
        "City of Colorado Springs Parks, Recreation, and Cultural Services",
    ],
    "foothills": [
        "City of Boulder Open Space and Mountain Parks",
        "Jefferson County Open Space Parks and Trails",
    ],
    "royal gorge": [
        "BLM Royal Gorge Field Office",
        "Canon City Area Recreation and Park District",
    ],
    "sand dunes": [
        "BLM San Luis Valley Field Office",
    ],
    "great sand dunes": [
        "BLM San Luis Valley Field Office",
    ],
}


def get_region_for_manager(manager: str) -> Optional[Tuple[str, str, float, float]]:
    """Return (region_description, nearby_city, lat, lng) for a manager."""
    return MANAGER_REGIONS.get(manager)


def get_region_text(manager: str) -> str:
    """Return a region description string to enrich trail embeddings."""
    region = MANAGER_REGIONS.get(manager)
    if region:
        return f"Located in {region[0]}. Near {region[1]}."
    return "Located in Colorado."


def resolve_location_managers(query: str) -> list:
    """
    Given a user query, find matching location keywords and return
    the list of relevant manager names for filtering.
    """
    q = query.lower()
    matched_managers = []
    for keyword, managers in LOCATION_ALIASES.items():
        if keyword in q:
            matched_managers.extend(managers)
    return list(set(matched_managers))
