"""
FAISS vector store builder and retriever.
Creates embeddings from trail documents and provides similarity search.
"""

import os
from typing import List, Dict, Any

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


def _get_embeddings() -> OpenAIEmbeddings:
    """Return an OpenAI embeddings instance using env config."""
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    return OpenAIEmbeddings(model=model)


def build_faiss_index(trail_docs: List[Dict[str, Any]]) -> FAISS:
    """
    Build a FAISS index from a list of trail document dicts.

    Each dict must have a 'text' field for embedding and may include
    arbitrary metadata fields (id, name, location, difficulty, etc.).
    """
    documents = []
    for doc in trail_docs:
        metadata = {k: v for k, v in doc.items() if k != "text"}
        documents.append(Document(page_content=doc["text"], metadata=metadata))

    embeddings = _get_embeddings()
    faiss_index = FAISS.from_documents(documents, embeddings)
    return faiss_index


def retrieve_trails(
    faiss_index: FAISS,
    query: str,
    top_k: int = 3,
) -> List[Document]:
    """
    Retrieve the top-k most relevant trail documents for a query.
    """
    results = faiss_index.similarity_search(query, k=top_k)
    return results


def save_index(faiss_index: FAISS, path: str) -> None:
    """Persist FAISS index to disk."""
    faiss_index.save_local(path)


def load_index(path: str) -> FAISS:
    """Load a persisted FAISS index from disk."""
    embeddings = _get_embeddings()
    return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
