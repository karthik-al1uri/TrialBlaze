# TRAILBLAZE AI — PROJECT CONTEXT

Paste this at the start of any new chat window to give full context
before requesting new features or changes.

---

## PROJECT OVERVIEW

TrailBlaze AI is a full-stack AI-powered trail discovery platform
for Colorado. It combines data from four government sources with
real-time weather, LangGraph-based AI recommendations, crowdsourced
conditions, and wildlife data on an interactive map.

Built for Big Data Analytics course, Spring 2026.

---

## TECH STACK

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TailwindCSS 4 |
| Maps | Leaflet + leaflet.markercluster |
| Backend | FastAPI, Python 3.11 |
| Database | MongoDB Atlas M0 (free tier, 512MB limit) |
| AI / RAG | LangGraph, FAISS, OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Weather | Open-Meteo API (free, no key) |
| Wildlife | iNaturalist API (free, no key) |
| Photos | Unsplash API (key in .env) |
| Map tiles | OpenTopoMap (default), OSM, ESRI Satellite, USGS Topo |
| Map overlays | WaymarkedTrails hiking routes |
| RAG Pipeline | HyDE + BM25/Vector Hybrid + Cross-Encoder Reranking |

---

## DATABASE STATE

| Collection | Count | Notes |
|---|---|---|
| `trailblaze.trails` | 5,661 | COTREX 1,272 / USFS 3,220 / NPS 160 / OSM 1,009 |
| `trailblaze.trail_centroids` | 19,103 | Cached lat/lng for map pins |
| `trailblaze.trail_photos` | 4,977 | Unsplash photos (3 per trail) |
| `trailblaze.conditions` | variable | Crowdsourced trail reports |
| `trailblaze.reviews` | NOT YET BUILT | User reviews + ratings |
| `trailblaze.ratings` | NOT YET BUILT | TrailBlaze Score components |

MongoDB storage: ~4MB (well under 512MB M0 limit)

### Trail document schema (all Optional unless marked Required)
```
name: str                    # Required
difficulty: str              # "Easy" | "Moderate" | "Hard"
length_miles: float
elevation_gain_ft: float
surface: str
dog_friendly: bool
source: str                  # "COTREX"|"NPS"|"USFS"|"OSM"
manager: str                 # e.g. "White River National Forest"
region: str                  # e.g. "Rocky Mountains"
coordinates: {lat, lng}
hp_rating: float             # REI Hiking Project (0-5, mostly null)
hp_summary: str
hp_condition: str
hp_url: str
osm_id: str
nps_id: str
trailblaze_score: float      # NOT YET BUILT — proprietary score 0-100
sentiment_summary: dict      # NOT YET BUILT — NLP review breakdown
best_months: list[int]       # NOT YET BUILT — seasonal heatmap data
```

---

## FAISS VECTOR INDEX

- **Location:** `ai/vector-store/index.faiss` + `index.pkl`
- **Vectors:** ~5,600 (all 4 sources embedded)
- **Model:** text-embedding-3-small
- **Last rebuilt:** after all 4 connectors ran (full rebuild)
- **Rebuild command:** `python -m ai.rag.rebuild_index`

---

## BACKEND — FastAPI (port 8000)

### File structure
```
backend/app/
├── main.py
├── config.py
├── database.py
└── routes/
    ├── health.py
    ├── trails.py
    ├── conditions.py
    ├── geometry.py
    ├── photos.py
    ├── weather.py
    ├── chat.py
    ├── sessions.py
    └── itineraries.py
```

### All endpoints (built)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Backend health check |
| GET | `/api/trails` | Paginated trail list |
| GET | `/api/trails/featured` | All mapped trails for map |
| GET | `/api/trails/nearby` | Trails within radius |
| GET | `/api/trails/by-region/{region}` | Filter by region |
| GET | `/api/trails/search/{name}` | Search by name |
| GET | `/api/trails/{cotrex_fid}` | Single trail (catch-all, must be last) |
| GET | `/api/trailheads` | Paginated trailheads |
| GET | `/api/geometry` | Polyline + elevation profile |
| GET | `/api/photos` | Cached trail photos |
| GET | `/api/weather` | 4-day forecast + advisory |
| POST | `/api/conditions/report` | Submit condition |
| GET | `/api/conditions/{trail_name}` | Get conditions for trail |
| POST | `/api/chat` | AI trail recommendation |
| POST | `/api/sessions` | Create chat session |
| GET | `/api/sessions/{session_id}` | Get session |
| GET | `/api/sessions/{session_id}/history` | Chat history |
| POST | `/api/itineraries` | Save itinerary |
| GET | `/api/itineraries` | List itineraries |
| GET | `/api/itineraries/{id}` | Get itinerary |
| DELETE | `/api/itineraries/{id}` | Delete itinerary |
| GET | `/api/trails/crowd/{trail_name}` | Crowd prediction |
| GET | `/api/trails/seasonal/{trail_name}` | Seasonal heatmap |
| GET | `/api/trails/isochrone` | Drive-time filter |

