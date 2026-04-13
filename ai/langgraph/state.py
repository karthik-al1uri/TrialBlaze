"""
Shared state definition for the TrailBlaze AI LangGraph execution.
All agents read from and write to this typed state dict.
"""

from typing import TypedDict, List, Optional, Dict, Any

from langchain_core.documents import Document


class TrailBlazeState(TypedDict):
    """State passed through the LangGraph nodes."""

    # User's original natural-language query
    user_query: str

    # Conversation history: list of {"role": "user"|"assistant", "content": str}
    chat_history: List[Dict[str, str]]

    # Session identifier for multi-turn tracking
    session_id: Optional[str]

    # Routing decision: which agents should handle the query
    route: Optional[str]  # "trail", "weather", "both", "national_park"

    # Router confidence score (0.0 - 1.0) — how certain the router is
    route_confidence: Optional[float]

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

    # Per-node error tracking: {"node_name": "error message"}
    node_errors: Dict[str, str]

    # Retry attempt counters per node
    retry_counts: Dict[str, int]

    # Timing metadata: {"node_name": elapsed_seconds}
    node_timings: Dict[str, float]

    # Whether retrieval returned zero results (triggers fallback path)
    retrieval_empty: bool

    # Additional debug metadata for quality checks
    debug_metadata: Dict[str, Any]
