""" 
Source-doc-level retrieval metrics: Recall@k and MRR over a gold set.
"""

from dataclasses import dataclass
 
 
def source_id(chunk_id: str) -> str:
    return chunk_id.rsplit("#", 1)[0]

@dataclass
class Scorecard:
    recall: dict[int, float]
    mrr: float
    n: int 

def _evaluate_query(
        expected: set[str], 
        chunk_sources: list[str], 
        ks) -> tuple[dict[int, float], float]:
    recalls = {}
    for k in ks:
        topk = set(chunk_sources[:k])
        recalls[k] = len(expected & topk) / len(expected)
    rr = 0.0
    for rank, sid in enumerate(chunk_sources, start=1):
        if sid in expected:
            rr = 1.0 / rank
            break
    return recalls, rr

def evaluate(
        gold, 
        retrieve_fn, 
        ks=(5, 10)) -> Scorecard:
    maxk = max(ks)
    recalls = {k: [] for k in ks}
    rrs = []
    for item in gold:
        expected = set(item.get("expected") or [])
        if not expected:
            continue  # not yet labeled
        results = retrieve_fn(item["query"], maxk)
        chunk_sources = [source_id(r.id) for r in results]
        q_recalls, rr = _evaluate_query(expected, chunk_sources, ks)
        for k in ks:
            recalls[k].append(q_recalls[k])
        rrs.append(rr)
    n = len(rrs)
    return Scorecard(
        recall={k: (sum(v) / len(v) if v else 0.0) for k, v in recalls.items()},
        mrr=(sum(rrs) / len(rrs) if rrs else 0.0),
        n=n,
    )