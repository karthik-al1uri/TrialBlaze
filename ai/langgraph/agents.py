"""
LangGraph agent nodes for TrailBlaze AI.
Each function takes a TrailBlazeState and returns a partial state update.
"""

import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ai.langgraph.state import TrailBlazeState


def _build_history_messages(chat_history: list) -> list:
    """Convert chat_history dicts into LangChain message objects."""
    msgs = []
    for msg in (chat_history or [])[-6:]:  # Last 6 messages (3 turns)
        if msg.get("role") == "user":
            msgs.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            msgs.append(AIMessage(content=msg["content"]))
    return msgs


def _get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI instance using env config."""
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0)


# ---------------------------------------------------------------------------
# Node 1: Router — classifies the query intent
# ---------------------------------------------------------------------------

# Keywords that trigger national_park intent (case-insensitive)
_NP_KEYWORDS = [
    "rocky mountain national park", "rmnp", "estes park",
    "national park", "bear lake", "trail ridge",
    "longs peak", "hallett peak",
]


def router_agent(state: TrailBlazeState) -> Dict[str, Any]:
    """
    Classify the user query to determine routing.
    Uses conversation history for context on follow-up queries.
    Returns route: 'trail', 'weather', 'both', or 'national_park'.
    """
    query_lower = state["user_query"].lower()

    # Check for national park keywords BEFORE LLM call
    for kw in _NP_KEYWORDS:
        if kw in query_lower:
            return {
                "route": "national_park",
                "source_filter": ["NPS"],
                "region_filter": "Rocky Mountains",
            }

    llm = _get_llm()

    history_context = ""
    if state.get("chat_history"):
        recent = state["chat_history"][-4:]  # Last 2 turns
        history_context = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}" for m in recent
        )
        history_context = f"\n\nRecent conversation:\n{history_context}\n"

    messages = [
        SystemMessage(content=(
            "You are a query classifier for a Colorado trail assistant. "
            "Classify the user query into exactly one category:\n"
            "- 'trail' if the user is asking about trail recommendations, difficulty, distance, scenery, or reviews.\n"
            "- 'weather' if the user is asking only about weather, lightning risk, or conditions.\n"
            "- 'both' if the query involves trail selection AND weather/conditions.\n"
            "Consider the conversation history to understand follow-up questions. "
            "For example, 'make it easier' after a trail recommendation is still a 'trail' query.\n"
            "Respond with ONLY one word: trail, weather, or both."
        )),
        HumanMessage(content=f"{history_context}Current query: {state['user_query']}"),
    ]
    response = llm.invoke(messages)
    route = response.content.strip().lower()

    if route not in ("trail", "weather", "both"):
        route = "both"

    return {"route": route}


# ---------------------------------------------------------------------------
# Node 2: Vector retrieval agent — searches FAISS for relevant trails
# ---------------------------------------------------------------------------

def vector_agent(state: TrailBlazeState, faiss_index) -> Dict[str, Any]:
    """
    Retrieve trail documents from FAISS and format them as context.
    Uses location-aware filtering when the user mentions a specific Colorado area.
    Passes source_filter/region_filter from state when set by router.
    """
    from ai.rag.retriever import retrieve_context, format_context
    from ai.services.geography import resolve_location_managers

    source_filter = state.get("source_filter")
    region_filter = state.get("region_filter")

    # If router set explicit filters (e.g. national_park), use those
    if source_filter or region_filter:
        docs = retrieve_context(
            faiss_index, state["user_query"], top_k=3,
            source_filter=source_filter,
            region_filter=region_filter,
        )
    else:
        # Existing location_managers path
        location_managers = resolve_location_managers(state["user_query"])
        docs = retrieve_context(
            faiss_index, state["user_query"], top_k=3,
            location_managers=location_managers if location_managers else None,
        )
    context = format_context(docs)
    return {"retrieved_docs": docs, "trail_context": context}


# ---------------------------------------------------------------------------
# Node 3: Weather agent — fetches live weather from Open-Meteo API
# ---------------------------------------------------------------------------

def weather_agent(state: TrailBlazeState) -> Dict[str, Any]:
    """
    Fetch live weather data from Open-Meteo API with multi-day forecast.
    Uses the trail's actual location (from retrieved docs) when available,
    otherwise falls back to parsing the user query.
    """
    from ai.services.weather import fetch_weather, fetch_weather_by_coords
    import requests

    # Try to get location from retrieved trail docs first
    weather_data = None
    location_name = "Central Colorado"
    lat, lng = None, None
    docs = state.get("retrieved_docs", [])
    if docs:
        for doc in docs:
            lat = doc.metadata.get("lat")
            lng = doc.metadata.get("lng")
            city = doc.metadata.get("nearby_city", "")
            if lat and lng:
                location_name = city or "trail area"
                weather_data = fetch_weather_by_coords(lat, lng, location_name)
                break

    # Fallback: parse location from user query
    if weather_data is None:
        weather_data = fetch_weather(state["user_query"])

    summary = weather_data.get("summary", "Weather data unavailable.")

    # Fetch multi-day forecast for richer context
    forecast_text = ""
    if lat and lng and "error" not in weather_data:
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lng,
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_10m_max",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "precipitation_unit": "inch",
                    "forecast_days": 4,
                    "timezone": "America/Denver",
                },
                timeout=8,
            )
            if resp.ok:
                daily = resp.json().get("daily", {})
                dates = daily.get("time", [])
                from ai.services.weather import WMO_CODES
                lines = [f"\n4-Day Forecast for {location_name}:"]
                for i, date in enumerate(dates):
                    wc = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
                    hi = daily.get("temperature_2m_max", [0])[i] if i < len(daily.get("temperature_2m_max", [])) else 0
                    lo = daily.get("temperature_2m_min", [0])[i] if i < len(daily.get("temperature_2m_min", [])) else 0
                    snow = daily.get("snowfall_sum", [0])[i] if i < len(daily.get("snowfall_sum", [])) else 0
                    precip = daily.get("precipitation_sum", [0])[i] if i < len(daily.get("precipitation_sum", [])) else 0
                    wind = daily.get("wind_speed_10m_max", [0])[i] if i < len(daily.get("wind_speed_10m_max", [])) else 0
                    desc = WMO_CODES.get(wc, "Unknown")
                    line = f"  {date}: {desc}, High {hi:.0f}°F / Low {lo:.0f}°F, Wind {wind:.0f}mph"
                    if snow > 0:
                        line += f", Snow {snow:.1f}\""
                    if precip > 0:
                        line += f", Precip {precip:.2f}\""
                    lines.append(line)
                forecast_text = "\n".join(lines)
        except Exception:
            pass

    # Build rich weather context for the synthesizer
    if "error" not in weather_data:
        details = [summary]
        if weather_data.get("safety_notes"):
            details.append("Safety alerts: " + " | ".join(weather_data["safety_notes"]))
        if forecast_text:
            details.append(forecast_text)
        return {"weather_context": "\n".join(details)}

    return {"weather_context": summary}


# ---------------------------------------------------------------------------
# Node 4: Synthesizer — combines all context into a final answer
# ---------------------------------------------------------------------------

def synthesizer_agent(state: TrailBlazeState) -> Dict[str, Any]:
    """
    Synthesize a final grounded answer from trail and weather context.
    Includes conversation history for multi-turn coherence.
    """
    llm = _get_llm()

    context_parts = []
    if state.get("trail_context"):
        context_parts.append(f"TRAIL INFORMATION:\n{state['trail_context']}")
    if state.get("weather_context"):
        context_parts.append(f"WEATHER CONTEXT:\n{state['weather_context']}")

    combined_context = "\n\n".join(context_parts) if context_parts else "No context available."

    messages = [
        SystemMessage(content=(
            "You are TrailBlaze AI, an intelligent Colorado trail planning assistant.\n\n"
            "STRICT RULES:\n"
            "1. ONLY recommend trails that appear in the 'Retrieved Context' below. "
            "Never invent trail names, locations, or details.\n"
            "2. Use the EXACT trail name, distance, difficulty, elevation, and location "
            "from the context. Do not change or embellish these facts.\n"
            "3. The 'Location' field in the context tells you WHERE the trail actually is. "
            "Use that — do NOT assume a trail is in a different area.\n"
            "4. If the retrieved trails don't match what the user asked for (e.g. they asked "
            "for Rocky Mountain National Park but the trails are elsewhere), be honest: "
            "'I found these trails in [actual location] — our database may not have trails "
            "in [requested area] yet.'\n"
            "5. WEATHER-AWARE RECOMMENDATIONS (CRITICAL):\n"
            "   - If weather context shows snow, freezing temperatures (<32°F), "
            "active thunderstorms, or dangerous conditions in an area, you MUST:\n"
            "     a) WARN the user about the hazardous conditions prominently at the top.\n"
            "     b) Explicitly advise AGAINST hiking trails in that area if conditions are severe "
            "(heavy snow, ice, extreme cold below 15°F, active storms).\n"
            "     c) Suggest alternative trails in areas with better weather if possible.\n"
            "     d) If conditions are moderate (light snow, cold but above 25°F), still recommend "
            "but include gear advice (traction devices, layers, etc.).\n"
            "   - Always include a '### Weather Conditions' section when weather data is available.\n"
            "   - Mention specific numbers: temperature, snowfall amounts, wind speeds.\n"
            "6. If the user references a previous message ('make it easier', 'tell me more'), "
            "use conversation history to understand what they mean.\n"
            "7. Format your response with markdown: use **bold** for trail names, bullet lists "
            "for details, and ### headings for sections.\n"
            "8. Keep responses concise and actionable.\n"
            "9. LANGUAGE: You MUST respond in the language specified below. "
            "If Spanish ('es'), write your ENTIRE response in Spanish. "
            "If English ('en'), respond in English.\n"
            f"   → Respond in: {'Spanish (español)' if state.get('language') == 'es' else 'English'}"
        )),
    ]

    # Add conversation history as messages for natural multi-turn flow
    messages.extend(_build_history_messages(state.get("chat_history", [])))

    # Add current query with context
    messages.append(HumanMessage(content=(
        f"{state['user_query']}\n\n"
        f"Retrieved Context:\n{combined_context}"
    )))

    response = llm.invoke(messages)
    return {"answer": response.content.strip()}
