import json
from pathlib import Path
 
from retrieval.retriever import retrieve
from eval.fusions import minmax_fuse
from eval.scorer import evaluate
 
GOLD = Path(__file__).parent / "gold.jsonl"
KS = (5, 10)
STRATEGIES = {
    "RRF (baseline)": None,
    "min-max norm":   minmax_fuse,
}

def load_gold():
    items = [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]
    labeled = [g for g in items if g.get("expected")]
    unverified = [g for g in items if not g.get("verified", False)]
    return items, labeled, unverified

def _retrieve_fn(fuse):
    return lambda query, k: retrieve(query, k=k, pool_per_collection=max(KS), fuse=fuse)

def _row(label, cards):
    cells = "".join(
        f"{c.recall[5]:>7.2f}{c.recall[10]:>8.2f}{c.mrr:>7.2f}   " for c in cards
    )
    return f"  {label:<16}{cells}"

def main():
    items, labeled, unverified = load_gold()
    print(f"gold: {len(items)} queries, {len(labeled)} labeled, {len(unverified)} not yet verified")
    if unverified:
        print(f"{len(unverified)} entries have verified=false")
    if not labeled:
        print("\nNo labeled queries yet. Fill 'expected' in eval/gold.jsonl using eval/store_index.tsv.")
        return
 
    layers = sorted({g.get("layer", "?") for g in labeled})
    names = list(STRATEGIES)
 
    header = " " * 18 + "".join(f"{n:^25}" for n in names)
    subhdr = " " * 18 + ("   R@5    R@10    MRR   " * len(names))
    print("\n" + header)
    print(subhdr)
    print("  " + "-" * (16 + 25 * len(names)))
 
    # overall
    cards = [evaluate(labeled, _retrieve_fn(STRATEGIES[n]), KS) for n in names]
    print(_row(f"OVERALL (n={cards[0].n})", cards))
 
    # per layer
    for layer in layers:
        subset = [g for g in labeled if g.get("layer") == layer]
        cards = [evaluate(subset, _retrieve_fn(STRATEGIES[n]), KS) for n in names]
        print(_row(f"{layer} (n={cards[0].n})", cards))
 
    print("\nHigher is better for all three.")

if __name__ == "__main__":
    main()






