"""
Tests for RAG quality check functions.

Covers:
  - check_retrieval_relevance: passes, fails on no docs, fails on empty content
  - check_answer_grounding: passes, fails on short answer, fails on no trail ref
  - check_response_relevance: keyword overlap scoring
  - benchmark_latency: times a callable, checks SLA
  - benchmark_retrieval_stages: latency stats over mock FAISS
  - run_all_checks: all 3 checks combined
"""

from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from ai.quality_checks.rag_quality import (
    check_retrieval_relevance,
    check_answer_grounding,
    check_response_relevance,
    benchmark_latency,
    benchmark_retrieval_stages,
    run_all_checks,
)


# ---------------------------------------------------------------------------
# check_retrieval_relevance
# ---------------------------------------------------------------------------

def test_retrieval_relevance_passes():
    docs = [Document(page_content="Trail info here.")]
    result = check_retrieval_relevance("query", docs, min_docs=1)
    assert result["passed"] is True
    assert result["num_docs_retrieved"] == 1


def test_retrieval_relevance_fails_no_docs():
    result = check_retrieval_relevance("query", [], min_docs=1)
    assert result["passed"] is False
    assert any("docs" in i.lower() for i in result["issues"])


def test_retrieval_relevance_fails_empty_content():
    docs = [Document(page_content="   ")]
    result = check_retrieval_relevance("query", docs, min_docs=1)
    assert result["passed"] is False


def test_retrieval_relevance_multiple_docs_one_empty():
    docs = [
        Document(page_content="Good trail info."),
        Document(page_content="   "),
    ]
    result = check_retrieval_relevance("query", docs, min_docs=1)
    assert result["passed"] is False
    assert result["num_docs_retrieved"] == 2


def test_retrieval_relevance_more_than_min():
    docs = [Document(page_content=f"Trail {i}") for i in range(5)]
    result = check_retrieval_relevance("query", docs, min_docs=3)
    assert result["passed"] is True


# ---------------------------------------------------------------------------
# check_answer_grounding
# ---------------------------------------------------------------------------

def test_answer_grounding_passes():
    context = "Trail 1: Royal Arch Trail\n  Location: Boulder"
    answer = "I recommend Royal Arch Trail near Boulder. It is a moderate hike with great views."
    result = check_answer_grounding(answer, context)
    assert result["passed"] is True
    assert result["answer_length"] > 50


def test_answer_grounding_fails_short():
    result = check_answer_grounding("Yes.", "Trail 1: Test", min_answer_length=50)
    assert result["passed"] is False
    assert any("short" in i.lower() for i in result["issues"])


def test_answer_grounding_fails_no_trail_reference():
    context = "Trail 1: Royal Arch Trail\n  Location: Boulder"
    answer = "I recommend going outside. The weather is nice and there are many options to explore in this area."
    result = check_answer_grounding(answer, context)
    assert result["passed"] is False


def test_answer_grounding_no_context_trails():
    # When context has no Trail N: lines, grounding check is skipped
    result = check_answer_grounding(
        "A nice trail to visit is the mountain path.", "No trails listed here.", min_answer_length=10
    )
    assert result["passed"] is True


def test_answer_grounding_extracts_trail_names():
    context = "Trail 1: Bear Lake Loop\nTrail 2: Sky Pond Trail"
    answer = "Sky Pond Trail is my recommendation."
    result = check_answer_grounding(answer, context, min_answer_length=10)
    assert result["passed"] is True
    assert "Bear Lake Loop" in result["trail_names_in_context"]
    assert "Sky Pond Trail" in result["trail_names_in_context"]


# ---------------------------------------------------------------------------
# check_response_relevance
# ---------------------------------------------------------------------------

def test_response_relevance_passes_high_overlap():
    query = "easy dog-friendly hike near Boulder"
    answer = "I recommend an easy hike near Boulder. Dogs are welcome on this trail."
    result = check_response_relevance(query, answer, min_overlap_ratio=0.3)
    assert result["passed"] is True
    assert result["overlap_ratio"] >= 0.3


def test_response_relevance_fails_low_overlap():
    query = "hard alpine summit Colorado 14er"
    answer = "The weather today is sunny and warm."
    result = check_response_relevance(query, answer, min_overlap_ratio=0.5)
    assert result["passed"] is False


def test_response_relevance_empty_query():
    result = check_response_relevance("", "Any answer text here.", min_overlap_ratio=0.3)
    assert isinstance(result["passed"], bool)


