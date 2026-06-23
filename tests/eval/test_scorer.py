from types import SimpleNamespace as NS
 
from eval.scorer import source_id, evaluate, _evaluate_query
 
 
def _r(rid):
    return NS(id=rid)
 
 
def test_source_id_strips_chunk_suffix():
    assert source_id("44#2") == "44"
    assert source_id("football/2026/jun/14/report#1") == "football/2026/jun/14/report"
    assert source_id("match-12") == "match-12"
 
 
def test_recall_and_rr_single_answer():
    # expected '44' appears at chunk rank 2
    recalls, rr = _evaluate_query({"44"}, ["99", "44", "12"], ks=(1, 5))
    assert recalls[1] == 0.0 
    assert recalls[5] == 1.0
    assert rr == 0.5
 
 
def test_recall_multi_answer_is_fraction():
    recalls, rr = _evaluate_query({"a", "b", "c"}, ["a", "x", "b", "y", "z"], ks=(5,))
    assert recalls[5] == 2 / 3
    assert rr == 1.0
 
 
def test_miss_scores_zero():
    recalls, rr = _evaluate_query({"a"}, ["x", "y", "z"], ks=(5,))
    assert recalls[5] == 0.0
    assert rr == 0.0
 
 
def test_evaluate_aggregates_and_skips_unlabeled():
    gold = [
        {"query": "q1", "expected": ["44"]},
        {"query": "q2", "expected": []},
        {"query": "q3", "expected": ["match-1"]},
    ]
    canned = {
        "q1": [_r("44#0"), _r("99#1")],
        "q3": [_r("7#0"), _r("8#0"), _r("match-1")],
    }
    card = evaluate(gold, lambda query, k: canned[query], ks=(5,))
    assert card.n == 2
    assert card.recall[5] == 1.0
    assert card.mrr == (1.0 + 1 / 3) / 2
 
 
def test_chunk_sources_use_topk_chunks_not_unique_sources():
    recalls, _ = _evaluate_query({"A", "B"}, ["A", "A", "B"], ks=(2,))
    assert recalls[2] == 0.5




