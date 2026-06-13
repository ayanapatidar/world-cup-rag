"""
tests/store/test_vector_store.py

Tests for store/vector_store.py.

Note: these tests write to a temporary ChromaDB instance so they don't
pollute the real data/ directory.
"""

import pytest
from unittest.mock import patch
from models import SearchResult
from store.vector_store import (
    upsert_documents,
    query,
    query_all_collections,
    collection_count,
    COLLECTIONS,
)


@pytest.fixture(autouse=True)
def tmp_chroma(tmp_path):
    """
    Redirect ChromaDB to a temporary directory for every test.
    Ensures tests are isolated and don't touch real data.
    """
    with patch("store.vector_store.DATA_DIR", str(tmp_path)):
        with patch("store.vector_store._client", None):
            yield


# COLLECTIONS constant

def test_collections_contains_expected_names():
    assert "match_facts" in COLLECTIONS
    assert "reactions" in COLLECTIONS
    assert "career_history" in COLLECTIONS


# upsert_documents

def test_upsert_invalid_collection_raises():
    with pytest.raises(ValueError, match="Unknown collection"):
        upsert_documents("nonexistent", ["id1"], ["text"], [{}])


def test_upsert_and_count():
    upsert_documents(
        "match_facts",
        ids=["doc1", "doc2"],
        texts=["France beat Brazil 2-0", "Mbappe scored twice"],
        metadatas=[{"match_id": "1"}, {"match_id": "1"}],
    )
    assert collection_count("match_facts") == 2


def test_upsert_is_idempotent():
    """Upserting the same id twice should not create duplicates."""
    for _ in range(2):
        upsert_documents(
            "match_facts",
            ids=["doc1"],
            texts=["France beat Brazil 2-0"],
            metadatas=[{"match_id": "1"}],
        )
    assert collection_count("match_facts") == 1


# query


def test_query_invalid_collection_raises():
    with pytest.raises(ValueError, match="Unknown collection"):
        query("nonexistent", "some query")


def test_query_returns_search_results():
    upsert_documents(
        "match_facts",
        ids=["doc1", "doc2", "doc3"],
        texts=[
            "France beat Brazil 2-0 in the quarter final",
            "Mbappe scored twice against Brazil",
            "The referee showed three yellow cards",
        ],
        metadatas=[{"match_id": "1"}, {"match_id": "1"}, {"match_id": "1"}],
    )
    results = query("match_facts", "who scored the goals?")
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


def test_query_results_have_correct_fields():
    upsert_documents(
        "match_facts",
        ids=["doc1"],
        texts=["France beat Brazil 2-0"],
        metadatas=[{"match_id": "1"}],
    )
    results = query("match_facts", "France Brazil")
    result = results[0]
    assert isinstance(result.id, str)
    assert isinstance(result.text, str)
    assert isinstance(result.metadata, dict)
    assert isinstance(result.distance, float)


def test_query_respects_n_results():
    upsert_documents(
        "match_facts",
        ids=["doc1", "doc2", "doc3"],
        texts=[
            "France beat Brazil 2-0",
            "Mbappe scored twice",
            "Griezmann added a third",
        ],
        metadatas=[{"match_id": "1"}, {"match_id": "1"}, {"match_id": "1"}],
    )
    results = query("match_facts", "goals", n_results=2)
    assert len(results) <= 2


def test_query_results_ordered_by_distance():
    upsert_documents(
        "match_facts",
        ids=["doc1", "doc2"],
        texts=[
            "Mbappe scored a brilliant goal in the final",
            "The weather in Paris was cloudy",
        ],
        metadatas=[{"match_id": "1"}, {"match_id": "1"}],
    )
    results = query("match_facts", "Mbappe goal", n_results=2)
    assert results[0].distance <= results[1].distance


# query_all_collections

def test_query_all_collections_returns_all_keys():
    results = query_all_collections("Mbappe goal")
    assert set(results.keys()) == set(COLLECTIONS)


def test_search_result_serializes_to_json():
    """Pydantic model should serialize cleanly — no extra steps needed."""
    result = SearchResult(
        id="doc1",
        text="France beat Brazil",
        metadata={"match_id": "1"},
        distance=0.42,
    )
    as_dict = result.model_dump()
    assert as_dict["id"] == "doc1"
    assert as_dict["distance"] == 0.42