"""
LangGraph orchestration graph for TrailBlaze AI.
Routes user queries through classification, retrieval, weather,
and synthesis agents based on query intent.

Routing logic:
  trail         → vector_agent → synthesizer
  weather       → weather_agent → synthesizer
  both          → vector_agent → weather_agent → synthesizer
  national_park → vector_agent → weather_agent → synthesizer
"""

import logging
from functools import partial

from langgraph.graph import StateGraph, END as LANGGRAPH_END

from ai.langgraph.state import TrailBlazeState
from ai.langgraph.agents import (
    router_agent,
    vector_agent,
    weather_agent,
    synthesizer_agent,
)

logger = logging.getLogger(__name__)


def _route_decision(state: TrailBlazeState) -> str:
    """
    Conditional edge after router: decide which pipeline branch to take.
    Logs the routing decision and confidence for observability.
    """
    route = state.get("route", "both")
    confidence = state.get("route_confidence", 0.0)
    logger.info(
        "[graph] Routing decision: %s (confidence=%.2f)", route, confidence
    )
    if route == "weather":
        return "weather_agent"
    # trail, both, national_park — all start with vector retrieval
    return "vector_agent"


def _after_vector_decision(state: TrailBlazeState) -> str:
    """
    Conditional edge after vector_agent.
    'both' and 'national_park' routes always fetch weather too.
    Pure 'trail' queries skip weather.
    If retrieval was empty on a trail-only query, skip weather and go straight to synthesizer.
    """
    route = state.get("route", "both")
    retrieval_empty = state.get("retrieval_empty", False)

    if route in ("both", "national_park"):
        return "weather_agent"
    if route == "trail" and retrieval_empty:
        # Skip weather fetch — synthesizer will use the fallback response
        logger.info("[graph] Retrieval empty on trail route — skipping weather, going to synthesizer")
        return "synthesizer"
    return "synthesizer"


def build_graph(faiss_index) -> StateGraph:
    """
    Build and compile the TrailBlaze AI LangGraph.

    Args:
        faiss_index: A FAISS vector store instance for trail retrieval.

    Returns:
        A compiled LangGraph ready to invoke.
    """
    graph = StateGraph(TrailBlazeState)

    # Wrap vector_agent with the FAISS index
    bound_vector_agent = partial(vector_agent, faiss_index=faiss_index)

    # Add nodes
    graph.add_node("router", router_agent)
    graph.add_node("vector_agent", bound_vector_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("synthesizer", synthesizer_agent)

    # Set entry point
    graph.set_entry_point("router")

    # Conditional routing after router classification
    graph.add_conditional_edges(
        "router",
        _route_decision,
        {
            "vector_agent": "vector_agent",
            "weather_agent": "weather_agent",
        },
    )

    # After vector agent: route to weather (both/national_park) or synthesizer (trail)
    graph.add_conditional_edges(
        "vector_agent",
        _after_vector_decision,
        {
            "weather_agent": "weather_agent",
            "synthesizer": "synthesizer",
        },
    )

    # After weather agent: always synthesize
    graph.add_edge("weather_agent", "synthesizer")

    # After synthesizer: end of graph
    graph.add_edge("synthesizer", LANGGRAPH_END)

    return graph.compile()
