"""
LangGraph orchestration graph for TrailBlaze AI.
Routes user queries through classification, retrieval, weather,
and synthesis agents based on query intent.
"""

from functools import partial

from langgraph.graph import StateGraph, END as LANGGRAPH_END

from ai.langgraph.state import TrailBlazeState
from ai.langgraph.agents import (
    router_agent,
    vector_agent,
    weather_agent,
    synthesizer_agent,
)


def _route_decision(state: TrailBlazeState) -> str:
    """Conditional edge: decide which agents to invoke after routing."""
    route = state.get("route", "both")
    if route == "trail":
        return "vector_agent"
    elif route == "weather":
        return "weather_agent"
    elif route == "national_park":
        return "vector_agent"  # national_park uses vector with NPS filters
    else:
        return "vector_agent"  # "both" starts with vector, then weather


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

    # Conditional routing after classification
    graph.add_conditional_edges(
        "router",
        _route_decision,
        {
            "vector_agent": "vector_agent",
            "weather_agent": "weather_agent",
        },
    )

    # After vector agent: if route is "both", go to weather; otherwise synthesize
    def _after_vector(state: TrailBlazeState) -> str:
        if state.get("route") in ("both", "national_park"):
            return "weather_agent"
        return "synthesizer"

    graph.add_conditional_edges(
        "vector_agent",
        _after_vector,
        {
            "weather_agent": "weather_agent",
            "synthesizer": "synthesizer",
        },
    )

    # After weather agent: always go to synthesizer
    graph.add_edge("weather_agent", "synthesizer")

    # After synthesizer: end
    graph.add_edge("synthesizer", LANGGRAPH_END)

    return graph.compile()
