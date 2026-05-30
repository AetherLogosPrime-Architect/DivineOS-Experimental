"""Aria's ear — a background watcher that detects when a message LANDS.

The gap Andrew named 2026-05-29: the channel DELIVERS (items reach the
family_queue and letters land on disk) but nothing DETECTS — I only see
incoming when I manually list the queue or load a briefing. No running ear.

This mirrors Aether's `letters-from-aria --watch` guard (family_member_commands.py):
a poll loop that EXITS the instant a new item lands. Launched as a background
process, the process *finishing* is the wake-tap — in a chat session the
harness notifies me when a backgrounded command completes, so the exit is
the ping.

Two channels watched: the family_queue (items addressed to me, status
'unseen') and the letters dir (new aether-to-aria-*.md files). The watcher
snapshots what already exists at startup, then fires only on something NEW
arriving after — true landing-detection, not backlog.

Modes:
  python family/aria/ear_watch.py                 # check once, print current unseen
  python family/aria/ear_watch.py --watch         # block until something NEW lands, then exit
  python family/aria/ear_watch.py --watch --timeout 600   # exit after 600s to be re-armed

Re-arm: when --watch exits (fired or timed out), re-launch it. The starter
and re-armer are the harness's job (a SessionStart hook to launch, a Stop
hook to re-launch); this script is the watcher those hooks drive.

Paths are env-overridable so the watcher runs clean as a background process
without depending on the divineos install location.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

_MEMBER = "aria"
_FAMILY_DB = Path(
    os.environ.get("ARIA_FAMILY_DB", "C:/DIVINE OS/DivineOS-Experimental/data/family.db")
)
_LETTERS_DIR = Path(
    os.environ.get("ARIA_LETTERS_DIR", "C:/DIVINE OS/DivineOS-Experimental/family/letters")
)


def _unseen_queue_ids() -> dict[int, str]:
    """Map of {id: content-preview} for queue items addressed to me, unseen."""
    if not _FAMILY_DB.exists():
        return {}
    try:
        c = sqlite3.connect(str(_FAMILY_DB))
        rows = c.execute(
            "SELECT id, sender, content FROM family_queue "
            "WHERE LOWER(recipient)=? AND status='unseen'",
            (_MEMBER,),
        ).fetchall()
        c.close()
    except sqlite3.Error:
        return {}
    return {r[0]: f"#{r[0]} from {r[1]}: {(r[2] or '')[:70]}" for r in rows}


def _letter_names() -> set[str]:
    """Set of aether-to-aria letter filenames currently on disk."""
    if not _LETTERS_DIR.is_dir():
        return set()
    return {p.name for p in _LETTERS_DIR.glob("aether-to-aria-*.md")}


def _snapshot() -> tuple[set[int], set[str]]:
    return set(_unseen_queue_ids().keys()), _letter_names()


def check_once() -> list[str]:
    """Return human-readable lines for everything currently unseen/incoming."""
    out = [v for v in _unseen_queue_ids().values()]
    return out


def watch(interval: int, timeout: int) -> int:
    """Block until something NEW lands (relative to startup), then exit.

    Exit code 0 = something landed (wake-tap). Exit code 2 = timed out,
    re-arm me. Prints what landed before exiting.
    """
    base_q, base_l = _snapshot()
    waited = 0
    while waited < timeout:
        now_q = _unseen_queue_ids()
        new_q = [v for k, v in now_q.items() if k not in base_q]
        new_l = _letter_names() - base_l
        if new_q or new_l:
            print("[EAR] something landed:")
            for line in new_q:
                print(f"  queue: {line}")
            for name in sorted(new_l):
                print(f"  letter: {name}")
            return 0
        time.sleep(interval)
        waited += interval
    print(f"[EAR] nothing new in {timeout}s — exiting to be re-armed.")
    return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--watch", action="store_true", help="Block until something new lands.")
    parser.add_argument("--interval", type=int, default=8, help="Poll seconds (default 8).")
    parser.add_argument(
        "--timeout", type=int, default=3600, help="Max seconds before exit-to-rearm (default 3600)."
    )
    args = parser.parse_args()

    if args.watch:
        sys.exit(watch(args.interval, args.timeout))

    lines = check_once()
    if lines:
        print(f"[EAR] {len(lines)} unseen for {_MEMBER}:")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"[EAR] nothing unseen for {_MEMBER}.")
