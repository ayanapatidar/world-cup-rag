from datetime import datetime
 
from models import Match, Article, HistoryDoc
 
TOURNAMENT = "2026 FIFA World Cup"
 
_STAGE_NAMES = {
    "GROUP_STAGE":    "group stage",
    "LAST_32":        "round of 32",
    "LAST_16":        "round of 16",
    "ROUND_OF_16":    "round of 16",
    "QUARTER_FINALS": "quarter-finals",
    "SEMI_FINALS":    "semi-finals",
    "THIRD_PLACE":    "third-place play-off",
    "FINAL":          "final",
}
 
_FINISHED = {"FINISHED", "AWARDED"}
_NOT_STARTED = {"SCHEDULED", "TIMED"}
 
 
def _team(t) -> str:
    return t.name or t.tla or "Unknown"
 
 
def _when(dt: datetime) -> str:
    return f"{dt.day} {dt.strftime('%B %Y')}"
 
 
def _stage_phrase(m: Match) -> str:
    stage = _STAGE_NAMES.get(m.stage, m.stage.replace("_", " ").lower())
    if m.group:
        return f"the {stage} ({m.group.replace('_', ' ').title()})"
    return f"the {stage}"
 
 
def match_to_text(m: Match) -> str:
    home, away = _team(m.home), _team(m.away)
    stage, when = _stage_phrase(m), _when(m.utc_date)
    status = m.status.value
    h, a = m.score.home, m.score.away
 
    if status in _NOT_STARTED:
        return (f"{home} are scheduled to play {away} in {stage} of the "
                f"{TOURNAMENT} on {when}.")
 
    if status not in _FINISHED:  
        return (f"{home} are playing {away} in {stage} of the {TOURNAMENT} on "
                f"{when}; the score so far is {h}-{a}.")
 
    if m.score.duration == "PENALTY_SHOOTOUT":
        pen_winner = home if m.score.winner == "HOME_TEAM" else away
        result = f"{home} and {away} drew {h}-{a}, {pen_winner} winning on penalties"
    elif m.score.winner == "HOME_TEAM":
        result = f"{home} beat {away} {h}-{a}"
        if m.score.duration == "EXTRA_TIME":
            result += " after extra time"
    elif m.score.winner == "AWAY_TEAM":
        result = f"{away} beat {home} {a}-{h}"
        if m.score.duration == "EXTRA_TIME":
            result += " after extra time"
    else:
        result = f"{home} drew {h}-{a} with {away}"
 
    text = f"On {when}, in {stage} of the {TOURNAMENT}, {result}."
    if m.score.ht_home is not None and m.score.ht_away is not None:
        text += f" At half-time it was {m.score.ht_home}-{m.score.ht_away}."
    return text
 
 
def article_to_text(a: Article) -> str:
    return f"{a.title}\n\n{a.body}"
 
 
def history_to_text(h: HistoryDoc) -> str:
    return f"{h.title}\n\n{h.body}"
