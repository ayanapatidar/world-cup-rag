from models import Match, Scorer, HistoryDoc, Article
from ingest.fetch_matches import FootballDataClient
from ingest.fetch_history import WikipediaClient, load_history_docs
from ingest.fetch_reactions import GuardianClient
from pipeline.passages import match_to_text
from pipeline.chunking import chunk
from store import vector_store

TOURNAMENT_TITLE = "2026 FIFA World Cup"

# Wikipedia rivalry titles use an en-dash (–), not a hyphen (-) !!!

RIVALRY_TITLES = [
    "Argentina–Brazil football rivalry",
    "Mexico–United States soccer rivalry",
    "England–Scotland football rivalry",
    "Germany–Netherlands football rivalry",
    "England–Germany football rivalry",
    "Argentina–Netherlands football rivalry",
    "Brazil–Uruguay football rivalry",
    "Japan–South Korea football rivalry",
    "Canada–United States soccer rivalry",
    "France–Germany football rivalry",
    "Argentina–Uruguay football rivalry",
    "France–Spain football rivalry",
    "Egypt–Tunisia football rivalry",
    "Australia–Japan football rivalry",
    "Australia–South Korea football rivalry",
    "Argentina–England football rivalry",
]

TEAM_TITLE_OVERRIDES: dict[str, str] = {
    "United States": "United States men's national soccer team",
    "Canada":        "Canada men's national soccer team",
}

SCORER_TITLE_OVERRIDES: dict[str, str] = {
    "In-beom Hwang": "Hwang In-beom",
    "Hyun-Gyu Oh":   "Oh Hyeon-gyu",
    "Abdulelah Al Amri": "Abdulelah Al-Amri",
    "Ibrahim M'Baye":    "Ibrahim Mbaye",
    "Ladislav Krejčí": "Ladislav Krejčí (footballer, born 1999)",
    "Nathaniel Brown": "Nathaniel Brown (footballer)",
}

def team_to_title(team_name: str) -> str:
    return TEAM_TITLE_OVERRIDES.get(
        team_name, f"{team_name} national football team"
    )

def scorer_to_title(name: str) -> str:
    return SCORER_TITLE_OVERRIDES.get(name, name)

def build_wikipedia_titles(
        matches: list[Match], 
        scorers: list[Scorer]
        ) -> list[str]:
    titles = [TOURNAMENT_TITLE, *RIVALRY_TITLES]
 
    for m in matches:
        for team in (m.home, m.away):
            if team.id is not None and team.name:
                titles.append(team_to_title(team.name))
 
    for s in scorers:
        titles.append(scorer_to_title(s.name))
 
    return list(dict.fromkeys(titles))

def fetch_wikipedia_history(refresh: bool = False) -> list[HistoryDoc]:
    fb = FootballDataClient()
    wiki = WikipediaClient()
    matches = fb.get_matches(refresh=refresh)
    scorers = fb.get_scorers(refresh=refresh)
    titles = build_wikipedia_titles(matches, scorers)
    return wiki.fetch_extracts(titles, refresh=refresh)

# new stuff here

MATCH_COLLECTION = "match_facts"
REACTION_COLLECTION = "reactions"
HISTORY_COLLECTION = "career_history"

def _clean_meta(meta: dict) -> dict:
    # chromaDB likes non-empty and scalar-only metadata
    return {k: v for k, v in meta.items() if v is not None}

def _match_docs(matches: list[Match]) -> tuple[list[str], list[str], list[dict]]:
    ids, texts, metas = [], [], []
    
    for m in matches:
        if m.home.id is None or m.away.id is None:
            continue
        
        ids.append(f"match-{m.id}")
        texts.append(match_to_text(m))
        metas.append(_clean_meta({
            "layer": "match",
            "match_id": m.id,
            "stage": m.stage,
            "group": m.group,
            "status": m.status.value,
            "utc_date": m.utc_date.isoformat(),
            "home": m.home.name,
            "away": m.away.name,
        }))
    return ids, texts, metas

