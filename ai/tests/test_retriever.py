"""
Tests for the RAG retriever module.

Covers:
  - format_context: empty, single doc, multiple docs, activity flags
  - deduplicate_by_name: removes duplicate trail names
  - _matches_difficulty: difficulty normalization
  - _matches_length: max distance filtering
  - _apply_metadata_filters: combined filter logic
  - reciprocal_rank_fusion: RRF score computation
  - build_bm25_index / bm25_search: BM25 keyword ranking
  - rerank_documents: fallback behavior when reranker unavailable
  - generate_hyde_query: fallback when LLM unavailable
  - retrieve_context: mock-FAISS integration test
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from ai.rag.retriever import (
    format_context,
    deduplicate_by_name,
    reciprocal_rank_fusion,
    build_bm25_index,
    bm25_search,
    rerank_documents,
    generate_hyde_query,
    _matches_difficulty,
    _matches_length,
    _apply_metadata_filters,
    retrieve_context,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_doc(name, difficulty="moderate", distance=5.0, source="COTREX", region="Front Range",
              content="Trail info."):
    return Document(
        page_content=content,
        metadata={
            "name": name,
            "difficulty": difficulty,
            "distance_miles": distance,
            "source": source,
            "region": region,
        },
    )


@pytest.fixture
def sample_docs():
    return [
        _make_doc("Royal Arch Trail", "moderate", 3.4, content="Steep trail with stone arch near Boulder."),
        _make_doc("Bear Lake Loop", "easy", 0.8, content="Easy loop around Bear Lake in RMNP."),
        _make_doc("Longs Peak", "hard", 14.5, content="14er summit route. Very strenuous."),
        _make_doc("Sky Pond Trail", "hard", 9.4, content="Alpine lake and waterfall in RMNP."),
        _make_doc("Garden of Gods", "easy", 3.5, content="Red rock formations near Colorado Springs."),
    ]


# ---------------------------------------------------------------------------
# format_context tests
# ---------------------------------------------------------------------------

def test_format_context_empty():
    result = format_context([])
    assert result == "No relevant trail information found."


def test_format_context_single_doc():
    doc = Document(
        page_content="A great trail near Boulder.",
        metadata={
            "name": "Test Trail", "location": "Boulder, CO", "difficulty": "easy",
            "distance_miles": 2.0, "elevation_gain_ft": 300,
        },
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


def test_format_context_includes_source_and_manager():
    doc = Document(
        page_content="Trail details.",
        metadata={
            "name": "Summit Trail", "source": "NPS", "manager": "Rocky Mountain NP",
            "region": "Front Range",
        },
    )
    result = format_context([doc])
    assert "Source: NPS" in result
    assert "Manager: Rocky Mountain NP" in result
    assert "Region: Front Range" in result


def test_format_context_activity_flags():
    doc = Document(
        page_content="Dog-friendly trail.",
        metadata={"name": "Dog Trail", "hiking": True, "bike": False, "dogs": "leash"},
    )
    result = format_context([doc])
    assert "hiking" in result
    assert "dogs: leash" in result


def test_format_context_nearby_city():
    doc = Document(
        page_content="Trail details.",
        metadata={"name": "Mountain Trail", "location": "Colorado", "nearby_city": "Boulder"},
    )
    result = format_context([doc])
    assert "near Boulder" in result


# ---------------------------------------------------------------------------
# deduplicate_by_name tests
# ---------------------------------------------------------------------------

def test_deduplicate_removes_duplicate_names(sample_docs):
    duplicated = sample_docs + [_make_doc("Royal Arch Trail", content="Duplicate entry.")]
    result = deduplicate_by_name(duplicated)
    names = [d.metadata["name"] for d in result]
    assert names.count("Royal Arch Trail") == 1


def test_deduplicate_preserves_order(sample_docs):
    result = deduplicate_by_name(sample_docs)
    assert result[0].metadata["name"] == "Royal Arch Trail"
    assert result[1].metadata["name"] == "Bear Lake Loop"


def test_deduplicate_empty_list():
    assert deduplicate_by_name([]) == []


def test_deduplicate_case_insensitive():
    docs = [
        _make_doc("Bear Lake Loop"),
        _make_doc("bear lake loop"),  # lowercase duplicate
    ]
    result = deduplicate_by_name(docs)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Metadata filter tests
# ---------------------------------------------------------------------------

def test_matches_difficulty_exact():
    doc = _make_doc("Trail", "moderate")
    assert _matches_difficulty(doc, "moderate") is True
    assert _matches_difficulty(doc, "easy") is False


def test_matches_difficulty_synonym():
    doc = _make_doc("Trail", "strenuous")
    assert _matches_difficulty(doc, "hard") is True


def test_matches_difficulty_none_filter():
    doc = _make_doc("Trail", "hard")
    assert _matches_difficulty(doc, None) is True


def test_matches_length_within_limit():
    doc = _make_doc("Trail", distance=4.0)
    assert _matches_length(doc, 5.0) is True


def test_matches_length_exceeds_limit():
    doc = _make_doc("Trail", distance=10.0)
    assert _matches_length(doc, 5.0) is False


def test_matches_length_no_filter():
    doc = _make_doc("Trail", distance=100.0)
    assert _matches_length(doc, None) is True


def test_matches_length_missing_metadata():
    doc = Document(page_content="x", metadata={"name": "T"})
    assert _matches_length(doc, 3.0) is True


def test_apply_metadata_filters_difficulty(sample_docs):
    result = _apply_metadata_filters(sample_docs, None, None, "easy", None)
    assert all(d.metadata["difficulty"] in ("easy", "beginner", "low") for d in result)
    assert len(result) == 2


def test_apply_metadata_filters_max_length(sample_docs):
    result = _apply_metadata_filters(sample_docs, None, None, None, 5.0)
    assert all((d.metadata.get("distance_miles") or 0) <= 5.0 for d in result)


def test_apply_metadata_filters_source(sample_docs):
    docs = sample_docs[:2]
    docs[0].metadata["source"] = "NPS"
    result = _apply_metadata_filters(docs, ["NPS"], None, None, None)
    assert len(result) == 1
    assert result[0].metadata["source"] == "NPS"


# ---------------------------------------------------------------------------
# RRF tests
# ---------------------------------------------------------------------------

def test_rrf_single_list():
    ranked = [[0, 1, 2]]
    result = reciprocal_rank_fusion(ranked)
    scores = {idx: s for idx, s in result}
    assert scores[0] > scores[1] > scores[2]


def test_rrf_two_lists_consensus():
    # Doc 0 is top in both lists — should win by large margin
    list_a = [0, 1, 2]
    list_b = [0, 2, 1]
    result = reciprocal_rank_fusion([list_a, list_b])
    winner_idx = result[0][0]
    assert winner_idx == 0


def test_rrf_empty_lists():
    result = reciprocal_rank_fusion([])
    assert result == []


def test_rrf_doc_in_one_list_only():
    # Doc 99 only appears in list_b — should still appear in output
    result = reciprocal_rank_fusion([[0, 1], [99, 0]])
    indices = [idx for idx, _ in result]
    assert 99 in indices


# ---------------------------------------------------------------------------
# BM25 tests
# ---------------------------------------------------------------------------

def test_build_bm25_index_returns_none_without_library(sample_docs):
    import ai.rag.retriever as r_module
    original = r_module._HAS_BM25
    r_module._HAS_BM25 = False
    idx = build_bm25_index(sample_docs)
    r_module._HAS_BM25 = original
    assert idx is None


def test_bm25_search_returns_empty_without_index(sample_docs):
    result = bm25_search(None, sample_docs, "easy hike", top_k=3)
    assert result == []


def test_bm25_search_with_real_index(sample_docs):
    import ai.rag.retriever as r_module
    if not r_module._HAS_BM25:
        pytest.skip("rank_bm25 not installed")
    idx = build_bm25_index(sample_docs)
    results = bm25_search(idx, sample_docs, "alpine lake waterfall", top_k=3)
    assert len(results) > 0
    # Sky Pond (index 3) mentions both 'alpine lake' and 'waterfall' — should rank high
    top_idx = results[0][0]
    assert sample_docs[top_idx].metadata["name"] == "Sky Pond Trail"


# ---------------------------------------------------------------------------
# Reranker fallback test
# ---------------------------------------------------------------------------

def test_rerank_documents_falls_back_without_reranker(sample_docs):
    import ai.rag.retriever as r_module
    original = r_module._HAS_RERANKER
    r_module._HAS_RERANKER = False
    result = rerank_documents("moderate hike Boulder", sample_docs, top_k=3)
    r_module._HAS_RERANKER = original
    assert len(result) == 3


def test_rerank_documents_empty_input():
    result = rerank_documents("any query", [], top_k=3)
    assert result == []


# ---------------------------------------------------------------------------
# HyDE fallback test
# ---------------------------------------------------------------------------

def test_generate_hyde_query_falls_back_on_error():
    with patch("ai.rag.retriever.ChatOpenAI", side_effect=ImportError("no openai")):
        result = generate_hyde_query("easy hike near Boulder with a dog")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# retrieve_context integration test with mock FAISS
# ---------------------------------------------------------------------------

def test_retrieve_context_basic_mock(sample_docs):
    mock_index = MagicMock()
    mock_index.similarity_search.return_value = sample_docs[:3]

    result = retrieve_context(mock_index, "moderate trail near Boulder", top_k=3)
    assert len(result) <= 3
    mock_index.similarity_search.assert_called()


def test_retrieve_context_deduplicates(sample_docs):
    doubled = sample_docs[:2] + sample_docs[:2]  # duplicate the first 2
    mock_index = MagicMock()
    mock_index.similarity_search.return_value = doubled

    result = retrieve_context(mock_index, "trail", top_k=4)
    names = [d.metadata["name"] for d in result]
    assert len(names) == len(set(names))


def test_retrieve_context_difficulty_filter(sample_docs):
    mock_index = MagicMock()
    mock_index.similarity_search.return_value = sample_docs

    result = retrieve_context(mock_index, "hike", top_k=5, difficulty_filter="easy")
    assert all(_matches_difficulty(d, "easy") for d in result)


def test_retrieve_context_faiss_error_returns_empty():
    mock_index = MagicMock()
    mock_index.similarity_search.side_effect = RuntimeError("FAISS unavailable")

    result = retrieve_context(mock_index, "any query", top_k=3)
    assert isinstance(result, list)
    assert len(result) == 0


def test_retrieve_context_cache_hit(sample_docs):
    mock_index = MagicMock()
    mock_index.similarity_search.return_value = sample_docs[:3]

    query = "unique cache test query xyzzy123"
    result1 = retrieve_context(mock_index, query, top_k=3)
    call_count_after_first = mock_index.similarity_search.call_count

    result2 = retrieve_context(mock_index, query, top_k=3)
    # Second call should use cache — no additional FAISS call
    assert mock_index.similarity_search.call_count == call_count_after_first
    assert [d.metadata["name"] for d in result1] == [d.metadata["name"] for d in result2]
