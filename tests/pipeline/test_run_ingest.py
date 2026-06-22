from models import Match, Score, Team, Scorer, Article, HistoryDoc
from pipeline.run_ingest import (
    build_wikipedia_titles,
    team_to_title,
    TEAM_TITLE_OVERRIDES,
    TOURNAMENT_TITLE,
    RIVALRY_TITLES,
    _clean_meta, 
    _match_docs, 
    _article_docs, 
    _history_docs
)
 
 
def _match(home_id, home_name, away_id, away_name):
    return Match(
        id=1,
        utc_date="2026-06-11T16:00:00Z",
        status="SCHEDULED",
        stage="GROUP_STAGE",
        home=Team(id=home_id, name=home_name),
        away=Team(id=away_id, name=away_name),
        score=Score(),
        last_updated="2026-06-11T16:00:00Z",
    )
 
 
def test_team_to_title_default_suffix():
    assert team_to_title("South Korea") == "South Korea national football team"
    assert team_to_title("Brazil") == "Brazil national football team"
 
 
def test_team_to_title_override_wins(monkeypatch):
    monkeypatch.setitem(
        TEAM_TITLE_OVERRIDES,
        "United States",
        "United States men's national soccer team",
    )
    assert team_to_title("United States") == "United States men's national soccer team"
 
 
def test_titles_include_all_four_sources():
    matches = [_match(1, "Argentina", 2, "Brazil")]
    scorers = [Scorer(player_id=10, name="Lionel Messi", goals=3, team_name="Argentina")]
    titles = build_wikipedia_titles(matches, scorers)
    assert TOURNAMENT_TITLE in titles                      
    assert all(r in titles for r in RIVALRY_TITLES)        
    assert "Argentina national football team" in titles     
    assert "Brazil national football team" in titles        
    assert "Lionel Messi" in titles   
 
 
def test_undetermined_teams_skipped():
    matches = [_match(None, None, None, None)] 
    titles = build_wikipedia_titles(matches, [])
    assert not any("national football team" in t for t in titles)
 
 
def test_dedupe_is_order_preserving():
    matches = [
        _match(1, "Brazil", 2, "Argentina"),
        _match(1, "Brazil", 3, "Chile"), 
    ]
    titles = build_wikipedia_titles(matches, [])
    assert titles.count("Brazil national football team") == 1
    assert titles[0] == TOURNAMENT_TITLE 
 

def _WC(t: str) -> int:
    return len(t.split())

 
def _det_match(mid=1, group=None, status="FINISHED"):
    return Match(id=mid, utc_date="2026-06-11T16:00:00Z", status=status, stage="GROUP_STAGE",
                 group=group, home=Team(id=10, name="Argentina"), away=Team(id=11, name="Brazil"),
                 score=Score(winner="HOME_TEAM", home=2, away=0),
                 last_updated="2026-06-11T18:00:00Z")
 
 
def _undet_match(mid=2):
    return Match(id=mid, utc_date="2026-07-04T16:00:00Z", status="TIMED", stage="LAST_32",
                 group=None, home=Team(), away=Team(), score=Score(),
                 last_updated="2026-07-04T16:00:00Z")
 
 
def _article(aid="g1", atype="matchreport", body="Short report.", byline=None):
    return Article(id=aid, match_id=1, title="Report", body=body, byline=byline,
                   article_type=atype, url="https://g/x", published="2026-06-11T20:00:00Z")
 
 
def test_clean_meta_drops_none():
    assert _clean_meta({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}
 
 
def test_match_docs_skips_undetermined_and_builds_id():
    ids, texts, metas = _match_docs([_det_match(mid=1), _undet_match(mid=2)])
    assert ids == ["match-1"]
    assert metas[0]["match_id"] == 1 and metas[0]["home"] == "Argentina"
    assert all(v is not None for m in metas for v in m.values())
 
 
def test_match_docs_drops_none_group():
    _, _, metas = _match_docs([_det_match(group=None)])
    assert "group" not in metas[0]
 
 
def test_article_docs_drops_minutebyminute():
    ids, _, _ = _article_docs([_article("g1", "matchreport"), _article("g2", "minutebyminute")],
                              max_tokens=512, token_len=_WC)
    assert ids == ["g1#0"]
 
 
def test_article_docs_meta_and_none_drop():
    _, _, metas = _article_docs([_article("g1", byline="A. Writer")], max_tokens=512, token_len=_WC)
    assert metas[0]["match_id"] == 1 and metas[0]["url"] == "https://g/x"
    assert metas[0]["byline"] == "A. Writer"
    _, _, m2 = _article_docs([_article("g2")], max_tokens=512, token_len=_WC)
    assert "byline" not in m2[0]  # None dropped
 
 
def test_article_docs_long_body_splits_into_numbered_chunks():
    body = " ".join(f"Sentence {i} with filler words here now." for i in range(60))
    ids, _, _ = _article_docs([_article(body=body)], max_tokens=30, token_len=_WC)
    assert ids[0] == "g1#0" and ids[1] == "g1#1" and len(ids) > 2
 
 
def test_history_docs_ids_and_none_url_dropped():
    docs = [
        HistoryDoc(id="44", source="wikipedia", title="Lionel Messi", body="Footballer.",
                   url="https://en.wikipedia.org/wiki/Lionel_Messi"),
        HistoryDoc(id="curated-1", source="curated", title="X", body="Y.", url=None),
    ]
    ids, _, metas = _history_docs(docs, max_tokens=512, token_len=_WC)
    assert ids == ["44#0", "curated-1#0"]
    assert metas[0]["source"] == "wikipedia"
    assert "url" not in metas[1]

def test_article_docs_dedups_same_id_across_matches():
    a1 = _article("football/2026/jun/13/roundup")
    a2 = _article("football/2026/jun/13/roundup")  # same id, e.g. stamped match_id 2 elsewhere
    ids, _, _ = _article_docs([a1, a2], max_tokens=512, token_len=_WC)
    assert ids == ["football/2026/jun/13/roundup#0"]
 
 
def test_history_docs_dedups_same_id():
    d = HistoryDoc(id="44", source="wikipedia", title="Lionel Messi", body="Footballer.", url=None)
    ids, _, _ = _history_docs([d, d], max_tokens=512, token_len=_WC)
    assert ids == ["44#0"]
