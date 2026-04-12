"""
Integration tests for the FastAPI backend.
Tests all endpoints against live MongoDB Atlas.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database import connect_db, close_db


@pytest_asyncio.fixture
async def client():
    """Create an async test client with DB connection."""
    await connect_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_db()


# --- Health ---

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app"] == "TrailBlaze AI"


# --- Trails ---

@pytest.mark.asyncio
async def test_list_trails(client):
    resp = await client.get("/api/trails?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "trails" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["trails"]) <= 5


@pytest.mark.asyncio
async def test_list_trails_filter_difficulty(client):
    resp = await client.get("/api/trails?difficulty=easy&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    for trail in data["trails"]:
        assert trail["difficulty"] == "easy"


@pytest.mark.asyncio
async def test_get_trail_not_found(client):
    resp = await client.get("/api/trails/9999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_trails(client):
    resp = await client.get("/api/trails/search/trail?page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "trails" in data


# --- Trailheads ---

@pytest.mark.asyncio
async def test_list_trailheads(client):
    resp = await client.get("/api/trailheads?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "trailheads" in data
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_get_trailhead_not_found(client):
    resp = await client.get("/api/trailheads/9999999")
    assert resp.status_code == 404


# --- Sessions ---

@pytest.mark.asyncio
async def test_create_and_get_session(client):
    # Create
    resp = await client.post("/api/sessions", json={"user_id": "test_user"})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert data["user_id"] == "test_user"
    session_id = data["session_id"]

    # Get
    resp = await client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    resp = await client.get("/api/sessions/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_chat_history_empty(client):
    # Create session first
    resp = await client.post("/api/sessions")
    session_id = resp.json()["session_id"]

    # Get empty history
    resp = await client.get(f"/api/sessions/{session_id}/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["total"] == 0


# --- Chat ---

@pytest.mark.asyncio
async def test_chat_trail_query(client):
    resp = await client.post("/api/chat", json={"query": "Find a moderate trail near Boulder"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["route"] == "trail"
    assert "session_id" in data
    assert len(data["answer"]) > 20


@pytest.mark.asyncio
async def test_chat_weather_query(client):
    resp = await client.post("/api/chat", json={"query": "What's the weather forecast for hiking?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["route"] == "weather"


@pytest.mark.asyncio
async def test_chat_with_session(client):
    # Create session
    resp = await client.post("/api/sessions")
    session_id = resp.json()["session_id"]

    # Chat with session
    resp = await client.post("/api/chat", json={
        "query": "Best beginner trail?",
        "session_id": session_id,
    })
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id

    # Verify history was saved
    resp = await client.get(f"/api/sessions/{session_id}/history")
    data = resp.json()
    assert data["total"] == 2  # user message + assistant response


@pytest.mark.asyncio
async def test_chat_empty_query_rejected(client):
    resp = await client.post("/api/chat", json={"query": ""})
    assert resp.status_code == 422  # Validation error


# --- Itineraries ---

@pytest.mark.asyncio
async def test_create_and_get_itinerary(client):
    body = {
        "title": "Test Weekend Hike",
        "trails": [
            {"name": "Royal Arch Trail", "difficulty": "moderate", "length_miles": 3.4, "order": 1},
            {"name": "Bear Lake Loop", "difficulty": "easy", "length_miles": 0.8, "order": 2},
        ],
    }
    resp = await client.post("/api/itineraries", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Weekend Hike"
    assert len(data["trails"]) == 2
    itin_id = data["itinerary_id"]

    # Get it back
    resp = await client.get(f"/api/itineraries/{itin_id}")
    assert resp.status_code == 200
    assert resp.json()["itinerary_id"] == itin_id


@pytest.mark.asyncio
async def test_list_itineraries(client):
    resp = await client.get("/api/itineraries")
    assert resp.status_code == 200
    data = resp.json()
    assert "itineraries" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_delete_itinerary(client):
    # Create
    resp = await client.post("/api/itineraries", json={"title": "Delete Me"})
    itin_id = resp.json()["itinerary_id"]

    # Delete
    resp = await client.delete(f"/api/itineraries/{itin_id}")
    assert resp.status_code == 204

    # Verify gone
    resp = await client.get(f"/api/itineraries/{itin_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_itinerary_not_found(client):
    resp = await client.delete("/api/itineraries/nonexistent")
    assert resp.status_code == 404
