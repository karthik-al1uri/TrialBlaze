"""
Seed the conditions collection with recent trail condition reports.
Run: python3 -m backend.scripts.seed_conditions
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from pathlib import Path

for candidate in [
    Path(__file__).resolve().parent.parent.parent / "ai" / ".env",
    Path.cwd() / "ai" / ".env",
]:
    if candidate.is_file():
        load_dotenv(candidate, override=True)
        break

MONGO_URI = os.getenv("MONGO_URI")

CONDITIONS = ["Clear", "Muddy", "Snow", "Icy", "Downed Tree", "Washed Out"]
CONDITION_WEIGHTS = [40, 20, 15, 10, 10, 5]

TRAILS = [
    "Bear Peak Trail", "Royal Arch Trail", "Flatirons Vista Trail",
    "Mount Sanitas Trail", "Chautauqua Trail", "Mesa Trail",
    "Longs Peak Trail", "Sky Pond Trail", "Emerald Lake Trail",
    "Dream Lake Trail", "Hanging Lake Trail", "Grays Peak Trail",
    "Quandary Peak Trail", "Mount Bierstadt Trail", "Maroon Bells Scenic Loop",
    "Incline Trail", "Horsetooth Rock Trail", "Waterton Canyon Trail",
    "Walker Ranch Loop", "Green Mountain West Ridge Trail",
]

NOTES = {
    "Clear": [
        "Trail in great shape, dry and well-maintained.",
        "Perfect conditions today, no issues.",
        "Clear skies and firm trail surface.",
        "",
    ],
    "Muddy": [
        "Some muddy patches near the creek crossings.",
        "Lower section is pretty soggy after the rain.",
        "Bring waterproof boots, mud in the shaded sections.",
        "",
    ],
    "Snow": [
        "Snow above treeline, microspikes recommended.",
        "Patchy snow on north-facing slopes.",
        "6-8 inches of fresh snow, beautiful but slow going.",
        "",
    ],
    "Icy": [
        "Ice on exposed rock sections, use caution.",
        "Microspikes essential in the shaded switchbacks.",
        "Icy morning conditions, better by afternoon.",
    ],
    "Downed Tree": [
        "Large tree blocking trail around mile 2, passable.",
        "Couple of downed trees, easy to go around.",
        "Trail crew was clearing debris when I passed.",
    ],
    "Washed Out": [
        "Section near the bridge is washed out from recent storm.",
        "Some erosion on the switchbacks, be careful.",
    ],
}


async def seed():
    if not MONGO_URI:
        print("ERROR: MONGO_URI not found")
        return

    client = AsyncIOMotorClient(MONGO_URI)
    db = client.trailblaze

    existing = await db.conditions.count_documents({})
    print(f"Existing conditions: {existing}")

    if existing >= 20:
        print("Already have enough conditions. Skipping seed.")
        client.close()
        return

    docs = []
    for trail in TRAILS:
        num = random.randint(1, 3)
        for _ in range(num):
            condition = random.choices(CONDITIONS, weights=CONDITION_WEIGHTS, k=1)[0]
            note = random.choice(NOTES[condition])
            hours_ago = random.randint(1, 72)
            docs.append({
                "trail_name": trail,
                "condition": condition,
                "note": note,
                "reported_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
            })

    result = await db.conditions.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} condition reports")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