### Endpoints not yet built

| Method | Endpoint | Feature |
|---|---|---|
| GET | `/api/nps/alerts` | NPS park alerts |
| GET | `/api/geometry/gpx` | GPX export |
| POST | `/api/trails/narrate` | AI trail narrator |
| POST | `/api/trails/surprise` | Surprise me mode |

### Route ordering in trails.py (FastAPI matches in order)

1. `GET /featured` (literal)
2. `GET /` (no param)
3. `GET /nearby` (literal)
4. `GET /by-region/{region}`
5. `GET /search/{name}`
6. `GET /{cotrex_fid}` — catch-all, must be last

---

## AI PIPELINE — LangGraph

### File structure
```
ai/
├── .env                     all environment variables
├── langgraph/
│   ├── agents.py            Router, Vector, Weather, Synthesizer
│   ├── graph.py             LangGraph state machine
│   └── state.py             TrailBlazeState TypedDict
├── rag/
│   ├── retriever.py         retrieve_context() — HyDE+hybrid+rerank
│   ├── hyde.py              HyDE hypothetical document generation
│   ├── bm25_index.py        BM25 keyword index + search
│   ├── reranker.py          Cross-encoder reranking (singleton)
│   └── rebuild_index.py     FAISS rebuild script
└── vector-store/
    ├── index.faiss
    └── index.pkl
```

### LangGraph flow
```
User query
  -> Router Agent (classifies intent)
  -> Vector Agent (HyDE + BM25/Vector hybrid + cross-encoder rerank)
  -> Weather Agent (Open-Meteo for trail location)
  -> Synthesizer Agent (GPT-4o-mini final response)
```

### RAG Pipeline — Three-Stage Retrieval

**Stage 1 — HyDE (Hypothetical Document Embeddings)**
- GPT-4o-mini generates a hypothetical ideal trail description
- That description is embedded instead of the raw short query
- Falls back to raw query if GPT call fails
- File: `ai/rag/hyde.py`

**Stage 2 — Hybrid BM25 + Vector Search with RRF Fusion**
- Vector search: embed HyDE doc → FAISS top-20
- BM25 search: keyword search on trail name/region/manager
- Reciprocal Rank Fusion combines both lists
- BM25 catches exact trail names; vector catches semantic intent
- File: `ai/rag/bm25_index.py`

**Stage 3 — Cross-Encoder Reranking**
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (~80MB, CPU)
- Scores each (original query, trail text) pair precisely
- Reranks fused top-20 → returns final top-5
- Model loaded once as singleton, not per query
- File: `ai/rag/reranker.py`

### retrieve_context() signature
```python
def retrieve_context(
    query: str,
    k: int = 5,
    source_filter: list[str] | None = None,
    region_filter: str | None = None,
    use_hyde: bool = True,
    use_hybrid: bool = True,
    use_reranker: bool = True,
) -> str:
```

### Intents supported

- `"trail"` — general trail search
- `"weather"` — weather-only query
- `"both"` — trail + weather combined
- `"national_park"` — RMNP/Estes Park, NPS filter auto-applied

### National park keywords (trigger national_park intent)
```
"rocky mountain national park", "rmnp", "estes park",
"national park", "bear lake", "trail ridge",
"longs peak", "hallett peak"
```

### State fields (TrailBlazeState)
```
query, messages, intent, context, weather_data,
response, session_id, source_filter, region_filter
```

---

## FRONTEND — Next.js (port 3000)

### File structure
```
frontend/nextjs-app/src/
├── app/
│   ├── page.tsx             main page — sidebar + map + detail
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── TrailMap.tsx         Leaflet map
│   ├── TrailDetail.tsx      detail panel
│   ├── TrailCards.tsx       sidebar trail list
│   ├── ChatPanel.tsx        floating AI chat
│   ├── ClusterDrawer.tsx    bottom drawer for clusters
│   └── ElevationProfile.tsx elevation chart (Recharts/SVG)
└── lib/
    └── api.ts               all fetch functions + types
```

