import pytest
from pydantic import ValidationError
 
from ingest.fetch_matches import FootballDataClient

FINISHED_MATCH = {
    "id": 330299,
    "utcDate": "2022-11-26T16:00:00Z",
    "status": "FINISHED",
    "stage": "GROUP_STAGE",
    "group": "GROUP_C",
    "lastUpdated": "2022-11-26T19:00:00Z",
    "homeTeam": {"id": 762, "name": "Argentina", "tla": "ARG", "crest": "xyz"},
    "awayTeam": {"id": 769, "name": "Mexico", "tla": "MEX", "crest": "abc"},
    "score": {
        "winner": "HOME_TEAM",
        "duration": "REGULAR",
        "fullTime": {"home": 2, "away": 0},
        "halfTime": {"home": 0, "away": 0},
    },
}

SCHEDULED_MATCH = {
    "id": 999,
    "utcDate": "2026-06-20T19:00:00Z",
    "status": "TIMED",
    "stage": "GROUP_STAGE",
    "group": None,
    "lastUpdated": "2026-06-15T00:00:00Z",
    "homeTeam": {"id": 1, "name": "Brazil", "tla": "BRA"},
    "awayTeam": {"id": 2, "name": "Spain", "tla": "ESP"},
    "score": {
        "winner": None,
        "duration": "REGULAR",
        "fullTime": {"home": None, "away": None},
        "halfTime": {"home": None, "away": None},
    },
}

def test_maps_finished_match():
    m = FootballDataClient._to_match(FINISHED_MATCH)
    assert m.id == 330299
    assert m.status.value == "FINISHED"
    assert m.group == "GROUP_C"
    assert m.home.name == "Argentina"
    assert m.away.tla == "MEX"
    assert m.score.home == 2 and m.score.away == 0
    assert m.score.ht_home == 0 and m.score.ht_away == 0
    assert m.score.duration == "REGULAR"
    assert m.utc_date.year == 2022

def test_maps_scheduled_match_with_nulls_and_missing_keys():
    m = FootballDataClient._to_match(SCHEDULED_MATCH)
    assert m.score.home is None         
    assert m.score.winner is None
    assert m.group is None
    
def test_unknown_status_fails_loud():
    bad = {**SCHEDULED_MATCH, "status": "NOT_A_REAL_STATUS"}
    with pytest.raises(ValidationError):
        FootballDataClient._to_match(bad)

def test_missing_required_field_fails_loud():
    incomplete = {k: v for k, v in FINISHED_MATCH.items() if k != "homeTeam"}
    with pytest.raises(KeyError):
        FootballDataClient._to_match(incomplete)

 
MESSI_RAW = {
    "player": {"id": 10, "name": "Lionel Messi", "nationality": "Argentina"},
    "team": {"id": 1, "name": "Argentina", "tla": "ARG"},
    "goals": 8, "assists": 3, "penalties": 1,
}

def test_to_scorer_maps_full_entry():
    s = FootballDataClient._to_scorer(MESSI_RAW)
    assert s.player_id == 10
    assert s.name == "Lionel Messi"
    assert s.team_name == "Argentina"
    assert s.goals == 8