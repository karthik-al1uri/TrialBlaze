"""Session and Chat History API routes."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from backend.app.database import get_db
from backend.app.models.session import (
    SessionCreate,
    SessionResponse,
    ChatHistoryResponse,
    ChatMessage,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(body: SessionCreate = SessionCreate()):
    """Create a new chat session."""
    db = get_db()
    now = datetime.now(timezone.utc)
    session = {
        "session_id": str(uuid.uuid4()),
        "user_id": body.user_id or "anonymous",
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }
    await db.sessions.insert_one(session)
    return SessionResponse(**session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details."""
    db = get_db()
    session = await db.sessions.find_one(
        {"session_id": session_id}, {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**session)


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get all chat messages for a session."""
    db = get_db()

    # Verify session exists
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cursor = db.chat_history.find(
        {"session_id": session_id}, {"_id": 0, "session_id": 0}
    ).sort("timestamp", 1)
    messages = await cursor.to_list(length=1000)

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatMessage(**m) for m in messages],
        total=len(messages),
    )


async def save_message(session_id: str, role: str, content: str):
    """Helper: persist a chat message and update session."""
    db = get_db()
    now = datetime.now(timezone.utc)

    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": now,
    })

    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"updated_at": now}, "$inc": {"message_count": 1}},
    )