def test_response_relevance_stopwords_only_query():
    result = check_response_relevance("what is the for a", "Some answer.", min_overlap_ratio=0.1)
    # All stopwords — no meaningful tokens — should pass (vacuously)
    assert result["passed"] is True


def test_response_relevance_partial_overlap():
    query = "moderate trail with views and waterfall"
    answer = "This trail has stunning views from the summit."
    result = check_response_relevance(query, answer, min_overlap_ratio=0.2)
    assert "views" in result["matched_tokens"]
    assert "trail" in result["matched_tokens"]


# ---------------------------------------------------------------------------
# benchmark_latency
# ---------------------------------------------------------------------------

def test_benchmark_latency_fast_function_passes():
    def fast_fn():
        return 42

    result = benchmark_latency(fast_fn, label="fast_fn", max_latency_seconds=5.0)
    assert result["passed"] is True
    assert result["result"] == 42
    assert result["elapsed_seconds"] < 5.0


def test_benchmark_latency_slow_function_fails():
    import time

    def slow_fn():
        time.sleep(0.05)
        return "done"

    result = benchmark_latency(slow_fn, label="slow_fn", max_latency_seconds=0.01)
    assert result["passed"] is False
    assert result["result"] == "done"


def test_benchmark_latency_raises_exception():
    def failing_fn():
        raise ValueError("simulated failure")

    result = benchmark_latency(failing_fn, label="failing_fn", max_latency_seconds=5.0)
    assert result["passed"] is False
    assert result["error"] is not None
    assert "simulated failure" in result["error"]


def test_benchmark_latency_with_args():
    def add(a, b):
        return a + b

    result = benchmark_latency(add, 3, 4, label="add", max_latency_seconds=1.0)
    assert result["passed"] is True
    assert result["result"] == 7


# ---------------------------------------------------------------------------
# benchmark_retrieval_stages (mock FAISS)
# ---------------------------------------------------------------------------

def test_benchmark_retrieval_stages_with_mock():
    mock_doc = Document(page_content="Trail info", metadata={"name": "Test Trail"})
    mock_index = MagicMock()
    mock_index.similarity_search.return_value = [mock_doc]

    queries = ["easy hike near Denver", "dog friendly trail", "moderate summit Colorado"]
    result = benchmark_retrieval_stages(
        mock_index, queries, top_k=3, max_latency_seconds=5.0
    )
    assert result["passed"] is True
    assert result["num_queries"] == 3
    assert result["p95_seconds"] < 5.0


def test_benchmark_retrieval_stages_faiss_error():
    mock_index = MagicMock()
    mock_index.similarity_search.side_effect = RuntimeError("FAISS down")

    result = benchmark_retrieval_stages(
        mock_index, ["trail query"], top_k=3, max_latency_seconds=5.0
    )
    assert result["num_queries"] == 1
    assert len(result["failures"]) == 1


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------

def test_run_all_checks_overall_pass():
    docs = [Document(page_content="Royal Arch Trail is great.")]
    context = "Trail 1: Royal Arch Trail\n  Location: Boulder"
    answer = "I recommend Royal Arch Trail near Boulder. It is a moderate hike with scenic views."
    result = run_all_checks("find a trail near Boulder", docs, context, answer)
    assert result["overall_passed"] is True
    assert result["checks_total"] == 3
    assert result["checks_passed"] == 3


def test_run_all_checks_overall_fail_empty():
    result = run_all_checks("query", [], "", "Short.")
    assert result["overall_passed"] is False
    assert result["checks_passed"] < result["checks_total"]


def test_run_all_checks_partial_failure():
    docs = [Document(page_content="Bear Lake Loop info.")]
    context = "Trail 1: Bear Lake Loop"
    answer = "Bear Lake Loop is perfect for families. It is a short, easy walk around Bear Lake."
    # Grounding and relevance pass, but min_docs=2 will fail retrieval check
    result = run_all_checks("easy family trail", docs, context, answer, min_docs=2)
    assert result["overall_passed"] is False
    assert result["checks_total"] == 3


def test_run_all_checks_returns_check_names():
    docs = [Document(page_content="Trail details.")]
    context = "Trail 1: Test Trail"
    answer = "Test Trail is a great choice for hiking in Colorado."
    result = run_all_checks("hike", docs, context, answer)
    check_names = {c["check"] for c in result["checks"]}
    assert "retrieval_relevance" in check_names
    assert "answer_grounding" in check_names
    assert "response_relevance" in check_names
