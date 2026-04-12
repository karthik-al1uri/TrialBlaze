"""
Seed the reviews collection with realistic sample reviews for popular Colorado trails.
Run: python -m backend.scripts.seed_reviews
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from pathlib import Path

# Load env
for candidate in [
    Path(__file__).resolve().parent.parent.parent / "ai" / ".env",
    Path.cwd() / "ai" / ".env",
]:
    if candidate.is_file():
        load_dotenv(candidate, override=True)
        break

MONGO_URI = os.getenv("MONGO_URI")

# Popular Colorado trails to seed reviews for
TRAILS = [
    "Bear Peak Trail",
    "Royal Arch Trail",
    "Flatirons Vista Trail",
    "Mount Sanitas Trail",
    "Chautauqua Trail",
    "Green Mountain West Ridge Trail",
    "Flagstaff Mountain Trail",
    "South Boulder Peak Trail",
    "Mesa Trail",
    "Enchanted Mesa Trail",
    "Betasso Preserve Canyon Loop",
    "Walker Ranch Loop",
    "Heil Valley Ranch - Wapiti Trail",
    "Hall Ranch - Nelson Loop",
    "Eldorado Canyon Trail",
    "Longs Peak Trail",
    "Sky Pond Trail",
    "Emerald Lake Trail",
    "Bear Lake Loop",
    "Glacier Gorge Trail",
    "Alberta Falls Trail",
    "Dream Lake Trail",
    "Flattop Mountain Trail",
    "Deer Mountain Trail",
    "Gem Lake Trail",
    "Lily Mountain Trail",
    "Twin Sisters Peak Trail",
    "Ypsilon Lake Trail",
    "Hanging Lake Trail",
    "Grays Peak Trail",
    "Torreys Peak Trail",
    "Quandary Peak Trail",
    "Mount Bierstadt Trail",
    "Maroon Bells Scenic Loop",
    "Crater Lake Trail - Maroon Bells",
    "Ice Lake Trail",
    "Blue Lakes Trail",
    "Columbine Lake Trail",
    "Mount Elbert Trail",
    "Horsetooth Falls Trail",
    "Horsetooth Rock Trail",
    "Garden of the Gods - Perkins Central Garden Trail",
    "Incline Trail",
    "Seven Bridges Trail",
    "North Cheyenne Canon Trail",
    "St Mary's Falls Trail",
    "Red Rocks Trail",
    "Roxborough State Park - Fountain Valley Trail",
    "Waterton Canyon Trail",
    "Colorado Trail - Segment 1",
]

REVIEW_TEMPLATES = [
    {
        "titles": ["Stunning views!", "Absolutely gorgeous", "A Colorado classic", "Worth every step"],
        "bodies": [
            "One of the best hikes I've done in Colorado. The views from the top are incredible. Trail was well-maintained and the signage was clear.",
            "Arrived early morning to beat the crowds and it was magical. Wildflowers were blooming and we saw a few marmots along the way.",
            "This trail never disappoints. I've hiked it multiple times across different seasons and each time offers something new.",
            "Challenging but rewarding. Pack plenty of water and start early. The summit views make it all worthwhile.",
        ],
        "rating_range": (4, 5),
    },
    {
        "titles": ["Great trail but crowded", "Beautiful but busy", "Plan to arrive early"],
        "bodies": [
            "Trail itself is fantastic but parking was a nightmare. Got there at 8am and the lot was already full. The trail gets very congested.",
            "Beautiful scenery throughout. Only downside is the popularity — expect lots of people on weekends. Weekday mornings are much better.",
            "Solid hike with great views. Trail was muddy in some spots after recent rain. Bring trekking poles.",
        ],
        "rating_range": (3, 4),
    },
    {
        "titles": ["Tougher than expected", "Underrated difficulty", "Be prepared"],
        "bodies": [
            "Don't underestimate this one. The elevation gain hits harder than you'd think. Bring plenty of water and snacks.",
            "Some sections were quite steep and rocky. Good hiking boots are a must. The trail was not as well-marked in the upper section.",
            "Started later than planned and the afternoon thunderstorms rolled in. Always check weather and start early in Colorado!",
        ],
        "rating_range": (3, 4),
    },
    {
        "titles": ["Perfect for families", "Easy and enjoyable", "Great beginner hike"],
        "bodies": [
            "Took the kids and they loved it. Well-maintained trail with plenty of shade. Perfect for a morning outing.",
            "Nice easy stroll with beautiful scenery. Saw deer along the trail. Great option if you want something relaxing.",
            "Perfect trail for visitors to Colorado. Not too strenuous but still gives you great mountain views.",
        ],
        "rating_range": (4, 5),
    },
    {
        "titles": ["Epic adventure", "Bucket list trail", "Life-changing hike"],
        "bodies": [
            "This has been on my bucket list for years and it did not disappoint. The alpine scenery is breathtaking. One of the most beautiful places I've ever been.",
            "Woke up at 4am to do this one and it was absolutely worth it. Watched the sunrise from the ridge. Unforgettable experience.",
            "Challenging but one of the most rewarding hikes in Colorado. The landscape changes dramatically as you gain elevation. Truly epic.",
        ],
        "rating_range": (5, 5),
    },
]

DIFFICULTY_FELT = [
    "Easier than expected",
    "As expected",
    "As expected",
    "Harder than expected",
    "As expected",
]


def make_review(trail_name: str, days_ago: int) -> dict:
    template = random.choice(REVIEW_TEMPLATES)
    rating = random.randint(*template["rating_range"])
    title = random.choice(template["titles"])
    body = random.choice(template["bodies"])
    felt = random.choice(DIFFICULTY_FELT)
    reported_at = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 12))
    hike_date = (reported_at - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d")

    return {
        "trail_name": trail_name,
        "rating": rating,
        "title": title,
        "body": body,
        "hike_date": hike_date,
        "difficulty_felt": felt,
        "reported_at": reported_at,
    }


async def seed():
    if not MONGO_URI:
        print("ERROR: MONGO_URI not found in environment")
        return

    client = AsyncIOMotorClient(MONGO_URI)
    db = client.trailblaze

    # Check current count
    existing = await db.reviews.count_documents({})
    print(f"Existing reviews: {existing}")

    if existing >= 50:
        print("Already have enough reviews. Skipping seed.")
        client.close()
        return

    reviews = []
    for trail in TRAILS:
        num_reviews = random.randint(3, 8)
        for _ in range(num_reviews):
            days_ago = random.randint(1, 180)
            reviews.append(make_review(trail, days_ago))

    result = await db.reviews.insert_many(reviews)
    print(f"Inserted {len(result.inserted_ids)} reviews for {len(TRAILS)} trails")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
