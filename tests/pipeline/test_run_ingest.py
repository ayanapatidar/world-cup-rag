from models import Match, Score, Team, Scorer
from pipeline import run_ingest
from pipeline.run_ingest import (
    build_wikipedia_titles,
    team_to_title,
    TOURNAMENT_TITLE,
    RIVALRY_TITLES,
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
        run_ingest.TEAM_TITLE_OVERRIDES,
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
 