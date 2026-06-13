from store.embedder import embed, embed_one


def test_embed_returns_correct_count():
    """embed() should return one vector per input text."""
    texts = ["Mbappe scores in the final", "Argentina win the World Cup"]
    vecs = embed(texts)
    assert len(vecs) == 2


def test_embed_returns_correct_dimensions():
    """Vectors should be 384-dimensional (multi-qa-MiniLM-L6-cos-v1)."""
    vecs = embed(["test"])
    assert len(vecs[0]) == 384


def test_embed_one_returns_single_vector():
    """embed_one() should return a single vector, not a list of lists."""
    vec = embed_one("How did Messi perform?")
    assert isinstance(vec, list)
    assert isinstance(vec[0], float)


def test_different_texts_produce_different_vectors():
    """Different inputs should not produce identical embeddings."""
    vec1 = embed_one("Mbappe scores")
    vec2 = embed_one("Argentina wins")
    assert vec1 != vec2


def test_similar_texts_produce_similar_vectors():
    """Semantically similar texts should be closer than unrelated ones."""
    import math

    def cosine_similarity(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x ** 2 for x in a))
        mag_b = math.sqrt(sum(x ** 2 for x in b))
        return dot / (mag_a * mag_b)

    similar1 = embed_one("Mbappe scored a goal")
    similar2 = embed_one("Mbappe found the net")
    unrelated = embed_one("The stock market crashed")

    sim_close = cosine_similarity(similar1, similar2)
    sim_far = cosine_similarity(similar1, unrelated)

    assert sim_close > sim_far