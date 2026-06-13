"""
store/vector_store.py

ChromaDB wrapper managing three collections:

  match_facts: match data (scorers, cards, stats, timeline)
  reactions: scraped match reports and reactions
  career_history: player career profiles and historical context

Documents are stored with metadata so you can filter by match_id,
player, team, or date at query time.
"""

import os
import chromadb
from chromadb.config import Settings

from models import SearchResult
from store.embedder import embed, embed_one

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
COLLECTIONS = ("match_facts", "reactions", "career_history")

_client: chromadb.Client | None = None

def _get_client() -> chromadb.Client:
    global _client
    if _client is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=DATA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client

def _get_collection(name: str):
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )

def upsert_documents(
    collection_name: str,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict],
) -> None:
    if collection_name not in COLLECTIONS:
        raise ValueError(
            f"Unknown collection '{collection_name}'. Valid options: {COLLECTIONS}"
        )
    if any(len(m) == 0 for m in metadatas):
        raise ValueError("All metadata dicts must be non-empty. Use at least one key.")

    collection = _get_collection(collection_name)
    embeddings = embed(texts)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    print(f"[vector_store] Upserted {len(ids)} documents in '{collection_name}'")

def query(
    collection_name: str,
    query_text: str,
    n_results: int = 5,
    where: dict | None = None,
) -> list[SearchResult]:
    
    if collection_name not in COLLECTIONS:
        raise ValueError(
            f"Unknown collection '{collection_name}'. Valid options: {COLLECTIONS}"
        )
    collection = _get_collection(collection_name)
    embedding = embed_one(query_text)

    kwargs = dict(
        query_embeddings=[embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    raw = collection.query(**kwargs)

    return [
        SearchResult(
            id=raw["ids"][0][i],
            text=raw["documents"][0][i],
            metadata=raw["metadatas"][0][i],
            distance=raw["distances"][0][i],
        )
        for i in range(len(raw["ids"][0]))
    ]

def query_all_collections(
    query_text: str,
    n_results: int = 5,
) -> dict[str, list[SearchResult]]:
    
    return {
        collection: query(collection, query_text, n_results=n_results)
        for collection in COLLECTIONS
    }

def collection_count(collection_name: str) -> int:
    return _get_collection(collection_name).count()