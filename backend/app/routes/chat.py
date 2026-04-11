"""
Chat endpoint — connects frontend requests to AI orchestration.
Routes user queries through the live LangGraph pipeline with FAISS retrieval
over real MongoDB trail data, with mock fallback if AI service is unavailable.
"""

import logging

from fastapi import APIRouter

from backend.app.models.chat import ChatRequest, ChatResponse, TrailReference
from backend.app.routes.sessions import save_message
from backend.app.database import get_db
from backend.app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Fallback mock responses when AI service is not available
_MOCK_RESPONSES = {
    "trail": {
        "answer": (
            "Based on your query, I recommend the Royal Arch Trail near Boulder. "
            "It's a 3.4-mile moderate hike with 1,400 ft elevation gain. "
            "The trail features shaded pine forest sections and ends at a stunning "
            "natural stone arch with panoramic views."
        ),
        "trails": [
            TrailReference(name="Royal Arch Trail", difficulty="moderate", length_miles=3.4),
            TrailReference(name="Mount Sanitas Trail", difficulty="moderate", length_miles=3.2),
        ],
    },
    "weather": {
        "answer": (
            "This afternoon in the Colorado Rockies, expect temperatures around 70°F "
            "with mostly sunny skies and light winds. Low risk of lightning, making it "
            "a great time for hiking. Stay hydrated and wear sunscreen!"
        ),
        "trails": [],
    },
}


def _classify_query_simple(query: str) -> str:
    """Simple keyword-based query classification (fallback)."""
    weather_kw = ["weather", "rain", "lightning", "temperature", "storm", "snow", "forecast"]
    q = query.lower()
    for kw in weather_kw:
        if kw in q:
            return "weather"
    return "trail"


async def _ensure_session(session_id, db):
    """Validate or create a session."""
    if session_id:
        session = await db.sessions.find_one({"session_id": session_id})
        if session:
            return session_id
    from backend.app.routes.sessions import create_session
    from backend.app.models.session import SessionCreate
    new_session = await create_session(SessionCreate())
    return new_session.session_id


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """
    Process a user chat query through the live LangGraph pipeline.
    Falls back to mock responses if the AI service is not initialized.
    """
    db = get_db()
    session_id = await _ensure_session(body.session_id, db)

    # Save user message
    await save_message(session_id, "user", body.query)

    # Load conversation history from MongoDB for this session
    chat_history = []
    history_cursor = db.chat_history.find(
        {"session_id": session_id},
        {"_id": 0, "role": 1, "content": 1},
    ).sort("timestamp", 1)
    async for msg in history_cursor:
        chat_history.append({"role": msg["role"], "content": msg["content"]})
    # Exclude the current user message (already saved above) — it's the last one
    if chat_history and chat_history[-1].get("role") == "user":
        chat_history = chat_history[:-1]

    # Try live AI pipeline
    if ai_service._compiled_graph is not None:
        try:
            result = await ai_service.run_query(body.query, chat_history=chat_history, language=body.language or "en")
            trail_refs = ai_service.extract_trail_references(result)
            quality = ai_service.run_quality_checks(result)

            answer = result.get("answer", "")
            route = result.get("route", "trail")

            await save_message(session_id, "assistant", answer)

            return ChatResponse(
                answer=answer,
                route=route,
                trails_referenced=[
                    TrailReference(**ref) for ref in trail_refs
                ],
                weather_context=result.get("weather_context", None),
                session_id=session_id,
                quality_check=quality,
            )
        except Exception as e:
            logger.error(f"LangGraph pipeline error: {e}", exc_info=True)
            # Fall through to mock

    # Fallback: mock responses
    logger.info("Using mock fallback for chat response.")
    route = _classify_query_simple(body.query)
    mock = _MOCK_RESPONSES[route]

    await save_message(session_id, "assistant", mock["answer"])

    return ChatResponse(
        answer=mock["answer"],
        route=route,
        trails_referenced=mock["trails"],
        session_id=session_id,
        quality_check={"status": "mock", "note": "AI service not available; using fallback."},
    )
