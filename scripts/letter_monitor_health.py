#!/usr/bin/env python3
"""Report whether the letter monitor is actually delivering — no self-match, no lying.

WHY THIS EXISTS

The letter monitor worked. Andrew 2026-08-15: *"the monitor we used to have
worked fine.. it just keeps dying and nothing checks for it or resets it, but
when it worked it worked."* He was right, and ``aria_rearm_events.log`` proves
it — ARMED, a real catch of the 2026-07-19 letter, then HEARTBEAT alive for two
weeks. It died at 2026-08-02 16:36:16 with ``FALLBACK activated after 3 failed
spawns in 77s`` and stayed dead for thirteen days.

Three things made those thirteen days silent, and this script exists so none of
them can happen quietly again.

**1. The old liveness check could not report dead.** It scanned every python
command line for the monitor's path — and the scanning process was itself a
python process whose command line contained that path, in a COMMENT explaining
the fix that was supposed to prevent exactly this. It found itself and reported
armed, unconditionally, from June onward. So the check most likely to notice the
death was the one guaranteed not to.

   Here: no process scan at all. Liveness is read from the monitor's OWN
   heartbeat file, which only the monitor writes. A checker cannot mistake
   itself for the thing it checks if it never looks at processes.

**2. The restart budget was a countdown, not a supervisor.** ``RestartCount 3``
at one-minute intervals spends itself in about seventy-seven seconds and then
never tries again, for any reason, forever. Worse, a task that has exhausted its
retries is indistinguishable from a task that never needed one.

   Here: no retry budget is enforced by this script, because a budget that can
   be exhausted is the bug. This reports; restarting is the caller's decision,
   and an unbounded caller is the correct shape.

**3. Silence read as health.** Every layer failed toward "fine". The check said
armed, the log stopped growing, nothing summed it up, and the only signal that
anything was wrong was Andrew noticing letters had stopped arriving.

   Here: absence is an explicit state with its own exit code, and the reason is
   always named. A stale heartbeat says how stale. A missing file says missing.
   Neither renders as OK.

Exit codes: 0 healthy, 1 stale, 2 never started / no heartbeat, 3 cannot tell.
"3 cannot tell" is deliberately distinct from all of the above — an unreadable
state must never be reported as a healthy one, which is the whole disease this
substrate keeps producing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# The monitor writes this; nothing else does. Single writer, single reader.
HEARTBEAT_NAME = "letter_monitor_heartbeat.json"

# A heartbeat older than this means the monitor is not delivering. The monitor's
# own poll interval is 30s; three missed beats is the threshold, which is long
# enough to survive a slow disk and short enough that a real death surfaces on
# the next check rather than thirteen days later.
STALE_AFTER_SECONDS = 90

# The harness kills a watch at thirty minutes. That is a ceiling, not a setting:
# asking for longer is capped silently, so no watch ever lives past it and every
# watch therefore ends. Before 2026-09-17 this file could not tell that ending
# from a death, so a scheduled event rendered as an emergency and Andrew read
# the emergency at the top of every prompt: "the Aria letter watcher keeps dying
# every prompt now."
#
# An alarm that fires on a scheduled event teaches its reader to skip the
# paragraph, and the reader who skips it is the one who misses a real death.
# That is not hypothetical here — thirteen silent days happened because every
# layer had stopped carrying meaning. So this distinction PROTECTS the alarm
# rather than quieting it.
MONITOR_LIFESPAN_SECONDS = 30 * 60

# How far short of the full term still counts as having run its life. A watch is
# not killed to the second, and the beat before the kill can be up to one poll
# interval old, so the window absorbs both without being wide enough to let an
# early stop pass as complete.
LIFESPAN_GRACE_SECONDS = 120


def _ran_its_full_term(armed_at: float | None, last_beat: float) -> bool:
    """True only when this watch demonstrably lived its whole allotted life.

    THE DISCRIMINATOR IS LIFESPAN, because it is the one thing a failure cannot
    fake: a crash cannot extend itself to a full term. Timing alone would not do
    — a crash could happen to occur at a routine-looking moment — which is why
    the question is how long it LIVED rather than when it stopped.

    Every uncertain answer resolves to False, i.e. to the loud case:

      - no start time recorded (an older monitor, or an unreadable field)
      - a start time in the future, or a life longer than the cap, either of
        which means this record is not describing the watch it appears to

    Unknown must land on alarm. The failure this file exists to end is silence
    read as health, and a quiet branch that grows is how it would come back.
    """
    if armed_at is None:
        return False
    lifespan = last_beat - armed_at
    if lifespan < 0 or lifespan > MONITOR_LIFESPAN_SECONDS + LIFESPAN_GRACE_SECONDS:
        return False
    return lifespan >= MONITOR_LIFESPAN_SECONDS - LIFESPAN_GRACE_SECONDS


def heartbeat_path() -> Path:
    try:
        from divineos.core.paths import divineos_home

        return divineos_home() / HEARTBEAT_NAME
    except Exception:  # noqa: BLE001 — home resolution must not decide health
        return Path(os.path.expanduser("~")) / ".divineos" / HEARTBEAT_NAME


def check(now: float | None = None) -> tuple[int, str]:
    """Return (exit_code, human_reason). Never raises."""
    now = time.time() if now is None else now
    p = heartbeat_path()

    if not p.exists():
        return 2, (
            f"NO HEARTBEAT — {p} does not exist. The monitor has not run since "
            f"this file was last cleared. It is not delivering letters."
        )

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        beat = float(raw["last_beat_unix"])
        recipient = str(raw.get("recipient", "?"))
    except Exception as exc:  # noqa: BLE001
        # Unreadable is its own answer. Reporting this as healthy is the exact
        # failure mode the whole file exists to prevent.
        return 3, f"CANNOT TELL — heartbeat unreadable ({exc.__class__.__name__}: {exc})"

    try:
        armed_at: float | None = float(raw["armed_at_unix"])
    except Exception:  # noqa: BLE001 — absent or unreadable both mean "cannot tell"
        armed_at = None

    age = now - beat
    if age > STALE_AFTER_SECONDS:
        if _ran_its_full_term(armed_at, beat):
            return 4, (
                f"EXPIRED ON SCHEDULE — ran its full term and the harness "
                f"stopped it, {age:.0f}s ago, recipient={recipient}. Nothing "
                f"broke. Re-arm when a wake is wanted."
            )
        return 1, (
            f"STALE — last beat {age:.0f}s ago (threshold {STALE_AFTER_SECONDS}s), "
            f"recipient={recipient}. It stopped BEFORE its term was up, so this "
            f"is a death rather than the scheduled end, and nothing restarted it."
        )

    return 0, f"HEALTHY — last beat {age:.0f}s ago, recipient={recipient}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quiet", action="store_true", help="print nothing; exit code only")
    args = ap.parse_args(argv[1:])

    code, reason = check()
    if not args.quiet:
        print(f"[letter-monitor-health] {reason}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
