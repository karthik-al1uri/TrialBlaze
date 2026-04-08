"""
TrailBlaze AI — FastAPI Backend Application.

Provides REST API endpoints for:
  - Trail and trailhead data (from MongoDB)
  - Chat (AI orchestration entrypoint)
  - Session management and chat history
  - Itinerary persistence
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import connect_db, close_db
from backend.app.services.ai_service import initialize_ai

logger = logging.getLogger(__name__)
from backend.app.routes.health import router as health_router
from backend.app.routes.trails import router as trails_router
from backend.app.routes.trails import trailheads_router
from backend.app.routes.sessions import router as sessions_router
from backend.app.routes.chat import router as chat_router
from backend.app.routes.itineraries import router as itineraries_router
from backend.app.routes.geometry import router as geometry_router
from backend.app.routes.photos import router as photos_router
from backend.app.routes.weather import router as weather_router
from backend.app.routes.conditions import router as conditions_router
from backend.app.routes.reviews import router as reviews_router
from backend.app.routes.isochrone import router as isochrone_router
from backend.app.routes.narrate import router as narrate_router
from backend.app.routes.nps import router as nps_router
from backend.app.routes.sun import router as sun_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown events."""
    await connect_db()
    try:
        await initialize_ai()
        logger.info("AI service initialized successfully.")
    except Exception as e:
        logger.warning(f"AI service init failed ({e}); chat will use fallback mock responses.")
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered outdoor guidance platform for Colorado trails",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(trails_router)
app.include_router(trailheads_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(itineraries_router)
app.include_router(geometry_router)
app.include_router(photos_router)
app.include_router(weather_router)
app.include_router(conditions_router)
app.include_router(reviews_router)
app.include_router(isochrone_router)
app.include_router(narrate_router)
app.include_router(nps_router)
app.include_router(sun_router)