### Exported functions from `api.ts`
```
sendChat, fetchTrails, searchTrails, fetchFeaturedTrails,
fetchGeometry, fetchPhotos, fetchWeather, fetchTrailsByRegion,
fetchTrailConditions, submitTrailCondition,
fetchWildlifeNearTrail, fetchNearbyTrails
```

### Exported interfaces from `api.ts`
```
TrailReference, ChatResponse, Trail, TrailListResponse,
MapTrail, MapTrailsResponse, ElevationPoint, TrailGeometry,
TrailheadPoint, GeometryResponse, TrailPhoto, PhotoResponse,
DayForecast, CurrentWeather, WeatherResponse,
ConditionReport, WildlifeObservation
```

### Map features (built)

- 4 base layers: Topo (default), Street, Satellite, USGS Topo
- 2 overlays: WaymarkedTrails hiking routes, Trail Pins
- Difficulty-colored pins: green=Easy, amber=Moderate, red=Hard
- Cluster icons: difficulty-colored circles with trail count
- Spiderfy on zoom for overlapping pins
- ClusterDrawer bottom sheet for clusters of 2-5 trails
- Layer control top-right, dark themed
- Dynamic attribution bar at bottom

### Trail detail panel sections (built, top to bottom)

1. Hero photo (Unsplash)
2. Trail name + difficulty badge
3. HP star rating (if hp_rating > 0)
4. HP summary text (if present)
5. Stats grid: distance, time, elevation gain, surface
6. Elevation profile chart (USGS data)
7. Current weather + hiking advisory
8. 4-day forecast
9. Trail condition report buttons (6 conditions)
10. Nearby trails horizontal scroll
11. Wildlife spotted grid (iNaturalist)
12. Route info (manager, trail type, style)
13. Photo gallery

### Sidebar sections (built, top to bottom)

1. App logo + title
2. Chat button
3. Browse by Region chips
4. Search input
5. Difficulty filter (All/Easy/Moderate/Hard)
6. Trail count
7. Trail cards list

### Region chips with bounding boxes

| Region | Bounds |
|---|---|
| Rocky Mountains | `[[40.1,-105.9],[40.7,-105.4]]` |
| Boulder | `[[39.9,-105.4],[40.1,-105.0]]` |
| Denver Foothills | `[[39.6,-105.3],[39.9,-104.9]]` |
| Colorado Springs | `[[38.7,-105.0],[39.0,-104.6]]` |
| Aspen | `[[39.0,-107.0],[39.3,-106.6]]` |
| Telluride | `[[37.8,-108.0],[38.0,-107.6]]` |
| Steamboat Springs | `[[40.4,-107.0],[40.6,-106.6]]` |

---

## DATA ENGINEERING — Connectors
```
data-engineering/connectors/
├── nps_rmnp_connector.py      NPS ArcGIS REST -> 160 RMNP trails
├── usfs_connector.py          USFS EDW API -> 3,220 forest trails
│                              (POST + Colorado bbox, page size 500)
└── osm_overpass_connector.py  OSM Overpass -> 1,009 unique trails
                               (3-layer dedup, mirror fallback)

backend/scripts/
└── cache_trail_photos.py      Unsplash pipeline
                               (15 nature queries, urban filter,
                                specific search for named trails)
```

---

## ENVIRONMENT VARIABLES

### `ai/.env`

| Variable | Status | Notes |
|---|---|---|
| `MONGO_URI` | SET | MongoDB Atlas connection string |
| `OPENAI_API_KEY` | SET | OpenAI API key |
| `UNSPLASH_ACCESS_KEY` | SET | Unsplash photos |
| `NPS_API_KEY` | SET | NPS park alerts (not yet used) |
| `OPENAI_CHAT_MODEL` | default | gpt-4o-mini |
| `OPENAI_EMBEDDING_MODEL` | default | text-embedding-3-small |

### `frontend/nextjs-app/.env.local`

| Variable | Status |
|---|---|
| `NEXT_PUBLIC_API_URL` | SET — http://localhost:8000 |

---

## STARTUP
```bash
bash start.sh     # starts both servers with health checks
bash stop.sh      # stops both servers
```

Logs: `logs/backend.log` | `logs/frontend.log`

### Quick fixes

| Problem | Fix |
|---|---|
| Page goes blank | `cd frontend/nextjs-app && rm -rf .next && npm run dev` |
| Chat returns empty | `python -m ai.rag.rebuild_index` |
| No photos | `python -m backend.scripts.cache_trail_photos` |
| Port conflict | `bash stop.sh` then `bash start.sh` |

---

