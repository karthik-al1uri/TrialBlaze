"""
Tests for the LangGraph TrailBlazeState definition.

Verifies that all fields introduced in the state schema can be
instantiated, mutated, and type-checked correctly.
"""

import pytest
from langchain_core.documents import Document

from ai.langgraph.state import TrailBlazeState


def _minimal_state(**overrides) -> TrailBlazeState:
    """Build a minimal valid TrailBlazeState for testing."""
    defaults: TrailBlazeState = {
        "user_query": "Find an easy trail near Boulder",
        "chat_history": [],
        "session_id": None,
        "route": None,
        "route_confidence": None,
        "retrieved_docs": [],
        "trail_context": "",
        "weather_context": "",
        "source_filter": None,
        "region_filter": None,
        "language": "en",
        "answer": "",
        "node_errors": {},
        "retry_counts": {},
        "node_timings": {},
        "retrieval_empty": False,
        "debug_metadata": {},
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Basic instantiation
# ---------------------------------------------------------------------------

def test_state_can_be_instantiated():
    state = _minimal_state()
    assert state["user_query"] == "Find an easy trail near Boulder"
    assert state["route"] is None
    assert state["retrieved_docs"] == []


def test_state_default_language_is_english():
    state = _minimal_state()
    assert state["language"] == "en"


def test_state_with_spanish_language():
    state = _minimal_state(language="es")
    assert state["language"] == "es"


# ---------------------------------------------------------------------------
# New fields from commit 1
# ---------------------------------------------------------------------------

def test_state_session_id_field():
    state = _minimal_state(session_id="sess-abc-123")
    assert state["session_id"] == "sess-abc-123"


def test_state_route_confidence_field():
    state = _minimal_state(route="trail", route_confidence=0.92)
    assert state["route"] == "trail"
    assert state["route_confidence"] == pytest.approx(0.92)


def test_state_node_errors_field():
    state = _minimal_state(node_errors={"router": "timeout", "vector_agent": "index missing"})
    assert state["node_errors"]["router"] == "timeout"
    assert "vector_agent" in state["node_errors"]


def test_state_node_timings_field():
    state = _minimal_state(node_timings={"router": 0.05, "vector_agent": 0.82})
    assert state["node_timings"]["router"] == pytest.approx(0.05)
    assert state["node_timings"]["vector_agent"] == pytest.approx(0.82)


def test_state_retry_counts_field():
    state = _minimal_state(retry_counts={"router": 2})
    assert state["retry_counts"]["router"] == 2


def test_state_retrieval_empty_defaults_false():
    state = _minimal_state()
    assert state["retrieval_empty"] is False


def test_state_retrieval_empty_can_be_true():
    state = _minimal_state(retrieval_empty=True)
    assert state["retrieval_empty"] is True


def test_state_debug_metadata_is_dict():
    state = _minimal_state(debug_metadata={"hyde_used": True, "bm25_used": False})
    assert state["debug_metadata"]["hyde_used"] is True


# ---------------------------------------------------------------------------
# Route values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route", ["trail", "weather", "both", "national_park", None])
def test_state_valid_route_values(route):
    state = _minimal_state(route=route)
    assert state["route"] == route


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

def test_state_chat_history_structure():
    history = [
        {"role": "user", "content": "Find me an easy trail"},
        {"role": "assistant", "content": "I recommend Bear Lake Loop."},
    ]
    state = _minimal_state(chat_history=history)
    assert len(state["chat_history"]) == 2
    assert state["chat_history"][0]["role"] == "user"
    assert state["chat_history"][1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def test_state_source_filter():
    state = _minimal_state(source_filter=["NPS", "USFS"])
    assert "NPS" in state["source_filter"]
    assert "USFS" in state["source_filter"]


def test_state_region_filter():
    state = _minimal_state(region_filter="Front Range")
    assert state["region_filter"] == "Front Range"


# ---------------------------------------------------------------------------
# Retrieved docs
# ---------------------------------------------------------------------------

def test_state_retrieved_docs_with_documents():
    docs = [
        Document(page_content="Trail A info", metadata={"name": "Trail A"}),
        Document(page_content="Trail B info", metadata={"name": "Trail B"}),
    ]
    state = _minimal_state(retrieved_docs=docs)
    assert len(state["retrieved_docs"]) == 2
    assert state["retrieved_docs"][0].metadata["name"] == "Trail A"


def test_state_answer_field():
    state = _minimal_state(answer="I recommend Royal Arch Trail near Boulder.")
    assert "Royal Arch" in state["answer"]
