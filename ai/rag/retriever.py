"""
RAG retriever module.
Wraps FAISS similarity search and formats retrieved context for LLM consumption.
Supports location-aware filtering when user mentions specific Colorado areas.
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS


def retrieve_context(
    faiss_index: FAISS,
    query: str,
    top_k: int = 3,
    location_managers: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    region_filter: Optional[str] = None,
) -> List[Document]:
    """
    Retrieve top-k trail documents relevant to the user query.
    If location_managers is provided, fetch extra candidates and filter
    to prioritize trails from those managers.
    If source_filter/region_filter provided, pre-filter FAISS candidates
    to only matching docs before ranking.
    """
    # --- source/region pre-filtering path ---
    if source_filter or region_filter:
        pool_size = min(top_k * 40, 300)
        candidates = faiss_index.similarity_search(query, k=pool_size)
        filtered = []
        for d in candidates:
            if source_filter and d.metadata.get("source") not in source_filter:
                continue
            if region_filter and d.metadata.get("region") != region_filter:
                continue
            filtered.append(d)
        if len(filtered) >= top_k:
            return filtered[:top_k]
        # Fallback: if filters reduce to 0, return unfiltered + note
        if not filtered:
            fallback = faiss_index.similarity_search(query, k=top_k)
            if fallback:
                fallback[0].page_content = (
                    "[Note: No trails found matching filters — showing general results]\n"
                    + fallback[0].page_content
                )
            return fallback
        # Partial match — return what we have
        return filtered[:top_k]

    # --- location_managers path (existing behavior, unchanged) ---
    if location_managers:
        from ai.services.geography import MANAGER_REGIONS, LOCATION_ALIASES
        import re

        # Step 1: Strip the location keyword from the query to avoid
        # FAISS matching trail names like "Rocky Gulch" for "Rocky Mountains"
        activity_query = query
        for keyword in sorted(LOCATION_ALIASES.keys(), key=len, reverse=True):
            activity_query = re.sub(
                re.escape(keyword), "", activity_query, flags=re.IGNORECASE
            ).strip()
        if len(activity_query) < 10:
            activity_query = "good hiking trail moderate"

        # Step 2: Build region-focused search queries
        region_descs = []
        for m in location_managers:
            r = MANAGER_REGIONS.get(m)
            if r:
                region_descs.append(f"near {r[1]}")
        region_suffix = " ".join(region_descs[:3])
        region_query = f"{activity_query} {region_suffix}"

        # Step 3: Search with region-enriched query, large pool, filter by manager
        candidates = faiss_index.similarity_search(region_query, k=min(top_k * 30, 200))
        matched = [d for d in candidates if d.metadata.get("manager") in location_managers]
        if len(matched) >= top_k:
            return matched[:top_k]

        # Step 4: Also try activity-only query with filtering
        candidates2 = faiss_index.similarity_search(activity_query, k=min(top_k * 30, 200))
        for d in candidates2:
            if d.metadata.get("manager") in location_managers:
                if not any(m.metadata.get("name") == d.metadata.get("name") for m in matched):
                    matched.append(d)
        if len(matched) >= top_k:
            return matched[:top_k]

        # Step 5: If still not enough, fill with best activity matches
        if matched:
            remaining = top_k - len(matched)
            others = [d for d in candidates2 if d.metadata.get("name") not in
                       {m.metadata.get("name") for m in matched}]
            matched.extend(others[:remaining])
            return matched[:top_k]

        return candidates2[:top_k]

    return faiss_index.similarity_search(query, k=top_k)


def format_context(documents: List[Document]) -> str:
    """
    Format retrieved documents into a single context string
    suitable for injection into an LLM prompt.
    """
    if not documents:
        return "No relevant trail information found."

    sections = []
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata
        header = f"Trail {i}: {meta.get('name', 'Unknown')}"
        # Source / Manager / Region — only include if non-null
        source_line = ""
        src = meta.get("source")
        mgr = meta.get("manager")
        rgn = meta.get("region")
        parts = []
        if src:
            parts.append(f"Source: {src}")
        if mgr:
            parts.append(f"Manager: {mgr}")
        if rgn:
            parts.append(f"Region: {rgn}")
        if parts:
            source_line = "  " + " | ".join(parts)
        location = f"  Location: {meta.get('location', 'N/A')}"
        nearby = meta.get("nearby_city")
        if nearby:
            location += f" (near {nearby})"
        difficulty = f"  Difficulty: {meta.get('difficulty', 'N/A')}"
        distance = f"  Distance: {meta.get('distance_miles', 'N/A')} miles"
        elevation = f"  Elevation Gain: {meta.get('elevation_gain_ft', 'N/A')} ft"
        detail = f"  Details: {doc.page_content}"
        lines = [header]
        if source_line:
            lines.append(source_line)
        lines.extend([location, difficulty, distance, elevation, detail])
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
