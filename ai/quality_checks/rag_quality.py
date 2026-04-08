"""
RAG quality checks for TrailBlaze AI.
Validates that retrieval and generation meet minimum quality criteria.
"""

from typing import List, Dict, Any

from langchain_core.documents import Document


def check_retrieval_relevance(
    query: str,
    documents: List[Document],
    min_docs: int = 1,
) -> Dict[str, Any]:
    """
    Basic relevance check: ensures at least min_docs were retrieved
    and that documents contain non-empty content.
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


def check_answer_grounding(
    answer: str,
    trail_context: str,
    min_answer_length: int = 50,
) -> Dict[str, Any]:
    """
    Basic grounding check: ensures the answer is non-trivial and
    references at least one trail name from the context.
    """
    passed = True
    issues = []

    if len(answer) < min_answer_length:
        passed = False
        issues.append(f"Answer too short ({len(answer)} chars, min {min_answer_length})")

    # Extract trail names from context for grounding check
    context_lower = trail_context.lower()
    answer_lower = answer.lower()

    # Check if answer mentions at least one trail from context
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


def run_all_checks(
    query: str,
    documents: List[Document],
    trail_context: str,
    answer: str,
) -> Dict[str, Any]:
    """Run all quality checks and return a summary."""
    retrieval_result = check_retrieval_relevance(query, documents)
    grounding_result = check_answer_grounding(answer, trail_context)

    all_passed = retrieval_result["passed"] and grounding_result["passed"]

    return {
        "overall_passed": all_passed,
        "checks": [retrieval_result, grounding_result],
    }
