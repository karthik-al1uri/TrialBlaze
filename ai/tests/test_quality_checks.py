"""Tests for RAG quality check functions."""

from langchain_core.documents import Document

from ai.quality_checks.rag_quality import (
    check_retrieval_relevance,
    check_answer_grounding,
    run_all_checks,
)


# --- Retrieval relevance ---

def test_retrieval_relevance_passes():
    docs = [Document(page_content="Trail info here.")]
    result = check_retrieval_relevance("query", docs, min_docs=1)
    assert result["passed"] is True
    assert result["num_docs_retrieved"] == 1


def test_retrieval_relevance_fails_no_docs():
    result = check_retrieval_relevance("query", [], min_docs=1)
    assert result["passed"] is False


def test_retrieval_relevance_fails_empty_content():
    docs = [Document(page_content="   ")]
    result = check_retrieval_relevance("query", docs, min_docs=1)
    assert result["passed"] is False


# --- Answer grounding ---

def test_answer_grounding_passes():
    context = "Trail 1: Royal Arch Trail\n  Location: Boulder"
    answer = "I recommend Royal Arch Trail near Boulder. It is a moderate hike with great views."
    result = check_answer_grounding(answer, context)
    assert result["passed"] is True


def test_answer_grounding_fails_short():
    result = check_answer_grounding("Yes.", "Trail 1: Test", min_answer_length=50)
    assert result["passed"] is False


def test_answer_grounding_fails_no_trail_reference():
    context = "Trail 1: Royal Arch Trail\n  Location: Boulder"
    answer = "I recommend going outside. The weather is nice and there are many options to explore in this area."
    result = check_answer_grounding(answer, context)
    assert result["passed"] is False


# --- Run all checks ---

def test_run_all_checks_overall_pass():
    docs = [Document(page_content="Royal Arch Trail is great.")]
    context = "Trail 1: Royal Arch Trail\n  Location: Boulder"
    answer = "I recommend Royal Arch Trail near Boulder. It is a moderate hike with scenic views of the Flatirons."
    result = run_all_checks("find a trail", docs, context, answer)
    assert result["overall_passed"] is True
    assert len(result["checks"]) == 2


def test_run_all_checks_overall_fail():
    result = run_all_checks("query", [], "", "Short.")
    assert result["overall_passed"] is False
