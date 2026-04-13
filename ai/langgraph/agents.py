"""
LangGraph agent nodes for TrailBlaze AI.
Each function takes a TrailBlazeState and returns a partial state update.

Robustness features:
  - Exponential backoff retry for all OpenAI API calls
  - Confidence scoring on Router intent classification
  - Structured logging in every agent node
  - Fallback responses when retrieval returns zero results
  - Timeout handling for weather and vector agents
  - Session history context threaded through all nodes
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ai.langgraph.state import TrailBlazeState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0   # seconds; doubled on each retry
_VECTOR_TIMEOUT = 12.0    # seconds before vector retrieval is considered slow
_WEATHER_TIMEOUT = 10.0   # seconds before weather fetch is considered slow

# Intent → confidence boost applied when strong keyword signals are present
_INTENT_CONFIDENCE_MAP = {
    "trail": 0.90,
    "weather": 0.90,
    "both": 0.75,
    "national_park": 0.95,
}

# Strong weather-only keywords that raise confidence
_WEATHER_KEYWORDS = [
    "weather", "rain", "snow", "storm", "lightning", "forecast",
    "temperature", "wind", "conditions today", "safe to hike today",
]

# Strong trail-only keywords
_TRAIL_KEYWORDS = [
    "recommend", "trail", "hike", "route", "path", "loop", "summit",
    "difficulty", "distance", "elevation", "dog friendly", "family",
]


def _build_history_messages(chat_history: list) -> list:
    """Convert chat_history dicts into LangChain message objects."""
    msgs = []
    for msg in (chat_history or [])[-6:]:  # Last 6 messages (3 turns)
        if msg.get("role") == "user":
            msgs.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            msgs.append(AIMessage(content=msg["content"]))
    return msgs


def _get_llm(temperature: float = 0) -> ChatOpenAI:
    """Return a ChatOpenAI instance using env config."""
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=temperature)


def _llm_invoke_with_retry(
    llm: ChatOpenAI,
    messages: list,
    node_name: str,
    max_retries: int = _MAX_RETRIES,
) -> Any:
    """
    Invoke an LLM with exponential backoff retry.
    Raises the last exception if all retries are exhausted.
    """
    delay = _RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.time()
            result = llm.invoke(messages)
            elapsed = time.time() - t0
            logger.debug(
                "[%s] LLM call succeeded on attempt %d (%.2fs)",
                node_name, attempt, elapsed,
            )
            return result
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "[%s] LLM call attempt %d/%d failed: %s — retrying in %.1fs",
                node_name, attempt, max_retries, exc, delay,
            )
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
    raise RuntimeError(
        f"[{node_name}] LLM call failed after {max_retries} attempts: {last_exc}"
    ) from last_exc


def _keyword_confidence(query_lower: str) -> Dict[str, float]:
    """
    Return raw keyword-signal scores for each intent category.
    Each score is the fraction of category keywords found in the query.
    """
    weather_hits = sum(1 for kw in _WEATHER_KEYWORDS if kw in query_lower)
    trail_hits = sum(1 for kw in _TRAIL_KEYWORDS if kw in query_lower)
    total = weather_hits + trail_hits or 1
    return {
        "weather_signal": weather_hits / total,
        "trail_signal": trail_hits / total,
    }


# ---------------------------------------------------------------------------
# Node 1: Router — classifies the query intent with confidence scoring
# ---------------------------------------------------------------------------

# Keywords that trigger national_park intent (case-insensitive)
_NP_KEYWORDS = [
    "rocky mountain national park", "rmnp", "estes park",
    "national park", "bear lake", "trail ridge",
    "longs peak", "hallett peak",
]

# High-confidence weather-only phrases that skip LLM call
_WEATHER_ONLY_PHRASES = [
    "what is the weather", "how is the weather", "weather forecast",
    "is it going to rain", "will it snow", "current weather",
    "temperature today", "weather today",
]

# High-confidence trail-only phrases that skip LLM call
_TRAIL_ONLY_PHRASES = [
    "recommend a trail", "find a trail", "what trail", "suggest a hike",
    "best hike", "hiking trail", "trail recommendation",
]


def router_agent(state: TrailBlazeState) -> Dict[str, Any]:
    """
    Classify the user query to determine routing.
    Uses keyword pre-screening for high-confidence cases, then LLM for ambiguous queries.
    Returns route + confidence score.
    """
    t0 = time.time()
    query = state["user_query"]
    query_lower = query.lower()

    logger.info(
        "[router] Classifying query (session=%s): %r",
        state.get("session_id", "n/a"), query[:120],
    )

    # --- Fast path: national park keywords ---
    for kw in _NP_KEYWORDS:
        if kw in query_lower:
            logger.info("[router] Intent=national_park (keyword match: %r)", kw)
            return {
                "route": "national_park",
                "route_confidence": _INTENT_CONFIDENCE_MAP["national_park"],
                "source_filter": ["NPS"],
                "region_filter": "Rocky Mountains",
                "node_timings": {"router": round(time.time() - t0, 3)},
            }

    # --- Fast path: strong weather-only signal ---
    for phrase in _WEATHER_ONLY_PHRASES:
        if phrase in query_lower:
            logger.info("[router] Intent=weather (phrase match: %r)", phrase)
            return {
                "route": "weather",
                "route_confidence": _INTENT_CONFIDENCE_MAP["weather"],
                "node_timings": {"router": round(time.time() - t0, 3)},
            }

    # --- Fast path: strong trail-only signal ---
    for phrase in _TRAIL_ONLY_PHRASES:
        if phrase in query_lower:
            logger.info("[router] Intent=trail (phrase match: %r)", phrase)
            return {
                "route": "trail",
                "route_confidence": _INTENT_CONFIDENCE_MAP["trail"],
                "node_timings": {"router": round(time.time() - t0, 3)},
            }

    # --- LLM classification for ambiguous queries ---
    llm = _get_llm()
    signals = _keyword_confidence(query_lower)

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
            "- 'trail' if asking about trail recommendations, difficulty, distance, "
            "scenery, dog-friendly hikes, family hikes, or reviews.\n"
            "- 'weather' if asking ONLY about weather, lightning risk, or current conditions.\n"
            "- 'both' if the query involves trail selection AND weather/conditions together.\n"
            "Consider conversation history to understand follow-up questions. "
            "'Make it easier' after a recommendation is still 'trail'. "
            "'Is it safe to hike today given the weather?' is 'both'.\n"
            "Respond with ONLY one word: trail, weather, or both."
        )),
        HumanMessage(content=f"{history_context}Current query: {query}"),
    ]

    route = "both"
    confidence = _INTENT_CONFIDENCE_MAP.get("both", 0.75)
    node_errors: Dict[str, str] = {}

    try:
        response = _llm_invoke_with_retry(llm, messages, "router")
        raw = response.content.strip().lower()
        if raw in ("trail", "weather", "both"):
            route = raw
            # Blend keyword signals with LLM output for final confidence
            if route == "weather":
                confidence = 0.5 + 0.4 * signals["weather_signal"]
            elif route == "trail":
                confidence = 0.5 + 0.4 * signals["trail_signal"]
            else:
                confidence = _INTENT_CONFIDENCE_MAP["both"]
        else:
            logger.warning("[router] LLM returned unexpected route %r — defaulting to 'both'", raw)
    except Exception as exc:
        logger.error("[router] Classification failed: %s — defaulting to 'both'", exc)
        node_errors["router"] = str(exc)

    logger.info(
        "[router] Intent=%s confidence=%.2f (signals=%s)",
        route, confidence, signals,
    )

    return {
        "route": route,
        "route_confidence": round(confidence, 3),
        "node_timings": {"router": round(time.time() - t0, 3)},
        "node_errors": node_errors,
    }


# ---------------------------------------------------------------------------
# Node 2: Vector retrieval agent — searches FAISS for relevant trails
# ---------------------------------------------------------------------------

def vector_agent(state: TrailBlazeState, faiss_index) -> Dict[str, Any]:
    """
    Retrieve trail documents from FAISS and format them as context.
    Uses location-aware filtering when the user mentions a specific Colorado area.
    Passes source_filter/region_filter from state when set by router.
    Logs retrieval outcome and sets retrieval_empty flag for downstream fallback.
    """
    from ai.rag.retriever import retrieve_context, format_context
    from ai.services.geography import resolve_location_managers

    t0 = time.time()
    query = state["user_query"]
    source_filter = state.get("source_filter")
    region_filter = state.get("region_filter")

    logger.info(
        "[vector_agent] Retrieving trails for query: %r (source_filter=%s, region_filter=%s)",
        query[:120], source_filter, region_filter,
    )

    docs: List = []
    node_errors: Dict[str, str] = dict(state.get("node_errors") or {})

    try:
        if source_filter or region_filter:
            docs = retrieve_context(
                faiss_index, query, top_k=3,
                source_filter=source_filter,
                region_filter=region_filter,
            )
        else:
            location_managers = resolve_location_managers(query)
            docs = retrieve_context(
                faiss_index, query, top_k=3,
                location_managers=location_managers if location_managers else None,
            )
    except Exception as exc:
        logger.error("[vector_agent] Retrieval failed: %s", exc)
        node_errors["vector_agent"] = str(exc)

    elapsed = time.time() - t0
    if elapsed > _VECTOR_TIMEOUT:
        logger.warning("[vector_agent] Slow retrieval: %.2fs (threshold=%.1fs)", elapsed, _VECTOR_TIMEOUT)

    retrieval_empty = len(docs) == 0
    if retrieval_empty:
        logger.warning("[vector_agent] No documents retrieved — will use fallback response")
    else:
        trail_names = [d.metadata.get("name", "?") for d in docs]
        logger.info(
            "[vector_agent] Retrieved %d docs in %.2fs: %s",
            len(docs), elapsed, trail_names,
        )

    context = format_context(docs)

    timings = dict(state.get("node_timings") or {})
    timings["vector_agent"] = round(elapsed, 3)

    return {
        "retrieved_docs": docs,
        "trail_context": context,
        "retrieval_empty": retrieval_empty,
        "node_timings": timings,
        "node_errors": node_errors,
    }


# ---------------------------------------------------------------------------
# Node 3: Weather agent — fetches live weather from Open-Meteo API
# ---------------------------------------------------------------------------

def weather_agent(state: TrailBlazeState) -> Dict[str, Any]:
    """
    Fetch live weather data from Open-Meteo API with multi-day forecast.
    Uses the trail's actual location (from retrieved docs) when available,
    otherwise falls back to parsing the user query.
    Includes timeout logging and graceful error handling.
    """
    from ai.services.weather import fetch_weather, fetch_weather_by_coords
    import requests

    t0 = time.time()
    node_errors: Dict[str, str] = dict(state.get("node_errors") or {})

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
                logger.info(
                    "[weather_agent] Fetching weather by coords: (%.4f, %.4f) — %s",
                    lat, lng, location_name,
                )
                try:
                    weather_data = fetch_weather_by_coords(lat, lng, location_name)
                except Exception as exc:
                    logger.warning("[weather_agent] fetch_weather_by_coords failed: %s", exc)
                break

    # Fallback: parse location from user query
    if weather_data is None:
        logger.info("[weather_agent] Falling back to query-based location extraction")
        try:
            weather_data = fetch_weather(state["user_query"])
        except Exception as exc:
            logger.error("[weather_agent] fetch_weather failed: %s", exc)
            node_errors["weather_agent"] = str(exc)
            weather_data = {"error": str(exc), "summary": "Weather data unavailable."}

    elapsed_weather = time.time() - t0
    if elapsed_weather > _WEATHER_TIMEOUT:
        logger.warning(
            "[weather_agent] Slow weather fetch: %.2fs (threshold=%.1fs)",
            elapsed_weather, _WEATHER_TIMEOUT,
        )

    summary = weather_data.get("summary", "Weather data unavailable.")
    logger.info("[weather_agent] Weather summary: %s", summary[:120])

    # Fetch multi-day forecast for richer context (best-effort)
    forecast_text = ""
    if lat and lng and "error" not in weather_data:
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lng,
                    "daily": (
                        "weather_code,temperature_2m_max,temperature_2m_min,"
                        "precipitation_sum,snowfall_sum,wind_speed_10m_max"
                    ),
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
        except Exception as exc:
            logger.warning("[weather_agent] Forecast fetch failed (non-fatal): %s", exc)

    # Build rich weather context for the synthesizer
    if "error" not in weather_data:
        details = [summary]
        if weather_data.get("safety_notes"):
            details.append("Safety alerts: " + " | ".join(weather_data["safety_notes"]))
        if forecast_text:
            details.append(forecast_text)
        weather_context = "\n".join(details)
    else:
        weather_context = summary

    timings = dict(state.get("node_timings") or {})
    timings["weather_agent"] = round(time.time() - t0, 3)

    return {
        "weather_context": weather_context,
        "node_timings": timings,
        "node_errors": node_errors,
    }


# ---------------------------------------------------------------------------
# Node 4: Synthesizer — combines all context into a final answer
# ---------------------------------------------------------------------------

_FALLBACK_RESPONSE_EN = (
    "I'm sorry, I wasn't able to find specific trail information matching your request "
    "in our database. Here are some tips for finding Colorado trails:\n\n"
    "- Try broadening your search (e.g. 'easy hike near Denver' instead of a specific trail name)\n"
    "- Specify a region: Boulder, Colorado Springs, Aspen, Durango, or Glenwood Springs\n"
    "- Specify a difficulty: easy, moderate, or hard\n"
    "- Mention an activity: hiking, biking, or dog-friendly\n\n"
    "I can also tell you about current weather conditions for any Colorado location."
)

_FALLBACK_RESPONSE_ES = (
    "Lo siento, no pude encontrar información específica de senderos que coincida con tu solicitud "
    "en nuestra base de datos. Aquí hay algunos consejos para encontrar senderos en Colorado:\n\n"
    "- Amplía tu búsqueda (por ejemplo, 'senderismo fácil cerca de Denver')\n"
    "- Especifica una región: Boulder, Colorado Springs, Aspen, Durango o Glenwood Springs\n"
    "- Especifica una dificultad: fácil, moderado o difícil\n"
    "- Menciona una actividad: senderismo, ciclismo o apto para perros\n\n"
    "También puedo informarte sobre las condiciones climáticas actuales para cualquier lugar de Colorado."
)


def synthesizer_agent(state: TrailBlazeState) -> Dict[str, Any]:
    """
    Synthesize a final grounded answer from trail and weather context.
    Includes conversation history for multi-turn coherence.
    Uses fallback response when retrieval_empty is True and only weather context is present.
    """
    t0 = time.time()
    llm = _get_llm()
    lang = state.get("language", "en")
    node_errors: Dict[str, str] = dict(state.get("node_errors") or {})

    logger.info(
        "[synthesizer] Generating answer (route=%s, confidence=%.2f, empty=%s, lang=%s)",
        state.get("route"), state.get("route_confidence", 0.0),
        state.get("retrieval_empty", False), lang,
    )

    # --- Fallback: no trails retrieved and query is trail-focused ---
    retrieval_empty = state.get("retrieval_empty", False)
    if retrieval_empty and state.get("route") in ("trail", "national_park"):
        logger.warning("[synthesizer] Using fallback response — no trail results retrieved")
        fallback = _FALLBACK_RESPONSE_ES if lang == "es" else _FALLBACK_RESPONSE_EN
        # If we have weather context, prepend it to the fallback
        if state.get("weather_context"):
            fallback = f"### Weather Conditions\n{state['weather_context']}\n\n{fallback}"
        timings = dict(state.get("node_timings") or {})
        timings["synthesizer"] = round(time.time() - t0, 3)
        return {
            "answer": fallback,
            "node_timings": timings,
            "node_errors": node_errors,
        }

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
            "4. If the retrieved trails don't match what the user asked for, be honest: "
            "'I found these trails in [actual location] — our database may not have trails "
            "in [requested area] yet.'\n"
            "5. WEATHER-AWARE RECOMMENDATIONS (CRITICAL):\n"
            "   - If weather context shows snow, freezing temps (<32°F), active thunderstorms, "
            "or dangerous conditions, you MUST:\n"
            "     a) WARN the user prominently at the top.\n"
            "     b) Advise AGAINST hiking if conditions are severe "
            "(heavy snow, ice, extreme cold below 15°F, active storms).\n"
            "     c) Suggest alternatives with better weather when possible.\n"
            "     d) For moderate conditions (light snow, above 25°F), still recommend "
            "but include specific gear advice (traction devices, layers, etc.).\n"
            "   - Always include a '### Weather Conditions' section when weather data is available.\n"
            "   - Mention specific numbers: temperature, snowfall amounts, wind speeds.\n"
            "6. STRUCTURED OUTPUT FORMAT:\n"
            "   - Use ### headings for each major section.\n"
            "   - Use **bold** for every trail name on first mention.\n"
            "   - Use bullet lists for trail details (distance, elevation, difficulty, dogs, etc.).\n"
            "   - End with a '### Pro Tips' section with 1–3 actionable hiking tips.\n"
            "7. If the user references a previous message ('make it easier', 'tell me more'), "
            "use conversation history to understand the context.\n"
            "8. Keep responses concise and actionable (aim for 200–400 words).\n"
            "9. LANGUAGE: Respond ENTIRELY in the language specified below.\n"
            f"   → Language: {'Spanish (español)' if lang == 'es' else 'English'}\n"
            f"   → Router confidence: {state.get('route_confidence', 'N/A')}"
        )),
    ]

    # Add conversation history for multi-turn coherence
    messages.extend(_build_history_messages(state.get("chat_history", [])))

    # Add current query with context
    messages.append(HumanMessage(content=(
        f"{state['user_query']}\n\n"
        f"Retrieved Context:\n{combined_context}"
    )))

    answer = ""
    try:
        response = _llm_invoke_with_retry(llm, messages, "synthesizer")
        answer = response.content.strip()
        logger.info(
            "[synthesizer] Answer generated (%d chars) in %.2fs",
            len(answer), time.time() - t0,
        )
    except Exception as exc:
        logger.error("[synthesizer] Generation failed: %s", exc)
        node_errors["synthesizer"] = str(exc)
        answer = (
            _FALLBACK_RESPONSE_ES if lang == "es"
            else "I encountered an error generating your trail recommendations. Please try again."
        )

    timings = dict(state.get("node_timings") or {})
    timings["synthesizer"] = round(time.time() - t0, 3)

    return {
        "answer": answer,
        "node_timings": timings,
        "node_errors": node_errors,
    }
