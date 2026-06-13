"""
Want to make sure sentence_transformers lives here, don't want to import it more than once.
To swap embedding models, change _MODEL_NAME here.

Current model choice: multi-qa-MiniLM-L6-cos-v1
Small dimensions, tuned specifically for question-answer retrieval tasks. 

Might experiment with others later.
"""

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "multi-qa-MiniLM-L6-cos-v1"
_model: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model == None:
        print("[embedder] Loading!")
        _model = SentenceTransformer(_MODEL_NAME)
        print("[embedder] Done! :}")
    return _model

def embed(texts: list[str]) -> list[list[float]]:
    return _get_model().encode(texts, convert_to_numpy=True).tolist()

def embed_one(text: str) -> list[float]:
    return embed([text])[0]