def _article_docs(articles: list[Article], *, max_tokens=None, token_len=None) -> tuple[list[str], list[str], list[dict]]:
    ids, texts, metas = [], [], []
    seen = set()

    for a in articles:
        if a.article_type == "minutebyminute":
            continue
        if a.id in seen:
            continue

        seen.add(a.id)
        chunks = chunk(a.body, header=a.title, max_tokens=max_tokens, token_len=token_len)

        for i, text in enumerate(chunks):
            ids.append(f"{a.id}#{i}")
            texts.append(text)
            metas.append(_clean_meta({
                "layer": "reaction",
                "match_id": a.match_id,
                "source": a.source,
                "title": a.title,
                "byline": a.byline,
                "article_type": a.article_type,
                "url": a.url,
                "published": a.published.isoformat(),
                "chunk": i,
            }))

    return ids, texts, metas

def _history_docs(docs: list[HistoryDoc], *, max_tokens=None, token_len=None) -> tuple[list[str], list[str], list[dict]]:
    ids, texts, metas = [], [], []
    seen = set()

    for d in docs:
        
        if d.id in seen:
            continue

        seen.add(d.id)
        chunks = chunk(d.body, header=d.title, max_tokens=max_tokens, token_len=token_len)

        for i, text in enumerate(chunks):
            ids.append(f"{d.id}#{i}")
            texts.append(text)
            metas.append(_clean_meta({
                "layer": "history",
                "source": d.source,
                "title": d.title,
                "url": d.url,
                "chunk": i,
            }))

    return ids, texts, metas

def ingest_matches(matches: list[Match]) -> int:
    ids, texts, metas = _match_docs(matches)

    if ids:
        vector_store.upsert_documents(MATCH_COLLECTION, ids, texts, metas)

    return len(ids)

def ingest_reactions(matches: list[Match], guardian: GuardianClient, *, refresh: bool = False) -> int:
    
    played = [
        m for m in matches
        if m.status.value in {"FINISHED", "AWARDED"}
        and m.home.id is not None and m.away.id is not None
    ]

    articles = []

    for m in played:
        articles.extend(guardian.get_match_reactions(m, refresh=refresh))

    ids, texts, metas = _article_docs(articles)

    if ids:
        vector_store.upsert_documents(REACTION_COLLECTION, ids, texts, metas)
    
    return len(ids)

def ingest_history(*, refresh: bool = False) -> int:
    docs = fetch_wikipedia_history(refresh=refresh) + load_history_docs()
    ids, texts, metas = _history_docs(docs)

    if ids:
        vector_store.upsert_documents(HISTORY_COLLECTION, ids, texts, metas)

    return len(ids)

def ingest_all(*, refresh: bool = False, rebuild: bool = False) -> dict[str, int]:
    
    # Upsert is idempotent on id, so re-running refreshes in place

    if rebuild:
        vector_store.reset_collections()

    fb = FootballDataClient()
    guardian = GuardianClient()
    matches = fb.get_matches(refresh=refresh)

    counts = {
        MATCH_COLLECTION: ingest_matches(matches),
        REACTION_COLLECTION: ingest_reactions(matches, guardian, refresh=refresh),
        HISTORY_COLLECTION: ingest_history(refresh=refresh),
    }

    print(f"[run_ingest] upserted {counts}")
    return counts

if __name__ == "__main__":
    import argparse
 
    parser = argparse.ArgumentParser(description="Ingest WC data into the vector store.")
    parser.add_argument("--refresh", action="store_true",
                        help="bypass the raw cache and refetch from the APIs")
    parser.add_argument("--rebuild", action="store_true",
                        help="drop and recreate the collections before ingesting")
    ingest_all(refresh=parser.parse_args().refresh, rebuild=parser.parse_args().rebuild)
