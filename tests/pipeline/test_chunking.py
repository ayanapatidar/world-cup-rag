from pipeline.chunking import chunk


def WC(t: str) -> int:
    return len(t.split())


def _body(n: int, words: int = 5) -> str:
    """n sentences of `words` words each, period-terminated."""
    return " ".join(
        " ".join(f"w{i}_{j}" for j in range(words - 1)) + "." for i in range(n)
    )


def test_short_text_single_chunk_with_header():
    out = chunk("Argentina beat Brazil 3-1.", header="Match", max_tokens=512, token_len=WC)
    assert out == ["Match\n\nArgentina beat Brazil 3-1."]


def test_no_header_no_prefix():
    out = chunk("Argentina beat Brazil 3-1.", max_tokens=512, token_len=WC)
    assert out == ["Argentina beat Brazil 3-1."]


def test_long_body_splits_into_multiple_chunks():
    out = chunk(_body(20), header="T", max_tokens=30, token_len=WC)
    assert len(out) > 1


def test_every_chunk_carries_header():
    out = chunk(_body(20), header="Lionel Messi", max_tokens=30, token_len=WC)
    assert all(c.startswith("Lionel Messi\n\n") for c in out)


def test_each_chunk_within_budget():
    out = chunk(_body(20), header="T", max_tokens=30, token_len=WC, overlap_sentences=1)
    for c in out:
        body_part = c.split("\n\n", 1)[1]
        assert WC(body_part) <= 25


def test_overlap_bridges_boundaries():
    out = chunk(_body(20), header="T", max_tokens=30, token_len=WC, overlap_sentences=1)
    bodies = [c.split("\n\n", 1)[1] for c in out]
    for prev, nxt in zip(bodies, bodies[1:]):
        assert prev.split(". ")[-1].rstrip(".") == nxt.split(". ")[0].rstrip(".")


def test_zero_overlap_yields_fewer_or_equal_chunks():
    with_overlap = chunk(_body(20), header="T", max_tokens=30, token_len=WC, overlap_sentences=1)
    no_overlap = chunk(_body(20), header="T", max_tokens=30, token_len=WC, overlap_sentences=0)
    assert len(no_overlap) <= len(with_overlap)