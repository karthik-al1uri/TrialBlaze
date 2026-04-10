"""
Rebuild the FAISS vector index from all trails in MongoDB.

Loads every trail document, builds embedding text, calls OpenAI
text-embedding-3-small in batches, and saves a LangChain-compatible
FAISS index to ai/vector-store/.

Usage:
    python ai/rag/rebuild_index.py            # full rebuild
    python ai/rag/rebuild_index.py --source NPS  # only NPS trails (merge)
"""

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict, List

from dotenv import load_dotenv

# Load environment from ai/.env
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path)

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "vector-store")


def _get_embeddings() -> OpenAIEmbeddings:
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    return OpenAIEmbeddings(model=model)


def _trail_to_text(trail: Dict[str, Any]) -> str:
    """Build embedding input string from trail fields."""
    parts = []
    name = trail.get("name", "")
    if name:
        parts.append(name)
    difficulty = trail.get("difficulty")
    if difficulty:
        parts.append(difficulty)
    region = trail.get("region")
    if region:
        parts.append(region)
    manager = trail.get("manager")
    if manager:
        parts.append(manager)
    surface = trail.get("surface")
    if surface:
        parts.append(surface)
    length = trail.get("length_miles")
    if length:
        parts.append(f"{length}mi")
    elevation = trail.get("elevation_gain_ft")
    if elevation:
        parts.append(f"{elevation}ft elevation")
    # Add activity flags
    if trail.get("hiking"):
        parts.append("hiking")
    if trail.get("bike"):
        parts.append("biking")
    dogs = trail.get("dogs")
    if dogs and dogs != "unknown":
        parts.append(f"dogs {dogs}")
    # Add reviews if present
    reviews = trail.get("reviews", [])
    for r in reviews[:2]:
        if isinstance(r, dict) and r.get("text"):
            parts.append(r["text"][:200])
        elif isinstance(r, str):
            parts.append(r[:200])
    return " ".join(parts)


def _trail_to_document(trail: Dict[str, Any]) -> Document:
    """Convert a MongoDB trail to a LangChain Document with full metadata."""
    text = _trail_to_text(trail)
    manager = trail.get("manager", "")
    region = trail.get("region", "")
    metadata = {
        "name": trail.get("name", "Unknown"),
        "location": region or manager or "Colorado",
        "nearby_city": "",
        "lat": None,
        "lng": None,
        "difficulty": trail.get("difficulty", "unknown"),
        "distance_miles": trail.get("length_miles"),
        "elevation_gain_ft": trail.get("elevation_gain_ft"),
        "cotrex_fid": trail.get("cotrex_fid"),
        "hiking": trail.get("hiking"),
        "bike": trail.get("bike"),
        "dogs": trail.get("dogs"),
        "manager": manager,
        "source": trail.get("source"),
        "region": region,
    }
    # Try to get coordinates from trail_centroids-style fields
    if trail.get("lat") and trail.get("lng"):
        metadata["lat"] = trail["lat"]
        metadata["lng"] = trail["lng"]
    return Document(page_content=text, metadata=metadata)


def main():
    parser = argparse.ArgumentParser(description="Rebuild FAISS index from MongoDB trails")
    parser.add_argument("--source", type=str, default=None,
                        help="Only embed trails from this source (e.g. NPS). Merges into existing index.")
    args = parser.parse_args()

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("ERROR: MONGO_URI not set. Add it to ai/.env")
        sys.exit(1)
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Add it to ai/.env")
        sys.exit(1)

    # Connect to MongoDB (sync client)
    client = MongoClient(mongo_uri)
    db_name = os.getenv("MONGO_DB_NAME", "trailblaze")
    db = client[db_name]

    # Load trails
    print("Loading trails from MongoDB...")
    query = {}
    if args.source:
        query["source"] = args.source
        print(f"Filtering by source: {args.source}")

    trails = list(db.trails.find(query, {"_id": 0}))

    # Filter out null/empty names
    valid_trails = [t for t in trails if t.get("name", "").strip()]
    skipped = len(trails) - len(valid_trails)
    print(f"Loaded {len(trails)} trails total. Skipping {skipped} with null names.")

    if not valid_trails:
        print("No valid trails to embed. Exiting.")
        client.close()
        return

    # Build documents
    print(f"Building embedding strings for {len(valid_trails)} trails...")
    documents = [_trail_to_document(t) for t in valid_trails]

    # Generate embeddings in batches
    print("Generating embeddings in batches of 100...")
    embeddings = _get_embeddings()
    batch_size = 100
    total_batches = (len(documents) + batch_size - 1) // batch_size

    faiss_index = None
    for batch_num in range(total_batches):
        start = batch_num * batch_size
        end = min(start + batch_size, len(documents))
        batch_docs = documents[start:end]
        print(f"Embedding batch {batch_num + 1} of {total_batches} (trails {start + 1} to {end})...")

        t0 = time.time()
        for attempt in range(2):
            try:
                batch_index = FAISS.from_documents(batch_docs, embeddings)
                elapsed = time.time() - t0
                if elapsed > 30:
                    print(f"WARNING: OpenAI API slow on batch {batch_num + 1}. Check rate limits.")
                if faiss_index is None:
                    faiss_index = batch_index
                else:
                    faiss_index.merge_from(batch_index)
                break
            except Exception as e:
                elapsed = time.time() - t0
                if attempt == 0:
                    print(f"WARNING: Batch {batch_num + 1} failed ({e}). Retrying in 5s...")
                    time.sleep(5)
                else:
                    print(f"ERROR: Batch {batch_num + 1} failed after retry. Skipping.")

    if faiss_index is None:
        print("ERROR: No embeddings generated. Exiting.")
        client.close()
        return

    # If --source flag, merge into existing index
    if args.source and os.path.exists(os.path.join(INDEX_DIR, "index.faiss")):
        print(f"Merging {args.source} embeddings into existing index...")
        existing = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        existing.merge_from(faiss_index)
        faiss_index = existing

    # Save index
    print("All embeddings done. Building FAISS index...")
    os.makedirs(INDEX_DIR, exist_ok=True)
    print("Saving index to ai/vector-store/...")
    faiss_index.save_local(INDEX_DIR)
    print(f"Index saved. Contains {faiss_index.index.ntotal} vectors.")

    # Source breakdown
    source_counts: Dict[str, int] = {}
    for doc in documents:
        src = doc.metadata.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    # If merged, recount from full index docstore
    if args.source:
        source_counts = {}
        for doc_id in faiss_index.docstore._dict.values():
            src = doc_id.metadata.get("source", "unknown") if hasattr(doc_id, "metadata") else "unknown"
            source_counts[src] = source_counts.get(src, 0) + 1

    print("Source breakdown in index:")
    for src in sorted(source_counts.keys()):
        print(f"  {src}: {source_counts[src]}")

    total = sum(source_counts.values())
    print(f"FAISS rebuild complete. AI chat now covers all {total} trails.")

    client.close()


if __name__ == "__main__":
    main()
