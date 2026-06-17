"""
Wikipedia and JSON client for historical context data.
 
Only this file changes if we swap providers(hence the mapping layer at the bottom).

SHOTOUT WIKIPEDIA! I LOVE OPEN SOURCE INFORMATION YAY
"""
import json
from pathlib import Path
 
from pydantic import ValidationError
 
from ingest.base_client import CachedJSONClient
from models import HistoryDoc
 
WIKI_ARTICLE_BASE = "https://en.wikipedia.org/wiki/"

class WikipediaClient(CachedJSONClient):
    BASE_URL = "https://en.wikipedia.org"
    USER_AGENT = "WorldCupRAG/0.1 (personal project, https://github.com/ayanapatidar/world-cup-rag)"
    
    def __init__(
            self, 
            cache_dir: Path = Path("data/raw")
            ) -> None:
        super().__init__(cache_dir)  
        self.session.headers.update({"User-Agent": self.USER_AGENT})
    
    def fetch_extracts(
        self, 
        titles: list[str], 
        *, 
        refresh: bool = False
    ) -> list[HistoryDoc]:
        # choosing to use a list of pre-defined titles because we already know the teams and the 
        # tournament that is relevant
        docs = []
        for title in titles:
            doc = self._fetch_one(title, refresh=refresh)
            if doc is not None:
                docs.append(doc)
        return docs
    
    def _fetch_one(
            self,
            title: str,
            *,
            refresh: bool
    ) -> HistoryDoc | None:
        
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,     # query.pages is a clean LIST, not a pageid-keyed dict
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "redirects": 1,
            "titles": title,
        }

        raw = self._get(
            "/w/api.php",
            params=params,
            cache_key=f"wikipedia_{self._slug(title)}",
            refresh=refresh,
        )

        pages = raw["query"]["pages"]
        return self._to_doc(pages[0]) if pages else None
    
    @staticmethod
    def _to_doc(page: dict) -> HistoryDoc | None:
        if page.get("missing") or not page.get("extract"):
            return None
        title = page["title"]
        
        return HistoryDoc(
            id=str(page["pageid"]),
            source="wikipedia",
            title=title,
            body=page["extract"],
            url=WIKI_ARTICLE_BASE + title.replace(" ", "_"),
        )
    
    @staticmethod
    def _slug(title: str) -> str:
        # they're apparently called slugs because of newspaper publishing
        # and not because slugs are smooth and unproblematic like i initially thought
        # :(
        return title.replace(" ", "_").replace("/", "_")

def load_history_docs(
    path: Path = Path("data/history_docs.jsonl"),
) -> list[HistoryDoc]:
    # pulling from hand curated docs. not complete of course!
    # hashtag mytakes
    docs = []
    for n, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            data["source"] = "curated"
            doc = HistoryDoc(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"{path} line {n}: {e}") from e
        docs.append(doc)
    return docs

