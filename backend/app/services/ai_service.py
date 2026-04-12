"""
AI Service — connects the backend to the LangGraph pipeline.
Loads a pre-built FAISS index from disk and runs queries
through the full LangGraph orchestration (router → retriever → weather → synthesizer).
"""

import os
import logging
import pickle
from typing import Dict, Any, Optional, List

import faiss
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from ai.langgraph.graph import build_graph
from ai.quality_checks.rag_quality import run_all_checks
from backend.app.database import get_db
from backend.app.config import settings

logger = logging.getLogger(__name__)
logger.info("AI service called for narration")
# Module-level singletons (initialized at startup)
_faiss_index: Optional[FAISS] = None
_compiled_graph = None

INDEX_PATH = "ai/vector-store/index.faiss"
PKL_PATH   = "ai/vector-store/index.pkl"


def _get_embeddings() -> OpenAIEmbeddings:
    """Return OpenAI embeddings instance."""
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    return OpenAIEmbeddings(model=model)


def load_faiss_index():
    """Load existing FAISS index from disk. Never rebuild automatically."""
    if os.path.exists(INDEX_PATH) and os.path.exists(PKL_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(PKL_PATH, "rb") as f:
            metadata = pickle.load(f)
        print(f"FAISS index loaded: {index.ntotal} vectors")
        return index, metadata
    else:
        print("WARNING: FAISS index not found.")
        print("Run: python -m ai.rag.rebuild_index")
        return None, []


# Call this ONCE at module load — never rebuild automatically
faiss_index, trail_metadata = load_faiss_index()


def _trail_to_text(trail: Dict[str, Any]) -> str:
    """Convert a MongoDB trail document into embedding text with geographic region."""
    from ai.services.geography import get_region_text

    parts = []
    name = trail.get("name", "Unknown Trail")
    manager = trail.get("manager", "")
    region_text = get_region_text(manager)
    parts.append(f"{name} is a Colorado trail. {region_text}")

    if trail.get("trail_type"):
        parts.append(f"Trail type: {trail['trail_type']}.")
    if trail.get("surface"):
        parts.append(f"Surface: {trail['surface']}.")

    difficulty = trail.get("difficulty", "unknown")
    parts.append(f"Difficulty: {difficulty}.")

    if trail.get("length_miles"):
        parts.append(f"Length: {trail['length_miles']} miles.")
    if trail.get("elevation_gain_ft"):
        parts.append(f"Elevation gain: {trail['elevation_gain_ft']} ft.")
    if trail.get("min_elevation_ft") and trail.get("max_elevation_ft"):
        parts.append(f"Elevation range: {trail['min_elevation_ft']} ft to {trail['max_elevation_ft']} ft.")

    if trail.get("hiking") is not None:
        parts.append(f"Hiking: {'yes' if trail['hiking'] else 'no'}.")
    if trail.get("bike") is not None:
        parts.append(f"Biking: {'yes' if trail['bike'] else 'no'}.")
    if trail.get("dogs"):
        parts.append(f"Dogs: {trail['dogs']}.")
    if manager:
        parts.append(f"Managed by: {manager}.")

    reviews = trail.get("reviews", [])
    if reviews:
        parts.append("User reviews:")
        for r in reviews[:3]:
            if isinstance(r, dict):
                parts.append(f"  - {r.get('text', '')}")
            else:
                parts.append(f"  - {r}")

    return " ".join(parts)


def _trail_to_document(trail: Dict[str, Any]) -> Document:
    """Convert a MongoDB trail dict to a LangChain Document."""
    from ai.services.geography import get_region_for_manager

    text = _trail_to_text(trail)
    manager = trail.get("manager", "")
    region = get_region_for_manager(manager)
    metadata = {
        "name": trail.get("name", "Unknown"),
        "location": region[0] if region else trail.get("region") or trail.get("manager", "Colorado"),
        "nearby_city": region[1] if region else "",
        "lat": region[2] if region else None,
        "lng": region[3] if region else None,
        "difficulty": trail.get("difficulty", "unknown"),
        "distance_miles": trail.get("length_miles"),
        "elevation_gain_ft": trail.get("elevation_gain_ft"),
        "cotrex_fid": trail.get("cotrex_fid"),
        "hiking": trail.get("hiking"),
        "bike": trail.get("bike"),
        "dogs": trail.get("dogs"),
        "manager": manager,
        "source": trail.get("source"),
        "region": trail.get("region"),
    }
    return Document(page_content=text, metadata=metadata)


async def initialize_ai():
    """
    Load pre-built FAISS index from disk and compile LangGraph.
    Called once at application startup.
    """
    global _faiss_index, _compiled_graph

    # Load pre-built FAISS index from disk — never rebuild automatically
    faiss_dir = "ai/vector-store"
    if os.path.exists(os.path.join(faiss_dir, "index.faiss")):
        embeddings = _get_embeddings()
        _faiss_index = FAISS.load_local(
            faiss_dir, embeddings, allow_dangerous_deserialization=True
        )
        logger.info(f"FAISS index loaded from {faiss_dir}")
    else:
        logger.warning("FAISS index files not found. Run: python -m ai.rag.rebuild_index")

    logger.info("Compiling LangGraph...")
    _compiled_graph = build_graph(_faiss_index)
    logger.info("LangGraph compiled. AI service ready.")


async def run_query(
    user_query: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """
    Run a user query through the full LangGraph pipeline.
    Returns the result state dict with answer, route, retrieved_docs, etc.
    Runs the synchronous LangGraph invoke in a thread to avoid blocking the event loop.
    """
    import asyncio

    if _compiled_graph is None:
        raise RuntimeError("AI service not initialized. Call initialize_ai() first.")

    initial_state = {
        "user_query": user_query,
        "chat_history": chat_history or [],
        "route": None,
        "retrieved_docs": [],
        "trail_context": "",
        "weather_context": "",
        "source_filter": None,
        "region_filter": None,
        "answer": "",
        "language": language,
    }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _compiled_graph.invoke, initial_state)
    return result


def extract_trail_references(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract trail references from LangGraph result for the API response."""
    refs = []
    for doc in result.get("retrieved_docs", []):
        meta = doc.metadata
        refs.append({
            "name": meta.get("name", "Unknown"),
            "difficulty": meta.get("difficulty"),
            "length_miles": meta.get("distance_miles"),
            "location": meta.get("location", ""),
            "nearby_city": meta.get("nearby_city", ""),
        })
    return refs


def run_quality_checks(result: Dict[str, Any]) -> Dict[str, Any]:
    """Run RAG quality checks on the pipeline output."""
    try:
        return run_all_checks(
            query=result.get("user_query", ""),
            documents=result.get("retrieved_docs", []),
            trail_context=result.get("trail_context", ""),
            answer=result.get("answer", ""),
        )
    except Exception as e:
        logger.warning(f"Quality check failed: {e}")
        return {"overall_passed": False, "error": str(e)}
