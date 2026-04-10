"""
TrailBlaze AI — Task 1 Demo Script
===================================
Processes hardcoded prompts through the full LangGraph pipeline:
1. Builds a FAISS index from sample trail documents
2. Routes queries through classification, retrieval, weather, and synthesis agents
3. Runs quality checks on the output
4. Prints the grounded AI response

Usage:
    cd TrailBlaze-AI
    export OPENAI_API_KEY=sk-...
    python -m ai.run_demo
"""

import os
import sys

from dotenv import load_dotenv

# Load .env from the ai/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from ai.vector_store.sample_trails import SAMPLE_TRAIL_DOCUMENTS
from ai.vector_store.faiss_store import build_faiss_index
from ai.langgraph.graph import build_graph
from ai.quality_checks.rag_quality import run_all_checks


DEMO_QUERIES = [
    "Find a moderate trail near Boulder under 5 miles with shade.",
    "Suggest low lightning-risk options for this afternoon.",
    "What is the easiest family-friendly trail in Rocky Mountain National Park?",
]


def run_query(compiled_graph, query: str, query_num: int) -> None:
    """Run a single query through the full pipeline and print results."""
    print(f"\n{'='*70}")
    print(f"  QUERY {query_num}: {query}")
    print(f"{'='*70}")

    # Execute the graph
    initial_state = {
        "user_query": query,
        "route": None,
        "retrieved_docs": [],
        "trail_context": "",
        "weather_context": "",
        "answer": "",
    }
    result = compiled_graph.invoke(initial_state)

    # Print routing decision
    print(f"\n[Router] Query classified as: {result['route']}")

    # Print retrieved trails
    print(f"\n[Retriever] Found {len(result['retrieved_docs'])} relevant trails:")
    for doc in result["retrieved_docs"]:
        print(f"  - {doc.metadata.get('name', 'Unknown')} ({doc.metadata.get('location', '')})")

    # Print weather context if present
    if result.get("weather_context"):
        print(f"\n[Weather] {result['weather_context']}")

    # Print final answer
    print(f"\n[TrailBlaze AI Response]\n{result['answer']}")

    # Run quality checks
    quality = run_all_checks(
        query=query,
        documents=result["retrieved_docs"],
        trail_context=result.get("trail_context", ""),
        answer=result["answer"],
    )
    status = "PASSED" if quality["overall_passed"] else "FAILED"
    print(f"\n[Quality Check] {status}")
    for check in quality["checks"]:
        icon = "✓" if check["passed"] else "✗"
        print(f"  {icon} {check['check']}: {'pass' if check['passed'] else ', '.join(check['issues'])}")


def main():
    # Validate API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set.")
        print("Set it via: export OPENAI_API_KEY=sk-your-key-here")
        print("Or create ai/.env with the key.")
        sys.exit(1)

    print("TrailBlaze AI — Task 1 Demo")
    print("Building FAISS index from sample trail data...")

    # Build FAISS index
    faiss_index = build_faiss_index(SAMPLE_TRAIL_DOCUMENTS)
    print(f"Indexed {len(SAMPLE_TRAIL_DOCUMENTS)} trail documents.")

    # Build the LangGraph
    compiled_graph = build_graph(faiss_index)
    print("LangGraph compiled successfully.")

    # Run demo queries
    for i, query in enumerate(DEMO_QUERIES, 1):
        run_query(compiled_graph, query, i)

    print(f"\n{'='*70}")
    print("  Demo complete. All queries processed.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
