"""
End-to-end acceptance tests for Task 6.
Verifies the full pipeline: user query → LangGraph → FAISS (MongoDB trails) → grounded AI response.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database import connect_db, close_db
from backend.app.services.ai_service import initialize_ai, _compiled_graph


@pytest_asyncio.fixture
async def client():
    """Create an async test client with DB + AI service initialized."""
    await connect_db()
    if _compiled_graph is None:
        await initialize_ai()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_db()


# --- E2E: Trail query through live AI pipeline ---

@pytest.mark.asyncio
async def test_e2e_trail_query_returns_grounded_answer(client):
    """User asks about trails → AI returns a grounded answer with real trail data."""
    resp = await client.post("/api/chat", json={"query": "Find an easy hike near Boulder"})
    assert resp.status_code == 200
    data = resp.json()

    # Must have an answer
    assert len(data["answer"]) > 50
    # Route should be trail
    assert data["route"] == "trail"
    # Must reference at least one trail
    assert len(data["trails_referenced"]) >= 1
    # Quality check should pass
    assert data["quality_check"]["overall_passed"] is True
    # Session should be created
    assert data["session_id"] is not None


@pytest.mark.asyncio
async def test_e2e_weather_query_returns_weather_context(client):
    """User asks about weather → AI routes to weather agent."""
    resp = await client.post("/api/chat", json={"query": "What is the weather like for hiking today?"})
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["answer"]) > 50
    assert data["route"] == "weather"
    assert data["session_id"] is not None


@pytest.mark.asyncio
async def test_e2e_both_query_combines_trail_and_weather(client):
    """User asks about trails AND weather → AI routes through both agents."""
    resp = await client.post("/api/chat", json={
        "query": "What's a good trail for hiking today given the weather conditions?"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["answer"]) > 50
    assert data["route"] == "both"
    assert data["session_id"] is not None


@pytest.mark.asyncio
async def test_e2e_chat_history_persisted(client):
    """Chat messages are saved and retrievable from session history."""
    # Create session
    resp = await client.post("/api/sessions", json={"user_id": "e2e_tester"})
    session_id = resp.json()["session_id"]

    # Send chat with session
    resp = await client.post("/api/chat", json={
        "query": "Best family trail in Colorado?",
        "session_id": session_id,
    })
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id

    # Verify history has both user + assistant messages
    resp = await client.get(f"/api/sessions/{session_id}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert history["total"] == 2
    assert history["messages"][0]["role"] == "user"
    assert history["messages"][1]["role"] == "assistant"
    assert "trail" in history["messages"][1]["content"].lower() or len(history["messages"][1]["content"]) > 50


@pytest.mark.asyncio
async def test_e2e_trail_data_from_mongodb(client):
    """Verify trails API returns real data from MongoDB Atlas."""
    resp = await client.get("/api/trails?page_size=3")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] > 1000  # We loaded 1272 trails
    assert len(data["trails"]) == 3
    # Each trail should have a name and source
    for trail in data["trails"]:
        assert trail["name"]
        assert trail["source"] == "cotrex"
