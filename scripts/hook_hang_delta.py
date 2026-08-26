"""Did a fix change the never-finished hook-run rate? Split the timing log and compare.

Aletheia, 2026-08-22, reviewing the claim that an inherited file descriptor in
the auto-push hooks WAS the freeze Andrew has been living with:

    "Land it, then re-measure. If never-finished runs drop sharply, the join is
    evidenced. If they do not, you have merged two problems."

She is right that the join was made by argument. Aria's 650-started-never-ended
figure does not discriminate: that population is defined by ABSENCE of an end
row, and a hook blocked on a descriptor, a hook killed at its deadline, and a
hook whose process died all produce that same absence.

So this does not measure hangs. It measures the never-finished RATE on either
side of a boundary, per hook, normalised by run count -- because the windows
are never the same size and a raw count drop can be nothing but a quieter hour.

Usage:
    python scripts/hook_hang_delta.py --boundary-iso 2026-08-22T23:40:28Z
    python scripts/hook_hang_delta.py --boundary-commit 456e250c
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
from collections import defaultdict


def load(log_path: pathlib.Path) -> list[dict]:
    rows = []
    with log_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn final line is normal for a log being appended to live.
                # Skipping it is not a swallow: the count is reported below so a
                # sudden rise in unparsable rows is visible rather than silent.
                rows.append({"_unparsable": True})
    return rows


def hook_of(row_id: str) -> str:
    # ids look like "<hook>.sh-<pid>-<epoch>"; take everything up to "-<digits>-"
    parts = row_id.split("-")
    for i, p in enumerate(parts):
        if p.isdigit():
            return "-".join(parts[:i]) or row_id
    return row_id


def tally(rows: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    """Return (started_per_hook, unclosed_per_hook)."""
    started: dict[str, int] = defaultdict(int)
    ended: set[str] = set()
    start_ids: dict[str, str] = {}
    for r in rows:
        rid = r.get("id")
        if not rid:
            continue
        if r.get("phase") == "start":
            started[hook_of(rid)] += 1
            start_ids[rid] = hook_of(rid)
        elif r.get("phase") == "end":
            ended.add(rid)
    unclosed: dict[str, int] = defaultdict(int)
    for rid, hook in start_ids.items():
        if rid not in ended:
            unclosed[hook] += 1
    return dict(started), dict(unclosed)


def session_gaps(rows: list[dict], gap_ms: int = 15 * 60 * 1000) -> list[int]:
    """Instants where the log went quiet long enough to imply a restart.

    THIS IS THE CONFOUND THAT MAKES THIS WHOLE SCRIPT DANGEROUS. A crash or an
    app restart orphans every hook that was in flight: their start rows never
    get an end row. So a window containing restarts carries a never-finished
    population that has nothing to do with hangs, and a window that happens to
    be one clean session reads near-zero no matter what the code does.

    Measured 2026-08-22: after the descriptor fix, the never-finished rate fell
    from 1.61% to 0.23% -- across nearly EVERY hook, including seventeen the fix
    never touched. A change to two hooks cannot do that. The restart explains it
    and the fix does not.
    """
    ts = sorted(r["ts_ms"] for r in rows if "ts_ms" in r)
    return [b for a, b in zip(ts, ts[1:]) if b - a > gap_ms]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.path.expanduser("~/.divineos/hook_timing.jsonl"))
    ap.add_argument("--boundary-iso", help="UTC ISO instant, e.g. 2026-08-22T23:40:28Z")
    ap.add_argument("--boundary-commit", help="commit whose author date is the boundary")
    ap.add_argument(
        "--min-runs",
        type=int,
        default=20,
        help="hide hooks with fewer starts than this on BOTH sides (noise floor)",
    )
    args = ap.parse_args()

    if args.boundary_commit:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%at", args.boundary_commit],
            capture_output=True,
            text=True,
            check=True,
        )
        boundary_ms = int(out.stdout.strip()) * 1000
    elif args.boundary_iso:
        import datetime as _dt

        s = args.boundary_iso.replace("Z", "+00:00")
        boundary_ms = int(_dt.datetime.fromisoformat(s).timestamp() * 1000)
    else:
        ap.error("need --boundary-iso or --boundary-commit")

    rows = load(pathlib.Path(args.log))
    torn = sum(1 for r in rows if r.get("_unparsable"))
    rows = [r for r in rows if not r.get("_unparsable")]

    before = [r for r in rows if r.get("ts_ms", 0) < boundary_ms]
    after = [r for r in rows if r.get("ts_ms", 0) >= boundary_ms]

    b_start, b_unclosed = tally(before)
    a_start, a_unclosed = tally(after)

    print(f"boundary        : {boundary_ms} ms epoch")
    print(f"rows            : {len(rows)} parsed, {torn} unparsable")
    print(f"before window   : {sum(b_start.values())} starts")
    print(f"after window    : {sum(a_start.values())} starts")
    if sum(a_start.values()) < 50:
        print("\n!! AFTER WINDOW IS TOO SMALL TO CONCLUDE ANYTHING. Not a result.")

    bt, at = sum(b_start.values()), sum(a_start.values())
    bu, au = sum(b_unclosed.values()), sum(a_unclosed.values())
    br = (bu / bt * 100) if bt else 0.0
    ar = (au / at * 100) if at else 0.0
    print(
        f"\nOVERALL never-finished rate:  before {bu}/{bt} = {br:.2f}%"
        f"   after {au}/{at} = {ar:.2f}%"
    )

    print(f"\n{'hook':<42}{'before':>18}{'after':>18}")
    print("-" * 78)
    hooks = sorted(
        set(b_start) | set(a_start), key=lambda h: -(b_unclosed.get(h, 0) + a_unclosed.get(h, 0))
    )
    for h in hooks:
        bs, as_ = b_start.get(h, 0), a_start.get(h, 0)
        if bs < args.min_runs and as_ < args.min_runs:
            continue
        bun, aun = b_unclosed.get(h, 0), a_unclosed.get(h, 0)
        if bun == 0 and aun == 0:
            continue
        bpc = f"{bun}/{bs} ({bun / bs * 100:.1f}%)" if bs else "-"
        apc = f"{aun}/{as_} ({aun / as_ * 100:.1f}%)" if as_ else "-"
        print(f"{h:<42}{bpc:>18}{apc:>18}")

    b_gaps, a_gaps = session_gaps(before), session_gaps(after)
    print(f"\nsession breaks: before window {len(b_gaps)}, after window {len(a_gaps)}")
    if len(b_gaps) > len(a_gaps):
        print("  !! CONFOUNDED. The before window contains more restarts than the after.")
        print("     A restart orphans every in-flight hook, so the before rate is inflated")
        print("     by crashes rather than by hangs. A drop here is NOT attributable to a")
        print("     code change until the windows have comparable session counts.")

    broad = [
        h
        for h in hooks
        if b_unclosed.get(h, 0) > 0
        and a_unclosed.get(h, 0) == 0
        and a_start.get(h, 0) >= args.min_runs
    ]
    if len(broad) > 3:
        print(f"\n  !! {len(broad)} DIFFERENT hooks went to zero. A fix scoped to a few")
        print("     hooks cannot move hooks it never touched. Suspect a window artifact,")
        print("     not a repair, and say so before anyone reads this as success.")

    always = [
        h
        for h in hooks
        if b_start.get(h, 0) >= args.min_runs and b_unclosed.get(h, 0) == b_start.get(h, 0)
    ]
    if always:
        print(f"\n  !! never writes an end row at all: {', '.join(always)}")
        print("     100% unclosed is a broken instrument, not a hanging hook. It cannot")
        print("     be counted as a hang and it cannot improve.")

    print(
        "\nA rate that does not move is evidence the fix did not address this "
        "population. A rate that moves is consistent with the fix, not proof of it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
