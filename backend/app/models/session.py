"""
Session and Chat History Pydantic models.
Maps to the 'sessions' and 'chat_history' MongoDB collections.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """A single chat message in a conversation."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionCreate(BaseModel):
    """Request body to create a new session."""
    user_id: Optional[str] = "anonymous"


class SessionResponse(BaseModel):
    """Session record returned by the API."""
    session_id: str
    user_id: str = "anonymous"
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    session_id: str
    messages: List[ChatMessage]
    total: int