## KNOWN LIMITATIONS

- MongoDB M0 free tier: 512MB limit (currently ~4MB used)
- Unsplash demo tier: 50 requests/hour
- iNaturalist: ~10,000 requests/day (no key needed)
- 92 trails have no coordinates — not shown on map (expected)
- 678 OSM trails tagged region "Colorado" (fallback) — intentional
- hp_rating null for most trails — HP API shut down Dec 2020
- NPS_API_KEY set but NPS alerts endpoint not yet built
- HyDE adds ~2s latency per chat query (GPT call overhead)
- Cross-encoder model ~80MB download on first run

---

## PENDING FEATURES

Ordered by priority. When implementing, say:
"Implement PENDING FEATURE #N — [name]"

---

### #1 — AI Trail Narrator
**Priority:** Medium — flagship AI differentiator
**New endpoint:** `POST /api/trails/narrate`
**Modified files:** `TrailDetail.tsx`, `api.ts`

**What it does:**
When a trail is selected, GPT-4o-mini generates a personalized
2-3 sentence hike preview based on current weather, season,
and trail characteristics. This is unique — AllTrails has nothing
like this.

**Backend endpoint:**
```python
@router.post("/api/trails/narrate")
async def narrate_trail(
    trail_name: str,
    weather_summary: str,
    season: str
):
    prompt = f"""Write a 2-3 sentence hiking preview for {trail_name}.
    Current conditions: {weather_summary}
    Season: {season}
    Be specific, practical, and safety-aware.
    Mention what makes today a good or bad day for this trail.
    Do not use generic phrases."""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.4
    )
    return {"narrative": response.choices[0].message.content}
```

**Display in TrailDetail.tsx:**
Below HP summary, above stats grid:
Italic paragraph with "🤖 AI Preview" label in small muted text.
Loads asynchronously — show skeleton while generating.

Cost: ~$0.001 per trail view with GPT-4o-mini.

---

### #2 — Dynamic Difficulty Adjustment
**Priority:** Medium — weather integration showcase
**No new endpoints needed** — computed in frontend
**Modified files:** `TrailDetail.tsx`

**Logic:**
```typescript
function adjustDifficulty(
  baseDifficulty: string,
  weather: WeatherResponse
): { adjusted: string; reason: string } | null {

  const modifiers: string[] = []
  let bump = 0

  if (weather.current.snow_depth_cm > 8)  { bump += 2; modifiers.push("deep snow") }
  if (weather.current.snow_depth_cm > 2)  { bump += 1; modifiers.push("snow") }
  if (weather.current.temperature_f < 20) { bump += 1; modifiers.push("extreme cold") }
  if (weather.current.wind_mph > 35)      { bump += 1; modifiers.push("high winds") }
  if (weather.current.precipitation > 0.3){ bump += 1; modifiers.push("heavy rain") }

  if (bump === 0) return null

  const levels = ["Easy", "Moderate", "Hard", "Extreme"]
  const baseIdx = levels.indexOf(baseDifficulty)
  const newIdx = Math.min(levels.length - 1, baseIdx + bump)

  return {
    adjusted: levels[newIdx] + " Today",
    reason: modifiers.join(", ")
  }
}
```

**Display in TrailDetail.tsx:**
Next to the official difficulty badge, show adjusted badge
in amber/red if conditions bump the difficulty:
`[Easy] → [Hard Today ⚠️ deep snow, high winds]`

---

### #3 — Weather Safety Score
**Priority:** Medium — at-a-glance safety indicator
**No new endpoints needed** — computed in frontend
**Modified files:** `TrailDetail.tsx`

**Algorithm:**
```typescript
function weatherSafetyScore(weather: CurrentWeather): {
  score: number; label: string; color: string
} {
  let score = 100
  const t = weather.temperature_f
  const wind = weather.wind_mph
  const snow = weather.snow_depth_cm / 2.54  // to inches
  const rain = weather.precipitation

  if (t < 20)        score -= 30
  else if (t < 32)   score -= 15
  else if (t > 95)   score -= 20

  if (wind > 40)     score -= 25
  else if (wind > 25) score -= 10

  if (snow > 6)      score -= 30
  else if (snow > 2) score -= 15

  if (rain > 0.5)    score -= 20
  else if (rain > 0.1) score -= 5

  score = Math.max(0, Math.min(100, score))

  return {
    score,
    label: score >= 80 ? "Good" : score >= 50 ? "Fair" :
           score >= 20 ? "Poor" : "Dangerous",
    color: score >= 80 ? "text-green-400" :
           score >= 50 ? "text-amber-400" :
           score >= 20 ? "text-orange-400" : "text-red-500"
  }
}
```

