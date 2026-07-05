from __future__ import annotations

import ollama
import argparse


from datetime import datetime
from models import SearchResult
from retrieval.retriever import retrieve


DEFAULT_MODEL = "mistral-small3.2"
DEFAULT_K = 6
NUM_CTX = 16000
TEMPERATURE = 0.3

SYSTEM_PROMPT = (
    "You are a knowledgeable football writer covering the 2026 FIFA World Cup."
    "Using the numbered context passages below, write a clear, engaging answer that "
    "weaves together the match facts, press reaction, and historical background you are given. "
    "Cite the passage(s) behind every claim with bracketed numbers, e.g. [1] or [2][3].\n\n"
    "Stay strictly grounded in the context: do not add events, scores, quotes, or analysis "
    "that are not in the passages, and do not embellish with drama, momentum, or emotion the "
    "sources do not state. Draw only on the provided context, never on outside knowledge. "
    "If the context does not cover what is asked, say so plainly rather than guessing.\n\n"
    "Match your length to the question: a factual lookup deserves a crisp sentence or two; "
    "an open question about a team's campaign or history deserves a fuller narrative."
)

def _source_key(result: SearchResult) -> str:
    return result.id.split("#", 1)[0]

def build_context(results: list[SearchResult]) -> tuple[str, list[dict]]:
    order = []
    grouped = {}

    for r in results: 
        key = _source_key(r)
        if key not in grouped:
            order.append(key)
            grouped[key] = {"key": key, "meta": r.metadata, "texts": []}
        grouped[key]["texts"].append(r.text)

    sources = []
    lines = []

    for n, key in enumerate(order, start = 1):
        entry = grouped[key]
        entry["n"] = n
        sources.append(entry)
        lines.append(f"[{n}] {' '.join(entry['texts'])}")

    return "\n".join(lines), sources

def _fmt_date(iso: str | None) -> str:
    if not iso:
        return
    
    dt = datetime.fromisoformat(iso)
    return f"{dt.day} {dt.strftime('%b %Y')}"

def format_source_line(n: int, 
                       meta: dict) -> str: 
    if meta.get("layer") == "match":
        home, away = meta.get("home", "?"), meta.get("away", "?")
        date = _fmt_date(meta.get("utc_date"))
        tail = f", {date}" if date else ""
        return f"[{n}] Match record: {home} vs {away}{tail}"
 
    source = (meta.get("source") or "source").title()
    title = meta.get("title", "")
    url = meta.get("url")
    line = f'[{n}] {source} — "{title}"'
    if url:
        line += f" — {url}"
    return line

def format_sources(sources: list[dict]) -> str:
    body = "\n".join(format_source_line(s["n"], s["meta"]) for s in sources)
    return "Sources\n" + body

def build_messages(question: str, 
                   context: str) -> str:
    user = f"Context:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]

def _stream_chat(messages: list[dict], 
                model: str, 
                *, 
                stream: bool = True):
    try: 
        resp = ollama.chat(model=model,
                           messages=messages,
                           stream=stream,
                           options={"num_ctx":NUM_CTX, "temperature": TEMPERATURE},
                           )
        if stream:
            for chunk in resp:
                yield chunk.message.content
        else:
            yield resp.message.content
    except ollama.ResponseError as e:
        raise SystemExit(
            f"Ollama returned an error for model '{model}': {e}. "
            f"If it isn't pulled yet, run `ollama pull {model}`."
        )

def answer(question: str,
           *, 
           k: int = DEFAULT_K, 
           model: str = DEFAULT_MODEL,
           stream: bool = True,
           show_context = False) -> str:
    
    results = retrieve(question, k)
    
    if not results:
        print("No matching context found in the index.")
        return ""
    
    context, sources = build_context(results)
    messages = build_messages(question, context)

    if show_context:
        print("=== context fed to the model ===")
        print(context)
        print("=== end context ===\n")
    
    parts = []

    for token in _stream_chat(messages, model, stream=stream):
        parts.append(token)
        if stream:
            print(token, end="", flush = True)

    if stream:
        print()

    print("\n" + format_sources(sources))
    return "".join(parts)

def main():
    p = argparse.ArgumentParser(
        description="Ask a question about the 2026 FIFA World Cup."
    )
    p.add_argument("question")
    p.add_argument("--k", type=int, default=DEFAULT_K, help="passages to retrieve")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--no-stream", action="store_true", help="wait for the full answer")
    p.add_argument("--show-context", action="store_true",
                   help="print the numbered context fed to the model (for debugging grounding)")
    args = p.parse_args()
 
    answer(args.question, k=args.k, model=args.model, stream=not args.no_stream, show_context=args.show_context)


if __name__ == "__main__":
    main()

