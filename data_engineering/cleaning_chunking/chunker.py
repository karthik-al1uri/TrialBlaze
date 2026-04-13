"""
Text chunker for trail records.
Converts normalized trail data into embedding-ready text chunks
with traceable source fields for RAG retrieval.
"""

from typing import Dict, Any, List, Optional


def _bool_to_str(val: Optional[bool]) -> str:
    if val is True:
        return "yes"
    if val is False:
        return "no"
    return "unknown"


def trail_to_text(trail: Dict[str, Any]) -> str:
    """
    Convert a normalized trail record into a single text passage
    suitable for embedding in a vector store.
    """
    parts = []

    name = trail.get("name", "Unknown Trail")
    parts.append(f"{name} is a Colorado trail.")

    trail_type = trail.get("trail_type")
    if trail_type:
        parts.append(f"Trail type: {trail_type}.")

    surface = trail.get("surface")
    if surface:
        parts.append(f"Surface: {surface}.")

    difficulty = trail.get("difficulty", "unknown")
    parts.append(f"Difficulty: {difficulty}.")

    length = trail.get("length_miles")
    if length:
        parts.append(f"Length: {length} miles.")

    elev_gain = trail.get("elevation_gain_ft")
    if elev_gain:
        parts.append(f"Elevation gain: {elev_gain} ft.")

    min_elev = trail.get("min_elevation_ft")
    max_elev = trail.get("max_elevation_ft")
    if min_elev and max_elev:
        parts.append(f"Elevation range: {min_elev} ft to {max_elev} ft.")

    hiking = trail.get("hiking")
    if hiking is not None:
        parts.append(f"Hiking: {_bool_to_str(hiking)}.")

    bike = trail.get("bike")
    if bike is not None:
        parts.append(f"Biking: {_bool_to_str(bike)}.")

    horse = trail.get("horse")
    if horse is not None:
        parts.append(f"Horseback riding: {_bool_to_str(horse)}.")

    dogs = trail.get("dogs")
    if dogs:
        parts.append(f"Dogs: {dogs}.")

    manager = trail.get("manager")
    if manager:
        parts.append(f"Managed by: {manager}.")

    # Include reviews if present
    reviews = trail.get("reviews", [])
    if reviews:
        parts.append("User reviews:")
        for review in reviews[:3]:  # Cap at 3 reviews per chunk
            parts.append(f"  - {review}")

    return " ".join(parts)


def create_chunk(trail: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a single embedding-ready chunk from a normalized trail record.

    Returns a dict with:
      - text: The passage for embedding
      - metadata: Structured fields for filtering/display
    """
    text = trail_to_text(trail)

    metadata = {
        "source": trail.get("source", "cotrex"),
        "cotrex_fid": trail.get("cotrex_fid"),
        "feature_id": trail.get("feature_id"),
        "name": trail.get("name"),
        "difficulty": trail.get("difficulty"),
        "length_miles": trail.get("length_miles"),
        "elevation_gain_ft": trail.get("elevation_gain_ft"),
        "surface": trail.get("surface"),
        "manager": trail.get("manager"),
        "hiking": trail.get("hiking"),
        "bike": trail.get("bike"),
        "dogs": trail.get("dogs"),
    }

    return {"text": text, "metadata": metadata}


def chunk_batch(trails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert a batch of normalized trail records into embedding-ready chunks.
    Filters out records that produce very short text (< 30 chars).
    """
    chunks = []
    for trail in trails:
        chunk = create_chunk(trail)
        if len(chunk["text"]) >= 30:
            chunks.append(chunk)
    return chunks
