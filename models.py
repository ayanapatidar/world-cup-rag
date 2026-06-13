"""
models.py

Shared Pydantic models for the pipeline.
All data shapes that cross module boundaries are defined here.
"""


from pydantic import BaseModel

class SearchResult(BaseModel):
    """A single result returned from a vector store query."""
    id: str
    text: str
    metadata: dict
    distance: float