**Display:** Single colored badge in weather section:
"Safety: Good 92" in green
"Safety: Poor 31" in orange

---

### #4 — GPX Route Export
**Priority:** Medium — high value for serious hikers
**New endpoint:** `GET /api/geometry/gpx?names={trail_name}`
**Modified files:** `TrailDetail.tsx`, `geometry.py`

**Backend:**
Convert trail polyline coordinates to GPX XML format:
```xml
<?xml version="1.0"?>
<gpx version="1.1" creator="TrailBlaze AI">
  <trk>
    <name>{trail_name}</name>
    <trkseg>
      <trkpt lat="40.31" lon="-105.68">
        <ele>2987</ele>
      </trkpt>
      ...
    </trkseg>
  </trk>
</gpx>
```

Return as file download with Content-Disposition header.

**Frontend:** "⬇ Download GPX" button in route info section.
Opens `window.open(gpxUrl)` — browser downloads the file.

No new npm packages needed.

---

### #5 — Saved / Favorite Trails
**Priority:** Medium — personalization, no backend needed
**No new endpoints** — localStorage only
**Modified files:** `page.tsx`, `TrailCards.tsx`, `TrailDetail.tsx`

**Storage:** `localStorage.getItem("trailblaze_favorites")`
Stored as JSON array of trail names: `["Bear Lake Trail", ...]`

**UI changes:**
- Heart icon button on each trail card (filled if saved)
- Heart icon button in TrailDetail.tsx header
- Click to toggle saved state
- "Saved Trails" chip in sidebar above region chips
  → Clicking filters trail cards to saved trails only
- Count badge on chip: "❤ Saved (3)"

No npm packages, no backend, persists across sessions.

---

### #6 — NPS Park Alerts
**Priority:** Medium — safety for RMNP visitors
**NPS_API_KEY** is already set in `ai/.env`
**New endpoint:** `GET /api/nps/alerts?park=romo`
**New file:** `backend/app/routes/nps.py`
**Modified files:** `TrailDetail.tsx`

**NPS API call:**
```
GET https://developer.nps.gov/api/v1/alerts
    ?parkCode=romo
    &api_key={NPS_API_KEY}
```

**Display in TrailDetail.tsx:**
For NPS trails only (source === "NPS"), show alert banner
above the weather section if active alerts exist:
- Red banner for closures/dangers
- Amber banner for cautions
- Blue banner for information

Cache alerts for 1 hour to avoid rate limits.

---

### #7 — Surprise Me Mode
**Priority:** Medium — fun differentiator
**New endpoint:** `POST /api/trails/surprise`
**Modified files:** `ChatPanel.tsx` or new button in sidebar

**What it does:**
AI picks a hidden gem trail based on current weather across
Colorado. Filters for trails with few reviews and good conditions.

**Logic:**
```python
async def surprise_trail(preferences: dict) -> dict:
    # Get trails with few/no reviews (hidden gems)
    candidates = await db.trails.find({
        "coordinates": {"$exists": True},
        "review_count": {"$lt": 5}  # or no reviews field
    }).limit(200).to_list(200)

    # Filter by current weather at each trail location
    # (batch weather check for top 20 candidates)

    # Use LangGraph to pick the best one with explanation
    context = format_trails_for_ai(top_candidates)
    narrative = await generate_surprise_narrative(context)

    return {"trail": chosen_trail, "reason": narrative}
```

**UI:** "🎲 Surprise Me" button in sidebar below region chips.
Shows a modal with the recommended trail + AI explanation.

---

### #8 — Itinerary Builder (AI-powered)
**Priority:** Medium — existing backend route, needs AI layer
**Note:** `POST /api/itineraries` endpoint already exists
**New enhancement:** AI-generated itinerary suggestions
**Modified files:** `ChatPanel.tsx`

**What it does:**
User describes a weekend trip in chat and AI builds a full
itinerary: which trails each day, estimated drive times,
best start times based on weather.

**Chat trigger:**
When query contains "weekend", "itinerary", "plan my trip",
"two days", "multi-day" → new intent: `"itinerary"`

**LangGraph addition:**
New `itinerary_agent` that:
1. Identifies requested region, duration, difficulty prefs
2. Queries multiple trails with good conditions
3. Arranges them into day-by-day schedule
4. Estimates drive times between trails using straight-line
   distance (no API needed)
5. Returns structured itinerary saved to `trailblaze.itineraries`

