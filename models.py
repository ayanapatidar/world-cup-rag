"""
models.py

Shared Pydantic models for the pipeline.
All data shapes that cross module boundaries are defined here.
"""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single result returned from a vector store query."""
    id: str
    text: str
    metadata: dict
    distance: float

class MatchStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    TIMED     = "TIMED"
    IN_PLAY   = "IN_PLAY"
    PAUSED    = "PAUSED"
    FINISHED  = "FINISHED"
    SUSPENDED = "SUSPENDED"   
    POSTPONED = "POSTPONED"  
    CANCELLED = "CANCELLED"  
    AWARDED   = "AWARDED"

class Team(BaseModel):
    id:   int
    name: str
    tla:  str 

class Score(BaseModel):
    winner:   str | None = None     # if pulling data from a scheduled match
    duration: str = "REGULAR"
    home:     int | None = None
    away:     int | None = None
    ht_home:  int | None = None
    ht_away:  int | None = None

class Match(BaseModel):
    id: int
    utc_date: datetime
    status: MatchStatus
    stage: str
    group: str | None = None
    home: Team
    away: Team
    score: Score
    last_updated: datetime
