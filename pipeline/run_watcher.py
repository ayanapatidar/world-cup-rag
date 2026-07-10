from __future__ import annotations
 
import argparse
import json
import os
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
 
from ingest.fetch_matches import FootballDataClient
from ingest.fetch_reactions import GuardianClient
from models import Match
from pipeline.run_ingest import ingest_matches, ingest_reactions
 
STATE_PATH = Path("data/seen_matches.json")
 
LIVE_INTERVAL = 60
IDLE_FLOOR = 900
IDLE_CAP = 3600
BACKFILL_AFTER = timedelta(hours=24)
 
_IN_PLAY = {"IN_PLAY", "PAUSED"}
_FINISHED = {"FINISHED", "AWARDED"}
_NOT_STARTED = {"SCHEDULED", "TIMED"}
 
_stop = False
 
 
def _handle_signal(signum, frame):
    global _stop
    _stop = True
    print("\n[watcher] Stopping after this cycle...")
 
def load_state(path: Path = STATE_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())
 
 
def save_state(state: dict[str, dict], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, path)

def changed_matches(matches: list[Match], state: dict[str, dict]) -> list[Match]:
    out = []
    for m in matches:
        prev = state.get(str(m.id))
        if prev is None or prev.get("last_updated") != m.last_updated.isoformat():
            out.append(m)
    return out

def newly_finished(matches: list[Match], state: dict[str, dict]) -> list[Match]:
    out = []
    for m in matches:
        if m.status.value not in _FINISHED:
            continue
        prev = state.get(str(m.id), {})
        if prev.get("reactions_at") is None:
            out.append(m)
    return out

def backfill_due(matches: list[Match], state: dict[str, dict],
                 now: datetime) -> list[Match]:
    """Finished matches whose 24h analysis backfill is now due."""
    out = []
    for m in matches:
        prev = state.get(str(m.id), {})
        at = prev.get("reactions_at")
        if not at or prev.get("backfill_done"):
            continue
        if now - datetime.fromisoformat(at) >= BACKFILL_AFTER:
            out.append(m)
    return out

def next_sleep(matches: list[Match], state: dict[str, dict], now: datetime) -> float:
    """LIVE_INTERVAL if anything is in play; else sleep until the soonest of
    (next kickoff, next backfill), floored and capped."""
    if any(m.status.value in _IN_PLAY for m in matches):
        return LIVE_INTERVAL
 
    upcoming: list[datetime] = [
        m.utc_date for m in matches
        if m.status.value in _NOT_STARTED and m.utc_date > now
    ]
    for prev in state.values():
        at = prev.get("reactions_at")
        if at and not prev.get("backfill_done"):
            upcoming.append(datetime.fromisoformat(at) + BACKFILL_AFTER)
 
    if not upcoming:
        return IDLE_CAP
    delta = (min(upcoming) - now).total_seconds()
    return max(IDLE_FLOOR, min(delta, IDLE_CAP))

def _record(state: dict[str, dict], m: Match) -> None:
    entry = state.setdefault(str(m.id), {})
    entry["last_updated"] = m.last_updated.isoformat()
    entry["status"] = m.status.value

def run_once(client: FootballDataClient, guardian: GuardianClient,
             state: dict[str, dict], *, now: datetime | None = None,
             dry_run: bool = False) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    matches = client.get_matches(refresh=True)
    first_run = not state
 
    changed = changed_matches(matches, state)
    finished = newly_finished(matches, state)
    backfill = backfill_due(matches, state, now)
 
    if first_run:
        print(f"[watcher] First run: baselining {len(matches)} matches ")
        for m in matches:
            _record(state, m)
            if m.status.value in _FINISHED:
                state[str(m.id)]["reactions_at"] = now.isoformat()
                state[str(m.id)]["backfill_done"] = True
        if not dry_run:
            save_state(state)
        return {"changed": 0, "reactions": 0, "backfill": 0}
 
    print(f"[watcher] {len(changed)} changed, {len(finished)} newly finished, "
          f"{len(backfill)} backfill due")
    if dry_run:
        for m in changed:
            print(f"    changed: {m.id} {m.home.name} vs {m.away.name} ({m.status.value})")
        return {"changed": len(changed), "reactions": len(finished),
                "backfill": len(backfill)}
 
    if changed:
        ingest_matches(changed)
        for m in changed:
            _record(state, m)
 
    if finished:
        ingest_reactions(finished, guardian, refresh=True)
        for m in finished:
            state[str(m.id)]["reactions_at"] = now.isoformat()
            state[str(m.id)]["backfill_done"] = False
 
    if backfill:
        ingest_reactions(backfill, guardian, refresh=True)
        for m in backfill:
            state[str(m.id)]["backfill_done"] = True
 
    save_state(state)
    return {"changed": len(changed), "reactions": len(finished),
            "backfill": len(backfill)}

def main() -> None:
    p = argparse.ArgumentParser(description="Poll for match updates and keep the corpus live.")
    p.add_argument("--once", action="store_true", help="run one cycle and exit")
    p.add_argument("--dry-run", action="store_true", help="print the diff but ingest nothing")
    p.add_argument("--state", type=Path, default=STATE_PATH)
    args = p.parse_args()
 
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
 
    client, guardian = FootballDataClient(), GuardianClient()
    state = load_state(args.state)
 
    while not _stop:
        now = datetime.now(timezone.utc)
        run_once(client, guardian, state, now=now, dry_run=args.dry_run)
        if args.once or _stop:
            break
        matches = client.get_matches()
        delay = next_sleep(matches, state, now)
        print(f"[watcher] sleeping {delay / 60:.1f} min")
        time.sleep(delay)
 
    print("[watcher] Done.")

if __name__ == "__main__":
    main()
 






