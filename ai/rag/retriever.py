"""
RAG retriever module for TrailBlaze AI.

Retrieval pipeline:
  1. FAISS dense vector search (OpenAI embeddings)
  2. BM25 keyword search (rank_bm25, optional)
  3. RRF (Reciprocal Rank Fusion) to merge dense + sparse rankings
  4. Cross-encoder reranking (sentence-transformers, optional)
  5. Metadata filtering: difficulty, length, source, region
  6. Result deduplication by trail name
  7. HyDE: generate a hypothetical ideal document to improve query embeddings

Fallbacks: if optional libraries are unavailable the module degrades
gracefully to pure FAISS similarity search.
"""

import hashlib
import logging
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional library guards
# ---------------------------------------------------------------------------
try:
    from rank_bm25 import BM25Okapi
    _HAS_BM25 = True
except ImportError:
    _HAS_BM25 = False
    logger.debug("rank_bm25 not installed — BM25 search disabled")

try:
    from sentence_transformers import CrossEncoder
    _HAS_RERANKER = True
except ImportError:
    _HAS_RERANKER = False
    logger.debug("sentence-transformers not installed — reranking disabled")

# ---------------------------------------------------------------------------
# Module-level singletons (loaded once per process)
# ---------------------------------------------------------------------------
_reranker_model: Optional[Any] = None
_reranker_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# In-memory cache for frequent queries: key → (timestamp, List[Document])
_QUERY_CACHE: Dict[str, Tuple[float, List[Document]]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_reranker():
    """Lazy-load the cross-encoder reranker singleton."""
    global _reranker_model
    if _reranker_model is None and _HAS_RERANKER:
        try:
            _reranker_model = CrossEncoder(_reranker_model_name)
            logger.info("Cross-encoder reranker loaded: %s", _reranker_model_name)
        except Exception as exc:
            logger.warning("Failed to load reranker: %s — reranking disabled", exc)
    return _reranker_model


def _cache_key(query: str, top_k: int, source_filter: Any, region_filter: Any,
               difficulty_filter: Any, max_length_miles: Any) -> str:
    """Build a deterministic cache key from retrieval parameters."""
    raw = f"{query}|{top_k}|{source_filter}|{region_filter}|{difficulty_filter}|{max_length_miles}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str) -> Optional[List[Document]]:
    """Return cached results if still fresh, else None."""
    entry = _QUERY_CACHE.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL_SECONDS:
        logger.debug("Cache hit for query key %s", key[:8])
        return entry[1]
    return None


def _set_cached(key: str, docs: List[Document]) -> None:
    """Store retrieval results in the in-memory cache."""
    _QUERY_CACHE[key] = (time.time(), docs)
    # Evict entries older than TTL to keep memory bounded
    now = time.time()
    stale_keys = [k for k, (ts, _) in _QUERY_CACHE.items() if now - ts > _CACHE_TTL_SECONDS]
    for k in stale_keys:
        del _QUERY_CACHE[k]


# ---------------------------------------------------------------------------
# HyDE: Hypothetical Document Embedding
# ---------------------------------------------------------------------------

def generate_hyde_query(query: str) -> str:
    """
    Generate a hypothetical ideal trail description that would perfectly answer
    the user's query. This synthetic document is then embedded and used for
    FAISS retrieval instead of the raw query, improving semantic alignment.

    Falls back to the original query if the LLM call fails.
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model, temperature=0.3)

        messages = [
            SystemMessage(content=(
                "You are a Colorado trail database. Given a user's trail question, "
                "write a single short paragraph (50-80 words) describing an ideal Colorado "
                "trail that would perfectly answer their question. Include: trail name, "
                "location in Colorado, difficulty, distance in miles, elevation gain in feet, "
                "key features (lakes, summit, canyon, etc.), and whether dogs are allowed. "
                "Write as if you are a factual trail description, not answering a question."
            )),
            HumanMessage(content=f"User question: {query}"),
        ]
        response = llm.invoke(messages)
        hypothetical = response.content.strip()
        logger.debug("[HyDE] Generated hypothetical doc (%d chars)", len(hypothetical))
        return hypothetical
    except Exception as exc:
        logger.warning("[HyDE] Generation failed: %s — using original query", exc)
        return query


# ---------------------------------------------------------------------------
# BM25 index building
# ---------------------------------------------------------------------------

def build_bm25_index(documents: List[Document]) -> Any:
    """
    Build a BM25 keyword index from a list of LangChain Documents.
    Returns None if rank_bm25 is not installed.
    """
    if not _HAS_BM25:
        return None
    tokenized_corpus = [
        doc.page_content.lower().split() for doc in documents
    ]
    return BM25Okapi(tokenized_corpus)


def bm25_search(
    bm25_index: Any,
    documents: List[Document],
    query: str,
    top_k: int,
) -> List[Tuple[int, float]]:
    """
    Run BM25 keyword search over documents.
    Returns list of (doc_index, score) sorted descending by score.
    """
    if bm25_index is None or not _HAS_BM25:
        return []
    tokens = query.lower().split()
    scores = bm25_index.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


# ---------------------------------------------------------------------------
# RRF: Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    ranked_lists: List[List[int]],
    k: int = 60,
) -> List[Tuple[int, float]]:
    """
    Merge multiple ranked lists of document indices using Reciprocal Rank Fusion.

    RRF score for doc d = sum(1 / (k + rank_i(d))) over all lists i.
    Higher score = better combined ranking.

    Args:
        ranked_lists: Each inner list is a sequence of doc indices from best to worst.
        k: RRF constant (default 60 is standard).

    Returns:
        List of (doc_index, rrf_score) sorted descending.
    """
    scores: Dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, doc_idx in enumerate(ranked, start=1):
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# Cross-encoder reranking
# ---------------------------------------------------------------------------

def rerank_documents(
    query: str,
    documents: List[Document],
    top_k: int,
) -> List[Document]:
    """
    Rerank documents using a cross-encoder model that scores (query, doc) pairs.
    Falls back to original order if reranker is unavailable.
    """
    if not documents:
        return documents

    reranker = _get_reranker()
    if reranker is None:
        return documents[:top_k]

    try:
        pairs = [(query, doc.page_content[:512]) for doc in documents]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        reranked = [doc for _, doc in ranked[:top_k]]
        logger.debug(
            "[reranker] Reranked %d → %d docs. Top score: %.3f",
            len(documents), len(reranked), max(scores),
        )
        return reranked
    except Exception as exc:
        logger.warning("[reranker] Reranking failed: %s — using original order", exc)
        return documents[:top_k]


# ---------------------------------------------------------------------------
# Metadata filtering helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_NORMALIZE = {
    "easy": "easy", "beginner": "easy", "low": "easy",
    "moderate": "moderate", "medium": "moderate", "intermediate": "moderate",
    "hard": "hard", "difficult": "hard", "strenuous": "hard", "advanced": "hard",
}


def _matches_difficulty(doc: Document, difficulty_filter: Optional[str]) -> bool:
    """Return True if doc difficulty matches the normalized filter value."""
    if difficulty_filter is None:
        return True
    raw = (doc.metadata.get("difficulty") or "").lower().strip()
    normalized = _DIFFICULTY_NORMALIZE.get(raw, raw)
    target = _DIFFICULTY_NORMALIZE.get(difficulty_filter.lower(), difficulty_filter.lower())
    return normalized == target


def _matches_length(doc: Document, max_length_miles: Optional[float]) -> bool:
    """Return True if doc distance is within the max_length_miles limit."""
    if max_length_miles is None:
        return True
    dist = doc.metadata.get("distance_miles")
    if dist is None:
        return True
    try:
        return float(dist) <= max_length_miles
    except (TypeError, ValueError):
        return True


def _apply_metadata_filters(
    documents: List[Document],
    source_filter: Optional[List[str]],
    region_filter: Optional[str],
    difficulty_filter: Optional[str],
    max_length_miles: Optional[float],
) -> List[Document]:
    """Apply all metadata filters to a list of documents."""
    filtered = []
    for doc in documents:
        if source_filter and doc.metadata.get("source") not in source_filter:
            continue
        if region_filter and doc.metadata.get("region") != region_filter:
            continue
        if not _matches_difficulty(doc, difficulty_filter):
            continue
        if not _matches_length(doc, max_length_miles):
            continue
        filtered.append(doc)
    return filtered


def deduplicate_by_name(documents: List[Document]) -> List[Document]:
    """Remove duplicate trail entries keeping the first occurrence of each name."""
    seen_names = set()
    unique = []
    for doc in documents:
        name = (doc.metadata.get("name") or "").strip().lower()
        if name and name in seen_names:
            continue
        seen_names.add(name)
        unique.append(doc)
    return unique


# ---------------------------------------------------------------------------
# Main retrieval function
# ---------------------------------------------------------------------------

def retrieve_context(
    faiss_index: FAISS,
    query: str,
    top_k: int = 3,
    location_managers: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    region_filter: Optional[str] = None,
    difficulty_filter: Optional[str] = None,
    max_length_miles: Optional[float] = None,
    use_hyde: bool = False,
    use_bm25: bool = False,
    use_reranker: bool = False,
    bm25_index: Optional[Any] = None,
    bm25_corpus: Optional[List[Document]] = None,
) -> List[Document]:
    """
    Retrieve top-k trail documents relevant to the user query.

    Pipeline (in order):
      1. Optional HyDE: replace raw query with a hypothetical document embedding
      2. FAISS dense retrieval with large candidate pool
      3. Optional BM25 keyword retrieval + RRF fusion
      4. Metadata filtering (source, region, difficulty, length)
      5. Location manager filtering (USFS/BLM/City)
      6. Optional cross-encoder reranking
      7. Deduplication by trail name
      8. Return top_k results

    Results are cached by query fingerprint for 5 minutes.
    """
    t0 = time.time()

    # --- Cache lookup ---
    cache_key = _cache_key(query, top_k, source_filter, region_filter,
                           difficulty_filter, max_length_miles)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # --- HyDE: generate hypothetical document for better embedding ---
    search_query = query
    if use_hyde:
        search_query = generate_hyde_query(query)
        logger.info("[retriever] HyDE active — using synthetic query (%d chars)", len(search_query))

    # --- Pool size: fetch more candidates than needed for filtering ---
    pool_size = min(top_k * 40, 400)

    # --- FAISS dense retrieval ---
    dense_candidates: List[Document] = []
    try:
        dense_candidates = faiss_index.similarity_search(search_query, k=pool_size)
    except Exception as exc:
        logger.error("[retriever] FAISS search failed: %s", exc)

    # --- BM25 keyword retrieval + RRF fusion ---
    if use_bm25 and _HAS_BM25 and bm25_index is not None and bm25_corpus is not None:
        bm25_results = bm25_search(bm25_index, bm25_corpus, query, top_k=pool_size)
        dense_idx_list = list(range(len(dense_candidates)))
        bm25_idx_list = [idx for idx, _ in bm25_results]

        fused = reciprocal_rank_fusion([dense_idx_list, bm25_idx_list])
        # Merge unique docs from both corpora based on fused ranking
        all_docs: Dict[int, Document] = {}
        for i, doc in enumerate(dense_candidates):
            all_docs[i] = doc
        bm25_offset = len(dense_candidates)
        for orig_idx, score in bm25_results:
            mapped_idx = bm25_offset + orig_idx
            if mapped_idx not in all_docs:
                all_docs[mapped_idx] = bm25_corpus[orig_idx]

        fused_docs = []
        for doc_idx, _ in fused:
            if doc_idx in all_docs:
                fused_docs.append(all_docs[doc_idx])
        dense_candidates = fused_docs
        logger.debug("[retriever] RRF fusion: %d docs after merging BM25+FAISS", len(dense_candidates))

    # --- Apply metadata filters ---
    if source_filter or region_filter or difficulty_filter or max_length_miles:
        filtered = _apply_metadata_filters(
            dense_candidates, source_filter, region_filter,
            difficulty_filter, max_length_miles,
        )
        logger.debug(
            "[retriever] Metadata filter: %d → %d docs (source=%s, region=%s, diff=%s, maxlen=%s)",
            len(dense_candidates), len(filtered),
            source_filter, region_filter, difficulty_filter, max_length_miles,
        )
        if filtered:
            dense_candidates = filtered
        elif not filtered:
            # Filters too restrictive — add note and fall back to unfiltered
            logger.warning("[retriever] Filters returned 0 results — falling back to unfiltered")
            if dense_candidates:
                dense_candidates[0].page_content = (
                    "[Note: No trails matched all filters — showing closest results]\n"
                    + dense_candidates[0].page_content
                )

    # --- Location manager filtering ---
    if location_managers:
        from ai.services.geography import MANAGER_REGIONS, LOCATION_ALIASES
        import re

        # Strip location keywords from query to get activity-focused query
        activity_query = query
        for keyword in sorted(LOCATION_ALIASES.keys(), key=len, reverse=True):
            activity_query = re.sub(
                re.escape(keyword), "", activity_query, flags=re.IGNORECASE
            ).strip()
        if len(activity_query) < 10:
            activity_query = "good hiking trail moderate difficulty"

        # Build region-enriched query for FAISS
        region_descs = []
        for m in location_managers:
            r = MANAGER_REGIONS.get(m)
            if r:
                region_descs.append(f"near {r[1]}")
        region_suffix = " ".join(region_descs[:3])
        region_query = f"{activity_query} {region_suffix}"

        # Search with region-enriched query
        try:
            region_candidates = faiss_index.similarity_search(
                region_query, k=min(top_k * 30, 200)
            )
        except Exception:
            region_candidates = []

        activity_candidates = dense_candidates  # Already fetched above

        # Merge: prioritise manager-matching docs
        matched = [d for d in region_candidates if d.metadata.get("manager") in location_managers]
        for d in activity_candidates:
            if d.metadata.get("manager") in location_managers:
                name = d.metadata.get("name")
                if not any(m.metadata.get("name") == name for m in matched):
                    matched.append(d)

        if matched:
            dense_candidates = matched
        elif activity_candidates:
            dense_candidates = activity_candidates

    # --- Deduplicate by trail name ---
    dense_candidates = deduplicate_by_name(dense_candidates)

    # --- Cross-encoder reranking ---
    if use_reranker and _HAS_RERANKER:
        candidates_for_rerank = dense_candidates[:min(len(dense_candidates), top_k * 4)]
        dense_candidates = rerank_documents(query, candidates_for_rerank, top_k)
    else:
        dense_candidates = dense_candidates[:top_k]

    elapsed = time.time() - t0
    logger.info(
        "[retriever] Returned %d docs in %.3fs (hyde=%s, bm25=%s, reranker=%s)",
        len(dense_candidates), elapsed, use_hyde, use_bm25, use_reranker,
    )

    _set_cached(cache_key, dense_candidates)
    return dense_candidates


def format_context(documents: List[Document]) -> str:
    """
    Format retrieved documents into a single context string
    suitable for injection into an LLM prompt.
    Includes all available metadata fields.
    """
    if not documents:
        return "No relevant trail information found."

    sections = []
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata
        header = f"Trail {i}: {meta.get('name', 'Unknown')}"

        # Source / Manager / Region line
        parts = []
        src = meta.get("source")
        mgr = meta.get("manager")
        rgn = meta.get("region")
        if src:
            parts.append(f"Source: {src}")
        if mgr:
            parts.append(f"Manager: {mgr}")
        if rgn:
            parts.append(f"Region: {rgn}")
        source_line = ("  " + " | ".join(parts)) if parts else ""

        location = f"  Location: {meta.get('location', 'N/A')}"
        nearby = meta.get("nearby_city")
        if nearby:
            location += f" (near {nearby})"

        difficulty = f"  Difficulty: {meta.get('difficulty', 'N/A')}"
        distance = f"  Distance: {meta.get('distance_miles', 'N/A')} miles"
        elevation = f"  Elevation Gain: {meta.get('elevation_gain_ft', 'N/A')} ft"

        # Activity flags
        activity_parts = []
        if meta.get("hiking"):
            activity_parts.append("hiking")
        if meta.get("bike"):
            activity_parts.append("biking")
        dogs = meta.get("dogs")
        if dogs and str(dogs).lower() not in ("unknown", "none", ""):
            activity_parts.append(f"dogs: {dogs}")
        activities = f"  Activities: {', '.join(activity_parts)}" if activity_parts else ""

        detail = f"  Details: {doc.page_content}"

        lines = [header]
        if source_line:
            lines.append(source_line)
        lines.extend([location, difficulty, distance, elevation])
        if activities:
            lines.append(activities)
        lines.append(detail)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
