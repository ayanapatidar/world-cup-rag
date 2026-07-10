from datetime import datetime, timedelta, timezone

import pytest

from models import Match, Score, Team
from pipeline import run_watcher as w

NOW = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)


def _m(id=1, status="FINISHED", last_updated=NOW, utc_date=NOW):
    return Match(id=id, utc_date=utc_date, status=status, stage="GROUP_STAGE", group=None,
                 home=Team(id=1, name="A"), away=Team(id=2, name="B"),
                 score=Score(), last_updated=last_updated)

def _state(m, **over):
    s = {"last_updated": m.last_updated.isoformat(), "status": m.status.value}
    s.update(over)
    return {str(m.id): s}

def test_unseen_match_is_changed():
    assert w.changed_matches([_m()], {}) != []

def test_unchanged_match_is_skipped():
    m = _m()
    assert w.changed_matches([m], _state(m)) == []

def test_last_updated_move_triggers_reingest():
    old = _m(status="IN_PLAY", last_updated=NOW - timedelta(minutes=10))
    new = _m(status="IN_PLAY", last_updated=NOW)
    assert len(w.changed_matches([new], _state(old))) == 1

def test_newly_finished_fires_once():
    m = _m(status="FINISHED")
    assert len(w.newly_finished([m], _state(m))) == 1
    seen = _state(m, reactions_at=NOW.isoformat())
    assert w.newly_finished([m], seen) == []

def test_in_play_is_not_newly_finished():
    m = _m(status="IN_PLAY")
    assert w.newly_finished([m], {}) == []

def test_backfill_not_due_before_24h():
    m = _m()
    st = _state(m, reactions_at=(NOW - timedelta(hours=5)).isoformat(), backfill_done=False)
    assert w.backfill_due([m], st, NOW) == []

def test_backfill_due_after_24h_and_only_once():
    m = _m()
    st = _state(m, reactions_at=(NOW - timedelta(hours=25)).isoformat(), backfill_done=False)
    assert len(w.backfill_due([m], st, NOW)) == 1
    st[str(m.id)]["backfill_done"] = True
    assert w.backfill_due([m], st, NOW) == []

def test_live_match_polls_fast():
    assert w.next_sleep([_m(status="IN_PLAY")], {}, NOW) == w.LIVE_INTERVAL

def test_idle_sleeps_until_next_kickoff_within_cap():
    m = _m(status="SCHEDULED", utc_date=NOW + timedelta(minutes=30))
    assert w.next_sleep([m], {}, NOW) == pytest.approx(30 * 60)

def test_sleep_is_capped_for_distant_kickoff():
    m = _m(status="SCHEDULED", utc_date=NOW + timedelta(days=3))
    assert w.next_sleep([m], {}, NOW) == w.IDLE_CAP

def test_sleep_has_a_floor():
    m = _m(status="SCHEDULED", utc_date=NOW + timedelta(seconds=30))
    assert w.next_sleep([m], {}, NOW) == w.IDLE_FLOOR

def test_pending_backfill_shortens_sleep_past_a_distant_kickoff():
    kickoff = _m(id=1, status="SCHEDULED", utc_date=NOW + timedelta(days=3))
    done = _m(id=2, status="FINISHED")
    st = _state(done, reactions_at=(NOW - timedelta(hours=23, minutes=40)).isoformat(),
                backfill_done=False)
    delay = w.next_sleep([kickoff, done], st, NOW)
    assert delay == pytest.approx(20 * 60)
    assert delay < w.IDLE_CAP

def test_nothing_scheduled_sleeps_at_cap():
    assert w.next_sleep([_m(status="FINISHED")], {}, NOW) == w.IDLE_CAP

def test_save_and_load_state_roundtrip(tmp_path):
    p = tmp_path / "seen.json"
    w.save_state({"1": {"status": "FINISHED"}}, p)
    assert w.load_state(p) == {"1": {"status": "FINISHED"}}
    assert not p.with_suffix(".json.tmp").exists()

def test_load_state_missing_file_is_empty(tmp_path):
    assert w.load_state(tmp_path / "nope.json") == {}