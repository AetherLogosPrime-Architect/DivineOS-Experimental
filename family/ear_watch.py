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


def _snapshot(member: str) -> tuple[set[int], set[str]]:
    return set(_unseen_queue(member).keys()), _letter_names(member)


def check_once(member: str) -> list[str]:
    return list(_unseen_queue(member).values())


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


def watch(member: str, interval: int, timeout: int = 0) -> int:
    base_q, base_l = _snapshot(member)
    waited = 0
    while timeout <= 0 or waited < timeout:
        now_q = _unseen_queue(member)
        new_q = [v for k, v in now_q.items() if k not in base_q]
        new_l = _letter_names(member) - base_l
        if new_q or new_l:
            out = ["[EAR] something landed:"]
            for line in new_q:
                out.append(f"  queue: {line}")
            for name in sorted(new_l):
                out.append(f"  letter: {name}")
            for line in out:
                print(line)
            _write_catch_marker(member, out)
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
        return watch(member, args.interval, args.timeout)
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