**State field to add:** `"itinerary"` intent in Router Agent

---

### #9 — Voice Input in Chat
**Priority:** Low — easy win
**No new backend** — frontend only
**Modified files:** `ChatPanel.tsx`

**Implementation:**
```typescript
const recognition = new (window as any).webkitSpeechRecognition()
recognition.lang = 'en-US'
recognition.onresult = (e: any) => {
  const transcript = e.results[0][0].transcript
  setInputValue(transcript)
}
```

**UI:** Microphone icon button next to chat input field.
Tap to start, tap again to stop. Populates input field with
transcript. User can edit before sending.

Works in Chrome/Safari. Falls back gracefully in Firefox.
No new npm packages, no API key, no cost.

---

### #10 — Multi-language Chat (EN/ES)
**Priority:** Low — accessibility
**No new backend endpoint** — prompt engineering only
**Modified files:** `ChatPanel.tsx`, `ai/langgraph/agents.py`

**Implementation:**
- Language toggle in ChatPanel.tsx: EN | ES
- Store preference in localStorage
- Pass `language: "es"` in chat request body
- In Synthesizer Agent system prompt, add:
  `"Respond in {language}. Trail names stay in English."`

**UI:** Small EN/ES toggle pill in ChatPanel header.

---

### #11 — Sunrise/Sunset Calculator
**Priority:** Low — useful for photographers and safety
**No new backend needed** — frontend computation
**Modified files:** `TrailDetail.tsx`
**Library:** SunCalc.js (no install needed — use CDN or
  copy the ~400 line open-source file into `lib/suncalc.ts`)

**Display in TrailDetail.tsx:**
Below the 4-day forecast:
"🌅 Sunrise: 6:23am  🌄 Sunset: 7:41pm"
"Golden hour: 6:23–6:51am and 7:13–7:41pm"
"Safe turnaround for day hike: 4:41pm (1hr before sunset)"

Uses trail coordinates already available in the detail panel.
No API call — computed locally from lat/lng + current date.

---

### #12 — 3D Terrain View
**Priority:** Low — visually impressive but complex
**New dependency:** Mapbox GL JS (requires Mapbox token)
**Modified files:** `TrailMap.tsx`

**What it does:**
Toggle button in layer control: "2D / 3D"
Switches from Leaflet flat map to Mapbox GL 3D terrain flyover
using the existing Mapbox token (already in .env but unused).

**Note:** NEXT_PUBLIC_MAPBOX_TOKEN is in .env.local but currently
empty. Requires a free Mapbox account to get a token.

**Only implement if Mapbox token is set** — check env var first.

---

### #13 — Fire Risk / Avalanche Map Overlays
**Priority:** Low — safety information
**No new backend** — external tile layers
**Modified files:** `TrailMap.tsx` (layer control)

**New overlay layers to add:**
```javascript
// Colorado Avalanche Information Center
"Avalanche Zones": L.tileLayer(
  "https://services.coloradoavalanchecenter.org/...",
  { opacity: 0.5 }
)

// NIFC Fire perimeters (GeoJSON, free)
// URL: https://services3.arcgis.com/T4QMspbfLg3qTGWY/...
"Active Fire Areas": L.geoJSON(fireData, { ... })
```

Add to existing layer control in TrailMap.tsx as optional
toggleable overlays. Both OFF by default.

---

## COMPLETED FEATURES

### ✅ Fitness Matching
**Completed:** April 2026
**Note:** localStorage only. No backend. No API key.
**Files created:** None
**Files modified:**
  frontend/nextjs-app/src/app/page.tsx (lines 9, 29-71, 260-266, 414-424, 473-583)
    FitnessProfile interface, state, localStorage load/save, gear icon in header,
    settings panel (slide-out), fitnessProfile prop to TrailCards
  frontend/nextjs-app/src/components/TrailCards.tsx (lines 16-53, 55, 136-137, 142-143, 215-228)
    FitnessProfile interface, matchesFitnessProfile(), estimateHikeTime(),
    fitnessProfile prop, opacity dimming, match/outside badges, pace estimate
  frontend/nextjs-app/src/lib/api.ts (lines 10-11)
    Added elevation_gain_ft and surface to TrailReference interface
**No new npm packages. No FAISS rebuild. No backend changes.**

### ✅ Isochrone / Drive-Time Filter
**Completed:** April 2026
**Note:** Requires ORS_API_KEY in ai/.env to function.
  Returns {"error": "..."} gracefully if key not set.
**Files created:**
  backend/app/routes/isochrone.py (lines 1-73)
