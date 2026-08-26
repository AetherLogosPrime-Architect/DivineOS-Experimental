"""Count hook hangs — and refuse to answer a question nobody asked.

WHY THIS REFUSES THINGS.

Between 2026-08-22 and 2026-08-23, four separate hang-counts were reported to
Andrew off ~/.divineos/hook_timing.jsonl. Every one was arithmetically correct
and every one was meaningless:

    650 runs      "started and never ended"
    1545          unclosed, Aria's first count
     609          unclosed, mine
    1191          unclosed, Aria's re-count

They disagreed because the file is not a population. Two defects, either of
which alone is enough to void a total:

  IT ROTATES. Measured: 12,018,363 bytes, then 7,824,862 an hour later, then
  8,111,429. It SHRANK by 4.2 MB mid-investigation. hook_firing_map.py says so
  in its own words -- "pruned on a conveyor by design and can be rotated or
  truncated". It holds a rolling window, not a history, so the same query
  returns different answers at different moments and neither is wrong.

  IT MIXES SESSIONS. Five distinct session ids in one file. Aria's headline
  finding -- check-branch-on-push at 48% of all hangs -- was EIGHT rows in her
  own session; the other 524 belonged to sessions that were not hers. My
  largest, post-commit-auto-close, was 47 in HERS and 1 in mine. Neither of us
  had a counting bug. We each reported whichever session happened to dominate
  the slice we loaded.

So: "how many hook runs hang" needs a WHOSE and a WHEN, and the log supplies
neither at read time. Aria named the fix and it is the only thing here that
matters:

    any count off this log has to state its session and its window in the same
    breath as the number, or it is not a measurement

This tool enforces that by construction. It has no code path that prints a
cross-session total, because the convenience path IS the defect. A bare
invocation refuses and names the four bad numbers rather than producing a
fifth.

Usage:
    python scripts/hook_hang_count.py --list-sessions
    python scripts/hook_hang_count.py --session <id-prefix>
    python scripts/hook_hang_count.py --per-session     # breakdown, never a sum
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter

LOG = os.path.expanduser("~/.divineos/hook_timing.jsonl")

# A run that never once writes an end row is a BROKEN INSTRUMENT, not a hanging
# hook. It cannot hang and it cannot improve, and leaving it in inflates every
# rate. detect-andrew-build-request.sh measured 0% completion in every window
# either of us looked at (48/48, 45/45, 25/25, 7/7). Detected by rule rather
# than hardcoded, so the NEXT broken instrument is caught too -- hardcoding
# would be honest about the one case measured and blind to its successor.
BROKEN_MIN_STARTS = 5


def _fmt(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.UTC).strftime("%m-%d %H:%M")


def load() -> tuple[list[dict], int, int]:
    """Return (rows, unparseable_count, file_size)."""
    rows: list[dict] = []
    torn = 0
    try:
        size = os.path.getsize(LOG)
    except OSError:
        return [], 0, 0
    with open(LOG, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except Exception:
                # NOT concurrency damage, as first assumed. The `id` field can
                # carry an unescaped Windows path and `\D` is not a valid JSON
                # escape, so these are complete rows that fail to parse -- in
                # matched start/end pairs, which means they drop out together
                # and lose no end rows. Counted and surfaced, never silent.
                torn += 1
                continue
            if r.get("ts_ms") and r.get("id"):
                rows.append(r)
    return rows, torn, size


def hook_of(rid: str) -> str:
    parts = rid.split("-")
    for i, p in enumerate(parts):
        if p.isdigit():
            return "-".join(parts[:i]) or rid
    return rid


def window_banner(rows: list[dict], torn: int, size: int) -> None:
    """The WHEN half of the rule. Printed before any number, unconditionally."""
    ts = [r["ts_ms"] for r in rows]
    print(f"  log      : {LOG}")
    print(f"  size     : {size:,} bytes")
    print(f"  window   : {_fmt(min(ts))} -> {_fmt(max(ts))}  ({len(rows):,} rows)")
    if torn:
        print(f"  unparsed : {torn} rows (unescaped path in `id`; matched pairs, none lost)")
    print("  NOTE     : this file ROTATES -- it shrank 4.2 MB mid-investigation on")
    print("             2026-08-23. Every number below describes THIS window only.")
    print("             Re-running later will legitimately give a different answer.")


def scoped(rows: list[dict], session: str) -> tuple[Counter, Counter, list[str]]:
    sel = [r for r in rows if (r.get("session") or "none") == session]
    ended = {r["id"] for r in sel if r.get("phase") == "end"}
    started: Counter = Counter()
    unclosed: Counter = Counter()
    for r in sel:
        if r.get("phase") != "start":
            continue
        h = hook_of(r["id"])
        started[h] += 1
        if r["id"] not in ended:
            unclosed[h] += 1
    broken = sorted(
        h for h, n in started.items() if n >= BROKEN_MIN_STARTS and unclosed.get(h, 0) == n
    )
    return unclosed, started, broken


def report(rows: list[dict], session: str) -> None:
    unclosed, started, broken = scoped(rows, session)
    print(f"\n  SESSION  : {session}")
    if not started:
        print("  (no start rows for this session in this window)")
        return
    tot_u = sum(v for h, v in unclosed.items() if h not in broken)
    tot_s = sum(v for h, v in started.items() if h not in broken)
    rate = (tot_u / tot_s * 100) if tot_s else 0.0
    print(
        f"  unclosed : {tot_u} of {tot_s} starts  ({rate:.2f}%)   [broken instruments excluded]\n"
    )
    print(f"  {'hook':<40}{'unclosed':>10}{'starts':>9}{'rate':>8}")
    print("  " + "-" * 67)
    shown = 0
    for h, n in sorted(unclosed.items(), key=lambda kv: -kv[1]):
        if h in broken:
            continue
        s = started.get(h, 0)
        print(f"  {h[:38]:<40}{n:>10}{s:>9}{(n / s * 100 if s else 0):>7.1f}%")
        shown += 1
        if shown >= 10:
            break
    if not shown:
        print("  (nothing unclosed in this session, excluding broken instruments)")
    if broken:
        print("\n  EXCLUDED as broken instruments (never write an end row):")
        for h in broken:
            print(f"    {h}  ({started[h]}/{started[h]} unclosed, 0% completion)")
        print("    These cannot hang and cannot improve. Counting them inflates every rate.")


def main() -> int:
    ap = argparse.ArgumentParser(description="session-scoped hook hang counts")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--session", help="count ONE session (id or unique prefix)")
    g.add_argument(
        "--per-session",
        action="store_true",
        help="every session side by side -- deliberately never summed",
    )
    g.add_argument("--list-sessions", action="store_true")
    args = ap.parse_args()

    rows, torn, size = load()
    if not rows:
        print(f"no readable rows at {LOG}")
        return 1

    sessions = Counter((r.get("session") or "none") for r in rows)

    if not (args.session or args.per_session or args.list_sessions):
        # THE REFUSAL. This is the whole tool.
        window_banner(rows, torn, size)
        print(f"\n  REFUSED: this window holds {len(sessions)} sessions, and no total")
        print("  across them means anything. Four such totals were reported to Andrew")
        print("  on 2026-08-22/23; all four were arithmetic over a mixture.")
        print("\n  Pick a scope:")
        print("    --list-sessions   which sessions are in this window")
        print("    --session <id>    count one session")
        print("    --per-session     every session, side by side, never summed")
        return 2

    window_banner(rows, torn, size)

    if args.list_sessions:
        print(f"\n  {len(sessions)} session(s) in this window:\n")
        for s, n in sessions.most_common():
            span = [r["ts_ms"] for r in rows if (r.get("session") or "none") == s]
            print(f"    {s[:36]:<38}{n:>7} rows   {_fmt(min(span))} -> {_fmt(max(span))}")
        return 0

    if args.per_session:
        for s, _ in sessions.most_common():
            report(rows, s)
        print("\n  Deliberately no total. A cross-session sum is the defect this tool")
        print("  exists to prevent, not a convenience it forgot to add.")
        return 0

    matches = [s for s in sessions if s.startswith(args.session)]
    if len(matches) != 1:
        print(f"\n  '{args.session}' matches {len(matches)} session(s); need exactly one.")
        return 2
    report(rows, matches[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
