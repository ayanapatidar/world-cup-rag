"""
Alternative fusion strategies the eval compares against the retriever's RRF
baseline. 
"""

def minmax_fuse(per_collection: dict) -> list:
   # Magnitude-aware, unlike RRF

    scored = []

    for results in per_collection.values():
        
        if not results:
            continue

        dists = [r.distance for r in results]
        lo, hi = min(dists), max(dists)
        span = hi - lo

        for r in results:
            # lower distance = better; map to similarity in [0,1]
            sim = 1.0 if span == 0 else 1.0 - (r.distance - lo) / span
            r.metadata["norm_score"] = sim
            scored.append((sim, r.distance, r))
            
    scored.sort(key=lambda t: (-t[0], t[1]))  # similarity desc, distance asc tiebreak
    return [r for _, _, r in scored]
