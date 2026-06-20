from models import Match, Score, Team, Article, HistoryDoc
from pipeline.passages import match_to_text, article_to_text, history_to_text


def _match(status="FINISHED", stage="GROUP_STAGE", group=None,
           home="Argentina", away="Brazil", winner=None, h=None, a=None,
           ht_home=None, ht_away=None, duration="REGULAR"):
    return Match(
        id=1,
        utc_date="2026-06-11T16:00:00Z",
        status=status,
        stage=stage,
        group=group,
        home=Team(id=1, name=home),
        away=Team(id=2, name=away),
        score=Score(winner=winner, duration=duration, home=h, away=a,
                    ht_home=ht_home, ht_away=ht_away),
        last_updated="2026-06-11T18:00:00Z",
    )


def test_match_home_win_with_halftime():
    text = _match(winner="HOME_TEAM", h=3, a=1, ht_home=2, ht_away=0)
    out = match_to_text(text)
    assert "Argentina beat Brazil 3-1" in out
    assert "group stage" in out
    assert "11 June 2026" in out
    assert "At half-time it was 2-0." in out


def test_match_away_win():
    out = match_to_text(_match(winner="AWAY_TEAM", h=1, a=2))
    assert "Brazil beat Argentina 2-1" in out


def test_match_draw():
    out = match_to_text(_match(winner="DRAW", h=2, a=2))
    assert "Argentina drew 2-2 with Brazil" in out


def test_match_extra_time():
    out = match_to_text(
        _match(stage="SEMI_FINALS", winner="AWAY_TEAM", h=1, a=2, duration="EXTRA_TIME")
    )
    assert "Brazil beat Argentina 2-1 after extra time" in out
    assert "semi-finals" in out


def test_match_penalties_reads_as_draw_plus_winner():
    out = match_to_text(
        _match(stage="FINAL", winner="HOME_TEAM", h=1, a=1, duration="PENALTY_SHOOTOUT")
    )
    assert "Argentina and Brazil drew 1-1, Argentina winning on penalties" in out
    assert "on penalties on" not in out


def test_match_group_label():
    out = match_to_text(_match(group="GROUP_C", winner="HOME_TEAM", h=2, a=0))
    assert "(Group C)" in out


def test_match_scheduled_is_a_fixture():
    out = match_to_text(_match(status="SCHEDULED"))
    assert "scheduled to play" in out
    assert "beat" not in out and "drew" not in out


def test_match_in_play_shows_running_score():
    out = match_to_text(_match(status="IN_PLAY", h=1, a=1))
    assert "are playing" in out
    assert "score so far is 1-1" in out


def test_article_frames_title_then_body():
    a = Article(
        id="g1", match_id=1, title="Argentina edge Brazil",
        body="It was tense.", url="https://example.com/x",
        published="2026-06-11T20:00:00Z",
    )
    assert article_to_text(a) == "Argentina edge Brazil\n\nIt was tense."


def test_history_frames_title_then_body():
    h = HistoryDoc(id="42", source="wikipedia", title="Lionel Messi",
                   body="Argentine footballer.", url=None)
    assert history_to_text(h) == "Lionel Messi\n\nArgentine footballer."