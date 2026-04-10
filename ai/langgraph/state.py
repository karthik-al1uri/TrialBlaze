"""
Shared state definition for the TrailBlaze AI LangGraph execution.
All agents read from and write to this typed state dict.
"""

from typing import TypedDict, List, Optional, Dict

from langchain_core.documents import Document


class TrailBlazeState(TypedDict):
    """State passed through the LangGraph nodes."""

    # User's original natural-language query
    user_query: str

    # Conversation history: list of {"role": "user"|"assistant", "content": str}
    chat_history: List[Dict[str, str]]

    # Routing decision: which agents should handle the query
    route: Optional[str]  # "trail", "weather", "both"

    # Retrieved trail documents from FAISS
    retrieved_docs: List[Document]

    # Formatted context string built from retrieved docs
    trail_context: str

    # Weather context from Open-Meteo API
    weather_context: str

    # Optional filters for source/region-scoped retrieval
    source_filter: Optional[List[str]]
    region_filter: Optional[str]

    # Response language: "en" or "es"
    language: str

    # Final synthesized answer
    answer: str
