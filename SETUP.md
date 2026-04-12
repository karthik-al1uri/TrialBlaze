# TrailBlaze AI — Setup Guide

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required for backend and AI pipeline |
| Node.js | 18+ | Required for frontend |
| MongoDB Atlas | Free M0 tier | Cloud-hosted, no local install needed |
| OpenAI API key | — | Required for AI chat and embeddings |

## 1. Clone the Repository

```bash
git clone https://github.com/<your-org>/TrailBlaze-AI.git
cd TrailBlaze-AI
```

## 2. Python Environment

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

## 3. Environment Variables

Copy the example env file and fill in your values:

```bash
cp ai/.env.example ai/.env
```

Open `ai/.env` and set the following:

| Variable | Required | Where to get it |
|---|---|---|
| `MONGO_URI` | Yes | MongoDB Atlas → Connect → Drivers |
| `OPENAI_API_KEY` | Yes | platform.openai.com/api-keys |
| `UNSPLASH_ACCESS_KEY` | Optional | unsplash.com/developers |
| `NPS_API_KEY` | Optional | developer.nps.gov/signup |

Copy the frontend env file:

```bash
cp frontend/nextjs-app/.env.local.example \
   frontend/nextjs-app/.env.local
```

The only frontend variable is:

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_MAPBOX_TOKEN` | No | Not used — app uses Leaflet/OpenStreetMap |

## 4. Frontend Dependencies

```bash
cd frontend/nextjs-app
npm install
cd ../..
```

## 5. Build the FAISS Index

The AI chat requires a FAISS vector index built from trail data in MongoDB.

```bash
python -m ai.rag.rebuild_index
```

Expected output:
```
Loading trails from MongoDB...
Loaded 5,661 trails total...
Generating embeddings in batches of 100...
FAISS rebuild complete.
```

This creates `ai/vector-store/index.faiss` and `ai/vector-store/index.pkl`.

## 6. Cache Trail Photos (Optional)

Pre-fetch Unsplash photos so the UI shows real trail images:

```bash
# Preview what will be cached (no writes):
python -m backend.scripts.cache_trail_photos --dry-run

# Run the full cache:
python -m backend.scripts.cache_trail_photos
```

This populates the `trail_photos` collection in MongoDB. Takes ~2 minutes.

## 7. Start the Application

### Quick Start (Recommended)

```bash
bash start.sh
```

This starts both servers, checks health, and prints URLs when ready.
Press `Ctrl+C` to stop both servers.

### Manual Start

**Backend (FastAPI):**
```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

**Frontend (Next.js):**
```bash
cd frontend/nextjs-app
npm run dev
```

### Stop Servers

```bash
bash stop.sh
```

## 8. Verify Everything Works

| Check | Command | Expected |
|---|---|---|
| Backend health | `curl http://localhost:8000/health` | `{"status": "healthy"}` |
| Frontend loads | Open http://localhost:3000 | Map renders with trail pins |
| API docs | Open http://localhost:8000/docs | Swagger UI |
| FAISS index | `python -c "import faiss; idx = faiss.read_index('ai/vector-store/index.faiss'); print(idx.ntotal)"` | `5661` |
| Trail search | `curl "http://localhost:8000/api/trails/search/Bear?page_size=3"` | JSON with trail results |

## Project Structure

```
TrailBlaze-AI/
├── ai/                          # AI pipeline
│   ├── langgraph/               # LangGraph agents (router, vector, weather, synthesizer)
│   ├── rag/                     # RAG pipeline and FAISS index builder
│   ├── vector-store/            # FAISS index files (generated)
│   ├── services/                # Geography and utility services
│   └── .env                     # Environment variables (not in git)
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py              # App entry point
│   │   ├── routes/              # API endpoints
│   │   │   ├── trails.py        # /api/trails/*
│   │   │   ├── geometry.py      # /api/geometry
│   │   │   ├── photos.py        # /api/photos
│   │   │   ├── conditions.py    # /api/conditions/*
│   │   │   └── chat.py          # /api/chat
│   │   ├── models/              # Pydantic models
│   │   └── database.py          # MongoDB connection
│   └── scripts/
│       └── cache_trail_photos.py
├── frontend/
│   └── nextjs-app/              # Next.js 15 frontend
│       ├── src/app/             # Pages (App Router)
│       ├── src/components/      # React components
│       │   ├── TrailMap.tsx      # Leaflet map with clusters
│       │   ├── TrailDetail.tsx   # Trail detail sidebar
│       │   ├── ElevationProfile.tsx
│       │   └── ClusterDrawer.tsx
│       └── src/lib/api.ts       # API client functions
├── data-engineering/            # Scrapers and data connectors
├── start.sh                     # Start both servers
├── stop.sh                      # Stop both servers
└── logs/                        # Server logs (gitignored)
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/trails` | List trails with pagination and filters |
| GET | `/api/trails/featured` | All trails with coordinates for map |
| GET | `/api/trails/nearby` | Trails near a lat/lng |
| GET | `/api/trails/by-region/{region}` | Trails filtered by region |
| GET | `/api/trails/search/{name}` | Search trails by name |
| GET | `/api/trails/{cotrex_fid}` | Single trail by COTREX FID |
| GET | `/api/geometry` | Trail polylines and elevation profiles |
| GET | `/api/photos` | Cached trail photos |
| GET | `/api/conditions/{trail_name}` | Trail condition reports |
| POST | `/api/conditions/report` | Submit a condition report |
| POST | `/api/chat` | AI chat (LangGraph + RAG) |
| GET | `/health` | Backend health check |

## Troubleshooting

### Frontend shows "Internal Server Error"

This is usually a stale Next.js webpack cache:

```bash
cd frontend/nextjs-app
rm -rf .next node_modules/.cache
npm run dev
```

### Backend won't start

Check `logs/backend.log` or run manually to see the error:

```bash
PYTHONPATH=. python -m uvicorn backend.app.main:app --port 8000
```

Common causes:
- `MONGO_URI` not set or wrong credentials
- `OPENAI_API_KEY` not set
- Port 8000 already in use → `bash stop.sh` first

### FAISS index is empty or missing

Rebuild it:

```bash
python -m ai.rag.rebuild_index
```

Requires `MONGO_URI` and `OPENAI_API_KEY` to be set in `ai/.env`.

### Photos show gradient fallback instead of real images

Run the photo caching script:

```bash
python -m backend.scripts.cache_trail_photos
```

Requires `UNSPLASH_ACCESS_KEY` in `ai/.env`.
