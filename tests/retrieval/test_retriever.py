from models import SearchResult
from retrieval import retriever
from retrieval.retriever import _rrf_fuse, retrieve, RRF_K
 
 
def _sr(rid, dist, layer="match"):
    return SearchResult(id=rid, text=rid, metadata={"layer": layer}, distance=dist)
 
 
def test_rrf_stamps_score_and_keeps_true_distance():
    fused = _rrf_fuse({"match_facts": [_sr("m1", 0.5)]})
    assert fused[0].metadata["rrf_score"] == 1.0 / (RRF_K + 1)
    assert fused[0].distance == 0.5  # true distance untouched
 
 
def test_rrf_interleaves_disjoint_lists_with_distance_tiebreak():
    per_collection = {
        "match_facts": [_sr("m1", 0.50), _sr("m2", 0.60)],
        "reactions": [_sr("r1", 0.40), _sr("r2", 0.55)],
        "career_history": [_sr("h1", 0.52)],
    }
    order = [r.id for r in _rrf_fuse(per_collection)]
    # rank-1s tie (1/61), broken by distance asc; then rank-2s (1/62)
    assert order == ["r1", "m1", "h1", "r2", "m2"]
 
 
def test_rrf_top3_spans_all_collections():
    per_collection = {
        "match_facts": [_sr("m1", 0.5), _sr("m2", 0.6)],
        "reactions": [_sr("r1", 0.5), _sr("r2", 0.6)],
        "career_history": [_sr("h1", 0.5), _sr("h2", 0.6)],
    }
    top3 = [r.id[0] for r in _rrf_fuse(per_collection)[:3]]
    assert set(top3) == {"m", "r", "h"}  # fair interleave, not one collection sweeping
 
 
def test_retrieve_returns_top_k_fused(monkeypatch):
    fake = {
        "match_facts": [_sr("m1", 0.50), _sr("m2", 0.70)],
        "reactions": [_sr("r1", 0.40)],
        "career_history": [_sr("h1", 0.55)],
    }
    monkeypatch.setattr(retriever.vector_store, "query_all_collections",
                        lambda q, n_results: fake)
    out = retrieve("any query", k=2)
    assert len(out) == 2
    assert [r.id for r in out] == ["r1", "m1"]  # rank-1s, distance tiebreak
    assert all("rrf_score" in r.metadata for r in out)
 
 
def test_retrieve_pool_depth_passed_through(monkeypatch):
    captured = {}
    def fake_query_all(q, n_results):
        captured["n"] = n_results
        return {"match_facts": [_sr("m1", 0.5)]}
    monkeypatch.setattr(retriever.vector_store, "query_all_collections", fake_query_all)
    retrieve("q", k=5, pool_per_collection=10)
    assert captured["n"] == 10