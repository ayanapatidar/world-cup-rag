"""
Guardian Open Platform client for World Cup match reactions.
 
Similar to fetch-matches.py.
Only this file changes if we swap providers(hence the mapping layer at the bottom).

Shoutout to the Guardian Open Platform, seriously. I thought I was going to have to scrape so many websites
but the API actually gives us plain-text article bodies (`bodyText`), so we don't even need HTML parsing.
"""

import json
import os
from pathlib import Path
from datetime import timedelta

import requests

from ingest.base_client import CachedJSONClient
from models import Article, Match

class GuardianClient(CachedJSONClient):
    BASE_URL = "https://content.guardianapis.com"
    SECTION = "football"
 
    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path = Path("data/raw"),
    ) -> None:
        super().__init__(cache_dir)
        api_key = api_key or os.environ.get("GUARDIAN_API_KEY")
        if not api_key:
            raise ValueError(
                "No Guardian API key found. Set GUARDIAN_API_KEY in your .env "
                "(free key at open-platform.theguardian.com), or pass api_key=."
            )
        self.session.params = {"api-key": api_key}
 
    def get_match_reactions(
        self,
        match: Match,
        *,
        page_size: int = 20,
        window_days: int = 3,
        refresh: bool = False,
    ) -> list[Article]:
        
        '''
        we search the football section for pieces mentioning BOTH teams within a
        few days of kickoff to catch the match report plus the next-day ratings and 
        analysis. Every result is stamped with `match.id`, which is what links a 
        reaction back to its game.
        some tunable things here:
            - `page_size` (how many articles), 
            - `window_days` (how long after kickoff to keep looking)
        also, if recall is poor, the team-name `AND` below could be loosened.
        '''
        
        from_date = match.utc_date.date()
        to_date = from_date + timedelta(days=window_days)
        params = {
            "q": f'"{match.home.name}" AND "{match.away.name}"',
            "section": self.SECTION,
            "from-date": from_date.isoformat(),
            "to-date": to_date.isoformat(),
            "show-fields": "byline,bodyText",
            "show-tags": "tone",
            "page-size": page_size,
            "order-by": "relevance"
        }

        raw = self._get(
            "/search",
            params=params,
            cache_key=f"guardian_{match.id}",
            refresh=refresh,
        )

        articles = []
        for result in raw["response"]["results"]:
            article = self._to_article(result, match.id)
            if article is not None:  
                articles.append(article)
        return articles
    
    @staticmethod
    def _to_article(raw: dict, match_id: int) -> Article | None:
        fields = raw.get("fields") or {}
        body = fields.get("bodyText")
        if not body:  # video pages with no usable reaction text
            return None
        return Article(
            id=raw["id"],
            match_id=match_id,  
            title=raw["webTitle"],
            body=body,
            byline=fields.get("byline"),
            article_type=GuardianClient._tone(raw.get("tags") or []),
            url=raw["webUrl"],
            published=raw["webPublicationDate"],
        )
    
    @staticmethod
    def _tone(tags: list[dict]) -> str | None:
        for tag in tags:
            if tag.get("type") == "tone":
                return tag["id"].split("/", 1)[-1]
        return None


