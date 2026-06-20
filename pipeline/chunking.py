import re
 
from store import embedder

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_SPECIAL_TOKEN_MARGIN = 4
 
 
def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_RE.split(text.strip()) if s]

def chunk(
    body: str,
    *,
    header: str = "",
    max_tokens: int | None = None,
    token_len=None,
    overlap_sentences: int = 1,
) -> list[str]:
    
    if max_tokens is None:
        max_tokens = embedder.max_tokens()
    if token_len is None:
        token_len = embedder.token_len
 
    budget = max_tokens - _SPECIAL_TOKEN_MARGIN
    prefix = f"{header}\n\n" if header else ""
 
    if token_len(prefix + body) <= budget:
        return [prefix + body]
 
    body_budget = budget - token_len(prefix)
    chunks: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for sent in _sentences(body):
        st = token_len(sent)
        if cur and cur_tokens + st > body_budget:
            chunks.append(prefix + " ".join(cur))
            cur = cur[-overlap_sentences:] if overlap_sentences else []
            cur_tokens = sum(token_len(s) for s in cur)
        cur.append(sent)
        cur_tokens += st
    if cur:
        chunks.append(prefix + " ".join(cur))
    return chunks
