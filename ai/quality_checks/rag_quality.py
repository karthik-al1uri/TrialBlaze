"""
RAG quality checks for TrailBlaze AI.

Validates retrieval and generation quality:
  - Retrieval relevance: enough docs returned, non-empty content
  - Answer grounding: answer references retrieved trail names
  - Latency benchmarking: measure time per retrieval stage
  - Retrieval precision: fraction of known-relevant docs in top-k
  - Response relevance scoring: keyword overlap between query and answer
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Check 1: Retrieval relevance
# ---------------------------------------------------------------------------

def check_retrieval_relevance(
    query: str,
    documents: List[Document],
    min_docs: int = 1,
) -> Dict[str, Any]:
    """
    Ensures at least min_docs were retrieved and content is non-empty.
    """
    passed = True
    issues = []

    if len(documents) < min_docs:
        passed = False
        issues.append(f"Expected at least {min_docs} docs, got {len(documents)}")

    empty_docs = [i for i, d in enumerate(documents) if not d.page_content.strip()]
    if empty_docs:
        passed = False
        issues.append(f"Empty content in document indices: {empty_docs}")

    return {
        "check": "retrieval_relevance",
        "passed": passed,
        "num_docs_retrieved": len(documents),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Check 2: Answer grounding
# ---------------------------------------------------------------------------

def check_answer_grounding(
    answer: str,
    trail_context: str,
    min_answer_length: int = 50,
) -> Dict[str, Any]:
    """
    Ensures the answer is non-trivial and references at least one trail
    name from the retrieved context.
    """
    passed = True
    issues = []

    if len(answer) < min_answer_length:
        passed = False
        issues.append(f"Answer too short ({len(answer)} chars, min {min_answer_length})")

    answer_lower = answer.lower()

    trail_names = []
    for line in trail_context.split("\n"):
        if line.startswith("Trail ") and ":" in line:
            name = line.split(":", 1)[1].strip()
            trail_names.append(name)

    if trail_names:
        grounded = any(name.lower() in answer_lower for name in trail_names)
        if not grounded:
            passed = False
            issues.append("Answer does not reference any retrieved trail names")

    return {
        "check": "answer_grounding",
        "passed": passed,
        "answer_length": len(answer),
        "trail_names_in_context": trail_names,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Check 3: Latency benchmarking
# ---------------------------------------------------------------------------

def benchmark_latency(
    fn: Callable,
    *args,
    label: str = "operation",
    max_latency_seconds: float = 5.0,
    **kwargs,
) -> Dict[str, Any]:
    """
    Time a callable and check whether it completes within max_latency_seconds.

    Args:
        fn: The callable to benchmark.
        *args: Positional arguments for fn.
        label: Human-readable name for the operation being benchmarked.
        max_latency_seconds: SLA threshold in seconds.
        **kwargs: Keyword arguments for fn.

    Returns:
        Dict with elapsed_seconds, passed (bool), and result.
    """
    t0 = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        error = None
    except Exception as exc:
        result = None
        error = str(exc)
    elapsed = time.perf_counter() - t0

    passed = error is None and elapsed <= max_latency_seconds

    return {
        "check": "latency",
        "label": label,
        "elapsed_seconds": round(elapsed, 4),
        "max_latency_seconds": max_latency_seconds,
        "passed": passed,
        "error": error,
        "result": result,
    }


def benchmark_retrieval_stages(
    faiss_index,
    queries: List[str],
    top_k: int = 3,
    max_latency_seconds: float = 3.0,
) -> Dict[str, Any]:
    """
    Benchmark FAISS retrieval latency over a set of queries.

    Returns per-query timings and overall pass/fail based on p95 latency.
    """
    from ai.rag.retriever import retrieve_context

    timings = []
    failures = []

    for query in queries:
        t0 = time.perf_counter()
        try:
            docs = retrieve_context(faiss_index, query, top_k=top_k)
            elapsed = time.perf_counter() - t0
            timings.append(elapsed)
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            timings.append(elapsed)
            failures.append({"query": query, "error": str(exc)})

    if not timings:
        return {
            "check": "retrieval_latency",
            "passed": False,
            "issues": ["No queries were benchmarked"],
        }

    sorted_timings = sorted(timings)
    p50 = sorted_timings[len(sorted_timings) // 2]
    p95_idx = max(0, int(len(sorted_timings) * 0.95) - 1)
    p95 = sorted_timings[p95_idx]
    avg = sum(timings) / len(timings)
    passed = p95 <= max_latency_seconds

    return {
        "check": "retrieval_latency",
        "passed": passed,
        "num_queries": len(queries),
        "avg_seconds": round(avg, 4),
        "p50_seconds": round(p50, 4),
        "p95_seconds": round(p95, 4),
        "max_latency_seconds": max_latency_seconds,
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# Check 4: Retrieval precision on known queries
# ---------------------------------------------------------------------------

def check_retrieval_precision(
    faiss_index,
    known_queries: List[Tuple[str, List[str]]],
    top_k: int = 3,
    min_precision: float = 0.5,
) -> Dict[str, Any]:
    """
    Measure retrieval precision on a set of queries with known-relevant trail names.

    Args:
        faiss_index: FAISS index to search.
        known_queries: List of (query, list_of_relevant_trail_names) tuples.
        top_k: Number of results to retrieve per query.
        min_precision: Minimum acceptable average precision (0.0–1.0).

    Returns:
        Dict with per-query precision and overall average.
    """
    from ai.rag.retriever import retrieve_context

    query_results = []
    total_precision = 0.0

    for query, relevant_names in known_queries:
        try:
            docs = retrieve_context(faiss_index, query, top_k=top_k)
        except Exception:
            docs = []

        retrieved_names_lower = {
            (d.metadata.get("name") or "").lower() for d in docs
        }
        relevant_lower = {n.lower() for n in relevant_names}
        hits = len(retrieved_names_lower & relevant_lower)
        precision = hits / top_k if top_k > 0 else 0.0
        total_precision += precision

        query_results.append({
            "query": query,
            "relevant": relevant_names,
            "retrieved": [d.metadata.get("name", "?") for d in docs],
            "hits": hits,
            "precision_at_k": round(precision, 3),
        })

    avg_precision = total_precision / len(known_queries) if known_queries else 0.0
    passed = avg_precision >= min_precision

    return {
        "check": "retrieval_precision",
        "passed": passed,
        "avg_precision_at_k": round(avg_precision, 3),
        "min_precision": min_precision,
        "num_queries": len(known_queries),
        "query_results": query_results,
    }


# ---------------------------------------------------------------------------
# Check 5: Response relevance scoring
# ---------------------------------------------------------------------------

def check_response_relevance(
    query: str,
    answer: str,
    min_overlap_ratio: float = 0.1,
) -> Dict[str, Any]:
    """
    Measure keyword overlap between the query and the answer.

    Computes what fraction of non-stopword query tokens appear in the answer.
    This is a lightweight proxy for answer relevance without needing an LLM judge.

    Args:
        query: The original user query.
        answer: The generated answer text.
        min_overlap_ratio: Minimum fraction of query keywords that must appear in answer.

    Returns:
        Dict with overlap_ratio and passed flag.
    """
    _STOPWORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
        "but", "is", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "i", "me", "my", "we", "you", "he", "she", "they",
        "it", "its", "near", "with", "from", "by", "that", "this", "there",
        "what", "how", "when", "where", "which", "who",
    }

    query_tokens = {
        w.strip(".,?!").lower()
        for w in query.split()
        if w.strip(".,?!").lower() not in _STOPWORDS and len(w) > 2
    }
    answer_lower = answer.lower()

    if not query_tokens:
        return {
            "check": "response_relevance",
            "passed": True,
            "overlap_ratio": 1.0,
            "matched_tokens": [],
            "issues": ["No meaningful query tokens to check"],
        }

    matched = [tok for tok in query_tokens if tok in answer_lower]
    overlap_ratio = len(matched) / len(query_tokens)
    passed = overlap_ratio >= min_overlap_ratio

    return {
        "check": "response_relevance",
        "passed": passed,
        "overlap_ratio": round(overlap_ratio, 3),
        "min_overlap_ratio": min_overlap_ratio,
        "query_tokens": list(query_tokens),
        "matched_tokens": matched,
        "issues": [] if passed else [
            f"Low query-answer overlap: {overlap_ratio:.1%} (min {min_overlap_ratio:.1%})"
        ],
    }


# ---------------------------------------------------------------------------
# Composite: run all checks
# ---------------------------------------------------------------------------

def run_all_checks(
    query: str,
    documents: List[Document],
    trail_context: str,
    answer: str,
    min_docs: int = 1,
    min_answer_length: int = 50,
    min_overlap_ratio: float = 0.1,
) -> Dict[str, Any]:
    """
    Run all quality checks and return a consolidated summary.

    Checks run:
      1. retrieval_relevance
      2. answer_grounding
      3. response_relevance

    Returns:
        Dict with overall_passed, individual check results, and aggregate stats.
    """
    retrieval_result = check_retrieval_relevance(query, documents, min_docs=min_docs)
    grounding_result = check_answer_grounding(answer, trail_context, min_answer_length=min_answer_length)
    relevance_result = check_response_relevance(query, answer, min_overlap_ratio=min_overlap_ratio)

    all_checks = [retrieval_result, grounding_result, relevance_result]
    all_passed = all(c["passed"] for c in all_checks)
    num_passed = sum(1 for c in all_checks if c["passed"])

    return {
        "overall_passed": all_passed,
        "checks_passed": num_passed,
        "checks_total": len(all_checks),
        "checks": all_checks,
    }
