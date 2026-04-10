"""Tests for the RAG retriever context formatting."""

from langchain_core.documents import Document

from ai.rag.retriever import format_context


def test_format_context_empty():
    result = format_context([])
    assert result == "No relevant trail information found."


def test_format_context_single_doc():
    doc = Document(
        page_content="A great trail near Boulder.",
        metadata={"name": "Test Trail", "location": "Boulder, CO", "difficulty": "easy",
                   "distance_miles": 2.0, "elevation_gain_ft": 300},
    )
    result = format_context([doc])
    assert "Trail 1: Test Trail" in result
    assert "Boulder, CO" in result
    assert "easy" in result
    assert "2.0 miles" in result
    assert "300 ft" in result
    assert "A great trail near Boulder." in result


def test_format_context_multiple_docs():
    docs = [
        Document(page_content="Trail A info.", metadata={"name": "Trail A"}),
        Document(page_content="Trail B info.", metadata={"name": "Trail B"}),
    ]
    result = format_context(docs)
    assert "Trail 1: Trail A" in result
    assert "Trail 2: Trail B" in result
