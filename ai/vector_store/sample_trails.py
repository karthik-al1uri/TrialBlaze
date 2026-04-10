"""
Sample Colorado trail documents for seeding the FAISS vector store.
Each document contains trail metadata and review text in a format
ready for embedding and retrieval.
"""

SAMPLE_TRAIL_DOCUMENTS = [
    {
        "id": "trail-001",
        "name": "Royal Arch Trail",
        "location": "Boulder, CO",
        "difficulty": "moderate",
        "distance_miles": 3.4,
        "elevation_gain_ft": 1400,
        "text": (
            "Royal Arch Trail is a 3.4-mile out-and-back trail near Boulder, Colorado. "
            "Rated as moderate with 1,400 ft elevation gain. The trail features a natural "
            "stone arch at the summit with panoramic views of Boulder and the Flatirons. "
            "Shaded sections through pine forest in the first mile. Rocky terrain near the top. "
            "Best visited spring through fall. Dogs allowed on leash. "
            "User review: 'Steep but rewarding. The arch view is incredible. Bring plenty of water.'"
        ),
    },
    {
        "id": "trail-002",
        "name": "Emerald Lake Trail",
        "location": "Rocky Mountain National Park, CO",
        "difficulty": "easy",
        "distance_miles": 3.6,
        "elevation_gain_ft": 650,
        "text": (
            "Emerald Lake Trail is a 3.6-mile out-and-back trail in Rocky Mountain National Park. "
            "Rated as easy with 650 ft elevation gain. Passes Dream Lake and Nymph Lake along the way. "
            "Well-maintained path with stunning alpine lake views surrounded by Hallett Peak and "
            "Flattop Mountain. Very popular trail, expect crowds in summer. "
            "User review: 'Perfect family hike. Three beautiful lakes in one trip. Go early to avoid crowds.'"
        ),
    },
    {
        "id": "trail-003",
        "name": "Sky Pond Trail",
        "location": "Rocky Mountain National Park, CO",
        "difficulty": "hard",
        "distance_miles": 9.4,
        "elevation_gain_ft": 1740,
        "text": (
            "Sky Pond Trail is a 9.4-mile out-and-back trail in Rocky Mountain National Park. "
            "Rated as hard with 1,740 ft elevation gain. Features Timberline Falls, Lake of Glass, "
            "and the remote Sky Pond at 10,900 ft. Requires scrambling over rocks near the waterfall. "
            "Exposed alpine terrain above treeline. Lightning risk in afternoon storms. "
            "User review: 'The most beautiful hike I have ever done. The scramble is fun but be careful when wet.'"
        ),
    },
    {
        "id": "trail-004",
        "name": "Hanging Lake Trail",
        "location": "Glenwood Springs, CO",
        "difficulty": "moderate",
        "distance_miles": 3.0,
        "elevation_gain_ft": 1020,
        "text": (
            "Hanging Lake Trail is a 3.0-mile out-and-back trail near Glenwood Springs, Colorado. "
            "Rated as moderate with 1,020 ft elevation gain. Features a turquoise lake fed by "
            "waterfalls on a cliff ledge. Permit required for access, limited daily visitors. "
            "Steep switchbacks with some shade from canyon walls. No dogs allowed. "
            "User review: 'Absolutely magical place. Get your permit early, they sell out fast.'"
        ),
    },
    {
        "id": "trail-005",
        "name": "Bear Lake Loop",
        "location": "Rocky Mountain National Park, CO",
        "difficulty": "easy",
        "distance_miles": 0.8,
        "elevation_gain_ft": 50,
        "text": (
            "Bear Lake Loop is a 0.8-mile loop trail in Rocky Mountain National Park. "
            "Rated as easy with only 50 ft elevation gain. Fully paved and wheelchair accessible. "
            "Stunning views of Hallett Peak and Continental Divide reflected in Bear Lake. "
            "Great for families with small children and elderly visitors. Very crowded in summer. "
            "User review: 'Short and sweet. Perfect if you want mountain views without a long hike.'"
        ),
    },
    {
        "id": "trail-006",
        "name": "Longs Peak via Keyhole Route",
        "location": "Rocky Mountain National Park, CO",
        "difficulty": "hard",
        "distance_miles": 14.5,
        "elevation_gain_ft": 5100,
        "text": (
            "Longs Peak via Keyhole Route is a 14.5-mile out-and-back trail in Rocky Mountain National Park. "
            "Rated as hard with 5,100 ft elevation gain. Colorado 14er summit at 14,259 ft. "
            "Technical scrambling through the Trough, Narrows, and Homestretch. Class 3 climbing required. "
            "Start before 3 AM to avoid afternoon lightning. Helmets recommended. "
            "User review: 'Bucket list climb. Extremely challenging. Not for beginners. The views from the top are unreal.'"
        ),
    },
    {
        "id": "trail-007",
        "name": "Maroon Bells Scenic Loop",
        "location": "Aspen, CO",
        "difficulty": "easy",
        "distance_miles": 1.5,
        "elevation_gain_ft": 100,
        "text": (
            "Maroon Bells Scenic Loop is a 1.5-mile loop trail near Aspen, Colorado. "
            "Rated as easy with 100 ft elevation gain. Iconic view of Maroon Bells reflected in "
            "Maroon Lake. One of the most photographed locations in Colorado. "
            "Shuttle or reservation required for vehicle access in summer. "
            "User review: 'The postcard view is real. Incredibly beautiful, easy walk for all ages.'"
        ),
    },
    {
        "id": "trail-008",
        "name": "Mount Sanitas Trail",
        "location": "Boulder, CO",
        "difficulty": "moderate",
        "distance_miles": 3.2,
        "elevation_gain_ft": 1300,
        "text": (
            "Mount Sanitas Trail is a 3.2-mile loop trail in Boulder, Colorado. "
            "Rated as moderate with 1,300 ft elevation gain. Popular local trail with steep rocky "
            "sections and ridge walking. Great views of Boulder, the Flatirons, and Indian Peaks. "
            "Exposed sections with little shade on the main summit route. "
            "User review: 'My go-to morning workout hike. Fast, steep, and great views at the top.'"
        ),
    },
    {
        "id": "trail-009",
        "name": "Ice Lake Basin Trail",
        "location": "Silverton, CO",
        "difficulty": "hard",
        "distance_miles": 7.0,
        "elevation_gain_ft": 2500,
        "text": (
            "Ice Lake Basin Trail is a 7.0-mile out-and-back trail near Silverton, Colorado. "
            "Rated as hard with 2,500 ft elevation gain. Features a vivid turquoise alpine lake "
            "surrounded by wildflower meadows and 13,000 ft peaks. Above treeline exposure. "
            "Best in July-August for wildflower season. Lightning danger in afternoon. "
            "User review: 'The color of Ice Lake is unbelievable. Wildflowers everywhere in July.'"
        ),
    },
    {
        "id": "trail-010",
        "name": "Garden of the Gods Perimeter Trail",
        "location": "Colorado Springs, CO",
        "difficulty": "easy",
        "distance_miles": 3.5,
        "elevation_gain_ft": 200,
        "text": (
            "Garden of the Gods Perimeter Trail is a 3.5-mile loop trail in Colorado Springs. "
            "Rated as easy with 200 ft elevation gain. Passes through dramatic red sandstone "
            "formations with views of Pikes Peak. Mostly flat and well-maintained. "
            "Open year-round and free admission. Dog friendly. "
            "User review: 'Great easy hike with jaw-dropping rock formations. Perfect winter trail.'"
        ),
    },
]
