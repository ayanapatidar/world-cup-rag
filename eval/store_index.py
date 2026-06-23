from pathlib import Path
from store import vector_store
 
OUT = Path(__file__).parent / "store_index.tsv"

def _label(layer: str, meta: dict) -> str:

    if layer == "match":
        return f"{meta.get('home')} vs {meta.get('away')} ({meta.get('stage')}, {meta.get('utc_date', '')[:10]})"
    
    return meta.get("title", "")

def source_index() -> dict[str, tuple[str, str]]:
    index = {}

    for collection in vector_store.COLLECTIONS:
        data = vector_store.list_documents(collection)

        for chunk_id, meta in zip(data["ids"], data["metadatas"]):
            source_id = chunk_id.rsplit("#", 1)[0]

            if source_id not in index:
                index[source_id] = (meta.get("layer", collection), _label(meta.get("layer", ""), meta))

    return index

def main() -> None:
    index = source_index()
    rows = sorted(index.items(), key=lambda kv: (kv[1][0], kv[1][1]))

    with OUT.open("w") as f:
        f.write("source_id\tlayer\tlabel\n")
        for source_id, (layer, label) in rows:
            f.write(f"{source_id}\t{layer}\t{label}\n")

    by_layer = {}

    for _, (layer, _label_) in index.items():
        by_layer[layer] = by_layer.get(layer, 0) + 1

    print(f"wrote {len(index)} source docs to {OUT}")
    print("by layer:", by_layer)
 
if __name__ == "__main__":
    main()