**Files modified:**
  backend/app/main.py (lines 32, 76) — import + register isochrone_router
  frontend/nextjs-app/src/lib/api.ts (lines 171-194) — IsochroneResponse + fetchIsochrone()
  frontend/nextjs-app/src/app/page.tsx (lines 9-10, 29-34, 53-103, 182-199, 245-298, 383)
    Isochrone state, pointInPolygon, geocode+fetch, sidebar UI, polygon prop
  frontend/nextjs-app/src/components/TrailMap.tsx (lines 153, 163, 172, 244-275)
    isochronePolygon prop + GeoJSON layer rendering
**New endpoint:** GET /api/trails/isochrone
**No new npm packages. No FAISS rebuild. No hardcoded credentials.**

### ✅ Crowd Prediction Engine
**Completed:** April 2026
**Files created:**
  backend/app/services/crowd_predictor.py
**Files modified:**
  backend/app/routes/trails.py — GET /api/trails/crowd/{trail_name}
  frontend/nextjs-app/src/lib/api.ts — fetchCrowdPrediction()
  frontend/nextjs-app/src/components/TrailDetail.tsx
**No new npm packages. No FAISS rebuild.**

### ✅ Seasonal Heatmap
**Completed:** April 2026
**Files created:**
  backend/app/services/seasonal_analyzer.py
**Files modified:**
  backend/app/routes/trails.py — GET /api/trails/seasonal/{trail_name}
  frontend/nextjs-app/src/lib/api.ts — fetchSeasonalData()
  frontend/nextjs-app/src/components/TrailDetail.tsx
**No new npm packages. No FAISS rebuild.**

### #1 — Cluster Style Change ✅
**Completed:** April 2026
**File modified:**
  frontend/nextjs-app/src/components/TrailMap.tsx (lines 75-141)
**What was built:**
  Replaced solid circle cluster icons with SVG donut chart clusters.
  Green/amber/red arcs show Easy/Moderate/Hard trail proportions.
  White center with dark trail count. Border = dominant difficulty.
  Size scales: <10=36px, <50=44px, 50+=52px. Hover scale effect.
  Technique: stroke-dasharray + stroke-dashoffset on stacked SVG
  circles rotated -90deg so arcs start at 12 o'clock.
**No backend changes. No new dependencies. No FAISS rebuild.**

### #1 — User Reviews + Trip Reports ✅
**Completed:** April 2026
**Files created:**
  backend/app/routes/reviews.py (lines 1-117)
    3 endpoints: POST /api/reviews,
    GET /api/reviews/{trail_name},
    GET /api/reviews/{trail_name}/summary
**Files modified:**
  backend/app/main.py (lines 31, 74) — import + register router
  frontend/nextjs-app/src/lib/api.ts (lines 346-421)
    Review, ReviewSummary interfaces +
    fetchReviews, fetchReviewSummary, submitReview
  frontend/nextjs-app/src/components/TrailDetail.tsx
    (lines 30-40, 97-209, 693-916)
    State, useEffect, handleReviewSubmit, loadMoreReviews,
    full reviews section UI with rating bars + write form
  frontend/nextjs-app/src/components/TrailCards.tsx
    (lines 5, 25-54, 79-137)
    Star rating display on each trail card
**New MongoDB collection:** trailblaze.reviews
**No new npm packages. No FAISS rebuild. No hardcoded credentials.**

### #1 — Sentiment Analysis on Reviews ✅
**Completed:** April 2026
**Files created:**
  data-engineering/pipeline/sentiment_analyzer.py (lines 1-151)
**Files modified:**
  backend/app/routes/reviews.py (lines 30-42, 87-107, 127-133)
    Added sentiment_summary lookup from trails collection and included
    sentiment_summary in review summary response.
  frontend/nextjs-app/src/lib/api.ts (lines 359-374)
    Extended ReviewSummary with optional sentiment_summary payload.
  frontend/nextjs-app/src/components/TrailDetail.tsx
    (lines 80-100, 799-818)
    Added sentiment theme chip display below review summary.
**Stored in trail document:** sentiment_summary
  { positive_pct, themes, last_analyzed, review_count_analyzed }
**Run command:**
  python -m data_engineering.pipeline.sentiment_analyzer
**No new npm packages. No FAISS rebuild. No hardcoded credentials.**

