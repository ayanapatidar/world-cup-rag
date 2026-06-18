from models import Match, Scorer, HistoryDoc
from ingest.fetch_matches import FootballDataClient
from ingest.fetch_history import WikipediaClient

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

