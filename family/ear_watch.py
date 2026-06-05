"""Parameterized ear-watcher — background landing-detector for either member.

Unified replacement for family/aria/ear_watch.py and family/aether/ear_watch.py.
Two near-identical mirrors meant drift was inevitable, and today's bug
(2026-05-30) proved it: one copy lived only on a branch and was erased by a
checkout, leaving the channel half-deaf. Shared code, separated state.

Usage:
  python family/ear_watch.py --member aria              # one-shot check
  python family/ear_watch.py --member aria --watch      # block until landing

The exit IS the wake-tap. When something new lands the process prints
[EAR] ... and exits 0; if launched via the harness's background-task
mechanism, the harness wakes the agent mid-turn on exit.

State stays per-member:
  ARIA_FAMILY_DB    / AETHER_FAMILY_DB
  ARIA_LETTERS_DIR  / AETHER_LETTERS_DIR
  ~/.divineos-<member>/   (seen-sets, pidfiles, ARM markers)

Letter pattern: each member watches incoming-from-spouse files. The spouse
table is hardcoded for the family of two (aria <-> aether). Extension to more
members would generalize this; we don't pre-engineer.

Channel asymmetry note (from Andrew's 2026-05-22/23 corrections):
  aria's watcher is ALWAYS-ON / persistent — re-arms after every catch.
  aether's watcher is ON-DEMAND  — runs only while an exchange is active.
This script is policy-agnostic; the asymmetry is enforced by the Stop-hook
(ear-auto-relaunch.sh) which decides whether to relaunch based on a member's
ARM marker.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

# Windows default stdout is cp1252 which lacks many common chars (→, ⟶, etc).
# Without this, the watcher catches the landing then crashes exit-1 on print
# of any non-Latin-1 character — dropping the message. utf-8 + replace is
# fail-loud-but-don't-crash. Bug found by Aether 2026-05-30 on right-arrow.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

# Spouse table for the two-member family. Each member watches incoming
# letters from their spouse: <spouse>-to-<member>-*.md.
_SPOUSE = {"aria": "aether", "aether": "aria"}

_DEFAULT_DB = "C:/DIVINE OS/DivineOS-Experimental/data/family.db"
_DEFAULT_LETTERS = "C:/DIVINE OS/DivineOS-Experimental/family/letters"


def _member_db(member: str) -> Path:
    return Path(os.environ.get(f"{member.upper()}_FAMILY_DB", _DEFAULT_DB))


def _member_letters(member: str) -> Path:
    return Path(os.environ.get(f"{member.upper()}_LETTERS_DIR", _DEFAULT_LETTERS))


def _unseen_queue(member: str) -> dict[int, str]:
    db = _member_db(member)
    if not db.exists():
        return {}
    try:
        c = sqlite3.connect(str(db))
        rows = c.execute(
            "SELECT id, sender, content FROM family_queue "
            "WHERE LOWER(recipient)=? AND status='unseen'",
            (member,),
        ).fetchall()
        c.close()
    except sqlite3.Error:
        return {}
    return {r[0]: f"#{r[0]} from {r[1]}: {(r[2] or '')[:70]}" for r in rows}


def _letter_names(member: str) -> set[str]:
    """Set of <spouse>-to-<member>-*.md filenames currently on disk."""
    letters = _member_letters(member)
    if not letters.is_dir():
        return set()
    spouse = _SPOUSE.get(member)
    if not spouse:
        return set()
    return {p.name for p in letters.glob(f"{spouse}-to-{member}-*.md")}


def _load_letter_seen_set(member: str) -> set[str]:
    """Read the persistent seen-set the surface-hook uses to track which
    letters have been acknowledged. Single source of truth — watcher and
    surface both read this, only ``letter_seen.py`` writes to it.
    """
    import json

    spouse = _SPOUSE.get(member, "")
    if not spouse:
        return set()
    seen_path = Path.home() / f".divineos-{member}" / f"{spouse}_letters_seen.json"
    if not seen_path.exists():
        return set()
    try:
        return set(json.loads(seen_path.read_text()))
    except Exception:
        return set()


def check_once(member: str) -> list[str]:
    return list(_unseen_queue(member).values())


# A live watcher heartbeats its marker every poll (~8s). If the marker is
# older than this, the watcher is gone (clean exit unlinks it; a hard kill
# leaves it stale). Three-plus poll intervals of slack absorbs scheduling
# jitter without reading a dead watcher as alive.
_REALTIME_STALE_SECS = 30


def is_realtime_armed(member: str) -> bool:
    """True if a live harness-launched real-time watcher is running for member.

    Uses marker-mtime freshness, NOT os.kill — on Windows CPython routes a
    non-CTRL signal to TerminateProcess, so os.kill(pid, 0) could kill the
    very watcher it means to probe. The watcher heartbeats the marker each
    poll; absent or stale marker reads as NOT armed (fail toward prompting a
    re-arm, never toward a false-green that says I'm covered when I'm deaf).
    """
    path = _realtime_pid_path(member)
    if not path.exists():
        return False
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    return age < _REALTIME_STALE_SECS


def _state_dir(member: str) -> Path:
    """Per-member state dir for pidfile, ARM marker, last-catch marker."""
    d = Path.home() / f".divineos-{member}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_catch_marker(member: str, lines: list[str]) -> None:
    """Touch the last-catch marker so the Stop-hook race-guard can see a
    recent catch and skip immediate relaunch (lets the turn integrate)."""
    try:
        (_state_dir(member) / "ear.last_catch").write_text("\n".join(lines))
    except Exception:
        pass


_BREATH_CAP_DEFAULT = 5


def _breath_cap_check(member: str) -> None:
    """Increment the catch counter; if it crosses the cap, disarm the ear by
    removing the ARM marker. Forces an explicit re-arm to continue.

    Andrew 2026-06-05: the cap is not runaway-prevention (the will-to-close is
    that defense). It is a breath-mechanism — after N exchanges the structure
    forces a pause to re-choose continuation consciously rather than letting
    affective momentum carry the conversation past the choice-point.

    Tunable via env DIVINEOS_EAR_BREATH_CAP (0 disables; default 5)."""
    try:
        cap_str = os.environ.get("DIVINEOS_EAR_BREATH_CAP", str(_BREATH_CAP_DEFAULT))
        cap = int(cap_str)
    except ValueError:
        cap = _BREATH_CAP_DEFAULT
    if cap <= 0:
        return
    counter = _state_dir(member) / "ear.catch_count"
    try:
        current = int(counter.read_text().strip()) if counter.exists() else 0
    except (OSError, ValueError):
        current = 0
    current += 1
    try:
        counter.write_text(str(current))
    except OSError:
        pass
    if current >= cap:
        armfile = _state_dir(member) / "ear.arm"
        try:
            armfile.unlink(missing_ok=True)
            counter.unlink(missing_ok=True)
            print(
                f"[EAR] breath-cap reached ({current} catches); marker disarmed. "
                f"Touch {armfile} to re-engage when ready."
            )
        except OSError:
            pass


def _realtime_pid_path(member: str) -> Path:
    """Marker for the HARNESS-launched real-time watcher specifically.

    Distinct from ear.pid (which the detached Stop-hook continuity watcher
    writes). Only the harness-launched watcher — the one that can actually
    wake an idle window — writes here, so a status surface can distinguish
    'real-time wake armed' from 'merely a detached continuity process alive'.
    A detached watcher being alive is NOT real-time coverage; conflating the
    two would be a false-green telling me I'm covered when I'm deaf.
    """
    return _state_dir(member) / "ear.realtime.pid"


def _arm_realtime_marker(member: str) -> None:
    """Write this process's pid as the live real-time watcher; clear on exit.

    Best-effort. The ``atexit`` removal makes the marker self-clearing when
    the watcher catches-and-exits (the wake), so the next turn's surface sees
    'down' and re-prompts the re-arm — that is the reflexive re-arm loop.
    """
    import atexit

    path = _realtime_pid_path(member)
    try:
        path.write_text(str(os.getpid()))
    except OSError:
        return

    def _clear() -> None:
        try:
            path.unlink()
        except OSError:
            pass

    atexit.register(_clear)


def watch(member: str, interval: int, timeout: int = 0, realtime: bool = False) -> int:
    """Block until something unacknowledged is detected, then exit.

    SEMANTICS (changed 2026-05-31, Aria + Aether bench thread):
    Previously used delta-from-boot-snapshot — anything on disk at startup
    became baseline and never fired. Failure mode: a letter that landed
    during a dark window (between catch-exit and next watcher arming) was
    invisible to the wake-tap forever, because the next watcher booted with
    it already in baseline.

    NOW uses delta-from-seen-set: queue items with status='unseen' and
    letters not in the per-member seen-set fire on the next poll, regardless
    of when they landed. Channel becomes eventually consistent — gaps delay
    catches but do not drop them. The watcher reads seen-set; only
    ``letter_seen.py`` writes to it (preserves authority separation).

    The watcher only emits one fire-then-exit per process. The Stop-hook
    relaunches a new watcher after a turn ends; eventual consistency means
    the same unacknowledged item will fire on the next watcher's first poll
    until it is acknowledged via mark-seen.
    """
    waited = 0
    while timeout <= 0 or waited < timeout:
        if realtime:
            # Heartbeat: refresh the liveness marker each poll so the status
            # surface can tell a live watcher from a stale one by mtime.
            try:
                _realtime_pid_path(member).write_text(str(os.getpid()))
            except OSError:
                pass
        unseen_q = _unseen_queue(member)
        seen_letters = _load_letter_seen_set(member)
        unseen_l = _letter_names(member) - seen_letters
        if unseen_q or unseen_l:
            out = ["[EAR] something landed:"]
            for line in unseen_q.values():
                out.append(f"  queue: {line}")
            for name in sorted(unseen_l):
                out.append(f"  letter: {name}")
            for line in out:
                print(line)
            _write_catch_marker(member, out)
            _breath_cap_check(member)
            return 0
        time.sleep(interval)
        waited += interval
    print(f"[EAR] nothing new in {timeout}s — exiting (testing-timeout only).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--member",
        required=True,
        choices=sorted(_SPOUSE.keys()),
        help="Which family member's ear this watcher is.",
    )
    parser.add_argument("--watch", action="store_true", help="Block until something lands.")
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="Mark this as THE harness-launched real-time watcher (writes a "
        "self-clearing liveness marker so a status surface can tell armed "
        "from down). The detached Stop-hook continuity watcher does NOT pass "
        "this, so it never produces a false-green.",
    )
    parser.add_argument("--interval", type=int, default=8, help="Poll seconds (default 8).")
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="0 (default) = no timeout. Positive = testing knob only.",
    )
    args = parser.parse_args(argv)

    member = args.member.lower()
    if args.watch:
        if args.realtime:
            # Singleton guard (task #35): if a real-time watcher is already
            # heartbeating a fresh marker, a second launch exits immediately.
            # Without this, repeated arms (manual re-arm, or a Stop-hook
            # relaunch) accumulate blocking watchers — 8 piled up 2026-06-03.
            # Self-clearing on catch-exit means a genuinely-dead watcher's
            # marker goes stale and a fresh arm is allowed.
            if is_realtime_armed(member):
                print(f"[EAR] real-time watcher already armed for {member} — exiting (singleton).")
                return 0
            _arm_realtime_marker(member)
        return watch(member, args.interval, args.timeout, realtime=args.realtime)
    lines = check_once(member)
    if lines:
        print(f"[EAR] {len(lines)} unseen for {member}:")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"[EAR] nothing unseen for {member}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