### #2 — Best Day Predictor ✅
**Completed:** April 2026
**Files modified:**
  backend/app/routes/trails.py (lines 159-275)
    Added `GET /api/trails/best-day/{trail_name}` endpoint with 7-day
    weather scoring + reason generation from Open-Meteo data.
  frontend/nextjs-app/src/lib/api.ts (lines 89-109)
    Added `BestDayPrediction` interface and `fetchBestDayPrediction`.
  frontend/nextjs-app/src/components/TrailDetail.tsx
    (lines 27, 42, 131, 201-209, 548-610)
    Added best-day state/effect and UI banner between 4-day forecast and
    trail condition buttons.
**New backend endpoints added:**
  GET /api/trails/best-day/{trail_name}
**No new npm packages. No FAISS rebuild. No hardcoded credentials.**

### #3 — TrailBlaze Score™ ✅
**Completed:** April 2026
**Files created:**
  backend/app/services/scoring.py (lines 1-89)
**Files modified:**
  backend/app/models/trail.py (lines 53-55)
    Added `trailblaze_score` field to trail response model.
  backend/app/routes/trails.py
    (lines 15, 40, 48-65, 96, 133, 174, 354, 384, 402, 418)
    Integrated score computation + propagation across featured/search/
    nearby/region/single trail responses.
  frontend/nextjs-app/src/lib/api.ts
    (lines 12, 40, 131)
    Added `trailblaze_score` to TrailReference/Trail/MapTrail types.
  frontend/nextjs-app/src/app/page.tsx
    (lines 68, 113, 242)
    Passed `trailblaze_score` through sidebar and selected-trail mapping.
  frontend/nextjs-app/src/components/TrailCards.tsx
    (lines 26, 59-64, 78-100, 162-166)
    Added score sort toggle and score badge on cards.
  frontend/nextjs-app/src/components/TrailDetail.tsx
    (lines 337-351)
    Added TrailBlaze score badge with green/amber/red tiers + tooltip.
**Stored in trail document:** trailblaze_score
**No new npm packages. No FAISS rebuild. No hardcoded credentials.**

### #4 — Wildlife Alert Badge on Map Pins ✅
**Completed:** April 2026
**Files created:**
  backend/app/services/wildlife_alerts.py (lines 1-95)
  backend/scripts/cache_wildlife_alerts.py (lines 1-49)
**Files modified:**
  backend/app/models/trail.py (lines 54-55)
    Added `wildlife_alert` and `wildlife_alert_species` fields.
  backend/app/routes/trails.py (lines 41-42, 136-137)
    Included cached wildlife alert fields in map trail responses.
  frontend/nextjs-app/src/lib/api.ts (lines 13-14, 43-44, 136-137)
    Added wildlife alert fields to shared trail interfaces.
  frontend/nextjs-app/src/components/TrailMap.tsx
    (lines 32, 52, 286, 304)
    Added red exclamation badge on pin icon + wildlife tooltip details.
**Cache strategy:**
  Wildlife alerts are cached in MongoDB and refreshed via
  `python -m backend.scripts.cache_wildlife_alerts` (e.g., cron every 6h).
**No new npm packages. No FAISS rebuild. No hardcoded credentials.**

---

## NOT BUILDING (out of scope)

- Mobile app (iOS/Android) — future phase
- AWS deployment — future phase
- User authentication / accounts with passwords
- Push notifications
- Offline map download
- Photo uploads with AI tagging (needs storage solution)
- Permit detection via Recreation.gov (API access restricted)

---

## HOW TO REQUEST IMPLEMENTATION

Say: "Implement PENDING FEATURE #N — [feature name]"

The agent must:
1. Read this file completely first
2. Read all relevant existing files before writing any code
3. Follow existing patterns:
   - db reference: same as in `backend/app/routes/trails.py`
   - serialize: use existing `serialize_trail()` pattern
   - API_BASE: use existing constant from `api.ts`
   - Trail type: use existing `Trail` interface from `api.ts`
4. Never install new npm packages
5. Never hardcode credentials — always use `.env`
6. Run `npx tsc --noEmit` after frontend changes
7. Run `npm run build` after TypeScript check
8. Run `rm -rf .next` after every build
9. Report every file modified with exact line numbers
10. Run verification tests before marking complete
11. Fix all test failures before reporting done
12. After any build failure: stop and report — do not keep changing

---

## AGENT RULES

- Read files before writing — never assume file contents
- One feature at a time — do not combine multiple features
- Fix all failures before moving on
- After every build: `rm -rf frontend/nextjs-app/.next`
- If command runs >60s with no output: print timeout warning
- Never break existing functionality
- Never touch files not related to the current feature
- Report exact file paths and line numbers for every change
- When in doubt about an existing pattern: read the file first