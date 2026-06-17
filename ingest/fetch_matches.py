"""
football-data.org API client for World Cup match data.
 
This module is the ONLY place that knows about football-data.org's format. 
Everything downstream depends on `Match`, not on the API.
Only this file changes if we swap providers(hence the mapping layer at the bottom).
"""

import json
import os
from pathlib import Path
 
import requests
 
from models import Match, Score, Team, Scorer
from ingest.base_client import CachedJSONClient


class FootballDataClient(CachedJSONClient):
    BASE_URL = "https://api.football-data.org/v4"
    COMPETITION = "WC" 

    def __init__(
            self,
            api_key: str | None = None,
            cache_dir: Path = Path("data/raw"),
        ) -> None:
        super().__init__(cache_dir)
        api_key = api_key or os.environ.get("FOOTBALL_DATA_API_KEY")
        if not api_key:
            raise ValueError(
                "No football-data.org API key found. Set FOOTBALL_DATA_API_KEY in your .env (free key at football-data.org), or pass api_key=."
            )
        self.session.headers.update({"X-Auth-Token": api_key})

    def get_matches(self, *, refresh: bool = False, **filters: str) -> list[Match]:
        raw = self._get(
                f"/competitions/{self.COMPETITION}/matches",
                params=filters or None,
                cache_key="wc_matches" if not filters else None,
                refresh=refresh,
            )
        return [self._to_match(m) for m in raw["matches"]]
    
    def get_scorers(self, limit: int = 200, refresh: bool = False) -> list[Scorer]:
        raw = self._get(
            f"/competitions/{self.COMPETITION}/scorers",
            params={"limit": limit},
            cache_key="wc_scorers",
            refresh=refresh,
        )
        return [self._to_scorer(s) for s in raw["scorers"]]


    @staticmethod
    def _to_match(raw: dict) -> Match:
        score = raw["score"]
        full = score.get("fullTime") or {}
        half = score.get("halfTime") or {}
        return Match(
            id=raw["id"],
            utc_date=raw["utcDate"],
            status=raw["status"],
            stage=raw["stage"],
            group=raw.get("group"),
            home=FootballDataClient._to_team(raw["homeTeam"]),
            away=FootballDataClient._to_team(raw["awayTeam"]),
            score=Score(
                winner=score.get("winner"),
                duration=score.get("duration", "REGULAR"),
                home=full.get("home"),
                away=full.get("away"),
                ht_home=half.get("home"),
                ht_away=half.get("away"),
            ),
            last_updated=raw["lastUpdated"],
        )

    @staticmethod
    def _to_team(raw: dict) -> Team:
        return Team(id=raw["id"], name=raw["name"], tla=raw.get("tla"))
    
    @staticmethod
    def _to_scorer(raw: dict) -> Scorer:
        player = raw["player"]
        team = raw.get("team")
        return Scorer(
            player_id=player["id"],
            name=player["name"],
            team_name=team["name"],
            goals=raw["goals"],
        )



