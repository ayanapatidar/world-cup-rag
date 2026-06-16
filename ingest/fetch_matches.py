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
 
from models import Match, Score, Team


class FootballDataClient:
    BASE_URL = "https://api.football-data.org/v4"
    COMPETITION = "WC" 

    def __init__(
            self,
            api_key: str | None = None,
            cache_dir: Path = Path("data/raw"),
        ) -> None:
        api_key = api_key or os.environ.get("FOOTBALL_DATA_API_KEY")
        if not api_key:
            raise ValueError(
                "No football-data.org API key found. Set FOOTBALL_DATA_API_KEY in your .env (free key at football-data.org), or pass api_key=."
            )
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": api_key})
    
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_matches(self, *, refresh: bool = False, **filters: str) -> list[Match]:
        raw = self._get(
                f"/competitions/{self.COMPETITION}/matches",
                params=filters or None,
                cache_key="wc_matches" if not filters else None,
                refresh=refresh,
            )
        return [self._to_match(m) for m in raw["matches"]]

    def _get(
            self,
            path: str,
            params: dict | None = None,
            cache_key: str | None = None,
            refresh: bool = False,
        ) -> dict:
        cache_file = self.cache_dir / f"{cache_key}.json" if cache_key else None
    
        if cache_file and cache_file.exists() and not refresh:
            return json.loads(cache_file.read_text())
    
        raw = self._request(path, params)
    
        if cache_file:
            cache_file.write_text(json.dumps(raw, indent=2))
        return raw

    def _request(
            self, 
            path: str, 
            params: dict | None
        ) -> dict:
        resp = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()


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


