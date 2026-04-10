"""Tests for the LangGraph state definition."""

from ai.langgraph.state import TrailBlazeState


def test_state_can_be_instantiated():
    state: TrailBlazeState = {
        "user_query": "Find an easy trail",
        "route": None,
        "retrieved_docs": [],
        "trail_context": "",
        "weather_context": "",
        "answer": "",
    }
    assert state["user_query"] == "Find an easy trail"
    assert state["route"] is None
    assert state["retrieved_docs"] == []
