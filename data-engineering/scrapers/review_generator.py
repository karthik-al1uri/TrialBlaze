"""
Trail review generator.

Since major trail review sites (AllTrails, etc.) block automated scraping
and require paid API access, this module generates contextual synthetic
reviews based on trail metadata. Reviews are realistic, varied, and
grounded in actual trail attributes (difficulty, surface, activities, etc.).

This serves as a placeholder until real review data is integrated via
a licensed API or manual collection.
"""

import random
from typing import Dict, Any, List, Optional


# --- Review templates organized by trail characteristics ---

EASY_TRAIL_TEMPLATES = [
    "Great {trail_type} for beginners! The {surface} surface was easy to walk on. Perfect for a quick outing.",
    "Took the family here and everyone loved it. Easy enough for our 5-year-old. Beautiful Colorado scenery.",
    "Nice flat {trail_type} with {surface} surface. Good for a morning walk. Not too challenging at all.",
    "Perfect trail for a casual hike. Only {length} miles and very manageable elevation. Highly recommend.",
    "Brought my elderly parents here — they had no trouble. Well-maintained {surface} path.",
    "Easy and relaxing. Great for days when you don't want a tough workout but still want to get outside.",
]

MODERATE_TRAIL_TEMPLATES = [
    "Solid moderate hike at {length} miles. The {elev_gain} ft elevation gain keeps it interesting. Worth the effort!",
    "Nice trail with some challenging sections. The {surface} surface was in good shape. Bring water!",
    "A good workout without being overwhelming. The views from the higher elevation points were stunning.",
    "Did this trail on a Saturday morning. Moderate difficulty felt about right. Some rocky sections to watch for.",
    "Great balance of challenge and enjoyment. The {trail_type} winds through beautiful Colorado terrain.",
    "Recommend poles for the steeper parts. Otherwise very doable for anyone with basic fitness.",
]

HARD_TRAIL_TEMPLATES = [
    "Challenging trail! {elev_gain} ft of elevation gain is no joke. Start early and bring plenty of water.",
    "Tough but incredibly rewarding. The views at the top make every step worth it. Not for beginners.",
    "This one pushed me to my limits. {length} miles of serious hiking. Allow a full day.",
    "Strenuous climb but spectacular alpine scenery. Watch the weather — afternoon storms are real up here.",
    "Bring trekking poles and extra layers. The trail gets exposed above treeline. Absolutely breathtaking though.",
    "One of the toughest trails I've done in Colorado. Serious hikers only. The payoff is incredible.",
]

BIKE_TEMPLATES = [
    "Great mountain biking trail! The {surface} surface provides good traction.",
    "Fun ride with some technical sections. Bikes are welcome here which is a plus.",
    "Rode this trail last weekend — flowy singletrack with nice views. Good for intermediate riders.",
]

HORSE_TEMPLATES = [
    "Rode my horse here — the trail is wide enough and well-maintained for equestrian use.",
    "Good horseback trail. Water crossings are manageable. Watch for hikers on weekends.",
]

DOG_TEMPLATES = [
    "Brought my dog (on leash) and she loved it. Plenty of shade and water access.",
    "Dog-friendly trail! Keep them leashed as required. Lots of fun smells for the pup.",
    "My golden retriever's favorite trail. Just remember to pack out waste bags.",
]

WINTER_TEMPLATES = [
    "Did this trail on snowshoes in January — absolutely magical winter scenery.",
    "Cross-country skiing here was fantastic. Well-groomed and peaceful.",
    "Great winter trail. Bring microspikes if there's been recent snow.",
]

GENERIC_TEMPLATES = [
    "Nice Colorado trail managed by {manager}. Well-maintained and clearly marked.",
    "Visited on a weekday to avoid crowds. Beautiful trail, will definitely come back.",
    "One of the hidden gems in this area. Not as crowded as the popular trails.",
    "Decent trail. Nothing spectacular but a solid option for getting outdoors.",
    "Trail was in good condition when we went. Parking can fill up on weekends.",
]

RATING_WEIGHTS = {
    "easy": [0.05, 0.05, 0.15, 0.40, 0.35],    # skews 4-5
    "moderate": [0.05, 0.05, 0.20, 0.40, 0.30],  # skews 4-5
    "hard": [0.05, 0.10, 0.15, 0.35, 0.35],       # skews 4-5
    "unknown": [0.05, 0.10, 0.25, 0.35, 0.25],
}


def _pick_rating(difficulty: str) -> int:
    """Generate a weighted random rating (1-5) based on difficulty."""
    weights = RATING_WEIGHTS.get(difficulty, RATING_WEIGHTS["unknown"])
    return random.choices([1, 2, 3, 4, 5], weights=weights, k=1)[0]


def _format_template(template: str, trail: Dict[str, Any]) -> str:
    """Fill in template placeholders with trail data."""
    return template.format(
        trail_type=trail.get("trail_type", "trail").lower(),
        surface=trail.get("surface", "natural"),
        length=trail.get("length_miles", "a few"),
        elev_gain=trail.get("elevation_gain_ft", "several hundred"),
        manager=trail.get("manager", "local land managers"),
    )


def generate_reviews(
    trail: Dict[str, Any],
    num_reviews: int = 3,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generate synthetic reviews for a trail based on its attributes.

    Args:
        trail: Normalized trail record.
        num_reviews: Number of reviews to generate (1-5).
        seed: Optional random seed for reproducibility.

    Returns:
        List of review dicts with text, rating, and source.
    """
    if seed is not None:
        random.seed(seed)

    difficulty = trail.get("difficulty", "unknown")
    num_reviews = max(1, min(num_reviews, 5))

    # Build a pool of applicable templates
    pool = list(GENERIC_TEMPLATES)

    if difficulty == "easy":
        pool.extend(EASY_TRAIL_TEMPLATES)
    elif difficulty == "moderate":
        pool.extend(MODERATE_TRAIL_TEMPLATES)
    elif difficulty == "hard":
        pool.extend(HARD_TRAIL_TEMPLATES)

    if trail.get("bike") is True:
        pool.extend(BIKE_TEMPLATES)
    if trail.get("horse") is True:
        pool.extend(HORSE_TEMPLATES)
    if trail.get("dogs") and trail["dogs"] not in ("", "no"):
        pool.extend(DOG_TEMPLATES)

    winter = trail.get("winter_activities", {})
    if isinstance(winter, dict) and any(v is True for v in winter.values()):
        pool.extend(WINTER_TEMPLATES)

    # Sample without replacement (if possible)
    k = min(num_reviews, len(pool))
    selected = random.sample(pool, k)

    reviews = []
    for template in selected:
        text = _format_template(template, trail)
        rating = _pick_rating(difficulty)
        reviews.append({
            "text": text,
            "rating": rating,
            "source": "synthetic",
        })

    return reviews


def enrich_trails_with_reviews(
    trails: List[Dict[str, Any]],
    reviews_per_trail: int = 3,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Add synthetic reviews to a list of normalized trail records.

    Args:
        trails: List of normalized trail dicts.
        reviews_per_trail: Number of reviews per trail.
        seed: Random seed for reproducibility.

    Returns:
        Same list with 'reviews' field populated.
    """
    random.seed(seed)
    for i, trail in enumerate(trails):
        trail["reviews"] = generate_reviews(
            trail,
            num_reviews=reviews_per_trail,
            seed=seed + i,
        )
    return trails
