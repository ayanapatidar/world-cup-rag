'''RRF acts as a scale-free, fair rank-interleave, it favors cross-layer diversity over letting one strong
collection dominate.'''

from store import vector_store
from models import SearchResult
 
RRF_K = 60  # standard RRF smoothing constant

def retrieve(query: str, k: int = 5, pool_per_collection: int = 10) -> list[SearchResult]:
    per_collection = vector_store.query_all_collections(query, n_results=pool_per_collection)
    fused = _rrf_fuse(per_collection)
    fused = _rerank(query, fused)
    return fused[:k]

def _rrf_fuse(per_collection: dict[str, list[SearchResult]]) -> list[SearchResult]:
    # Each passage scores 1/(RRF_K + rank) from its list
    # Rank is 1-indexed 

    scored = []
    for results in per_collection.values():
        for rank, result in enumerate(results, start=1):
            rrf = 1.0 / (RRF_K + rank)
            result.metadata["rrf_score"] = rrf
            scored.append((rrf, result.distance, result))
 
    scored.sort(key=lambda t: (-t[0], t[1]))  # rrf desc, then distance asc
    return [result for _, _, result in scored]

def _rerank(query: str, results: list[SearchResult]) -> list[SearchResult]:
    '''TODO(eval): add a cross-encoder (ms-marco-MiniLM-L-6-v2) that rescores
    each (query, passage) pair and re-sorts, once the eval harness can measure
    whether it beats the dense+RRF baseline.'''
    return results

