#!/usr/bin/env python3
"""Refusing gates whose refusal sits BEHIND a load that fails open.

THE FAULT, found by Aletheia 2026-09-21 in the emergency stop itself:

    source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0

Exit 0 is ALLOW. So a gate that refuses things will, if that one shared file
cannot be loaded, permit everything instead -- silently, with no line anywhere
saying the check did not run. One file, many gates, including the off-switch.

Her rule from an earlier round, and the reason this is a script rather than a
sentence in a letter: A DETECTOR MAKES IT A PROPERTY. The same rule produced
check_failure_path_refuses.py next door, for the neighbouring class in Python.

WHAT THIS MEASURES, and it is deliberately ORDER rather than presence. Loading
a library that may fail is fine. Loading it BEFORE the gate can reach its own
refusal is the fault, because the refusal is then downstream of something
allowed to vanish. A gate is clean when a refusal is reachable above every
fail-open load.

WHY A BASELINE RATHER THAN A BLANKET REPAIR. The gates sharing this pattern
each need reading: some genuinely need the library to run their check at all,
and for those, failing closed would brick the session including the edit that
repairs the library -- the off-switch-traps-itself shape the corrigibility
module rejects by name. That is a repair per gate, not a sweep. So the
population is pinned: it may shrink, never grow. Same shape and same reason as
the dark-surfaces and orphan-module baselines already in this directory --
visibility was the missing half, and new instances now block rather than
arriving quietly.

WHAT IT CANNOT DECIDE. Whether a given gate SHOULD fail closed. That depends
on what the gate protects and what breaks if it refuses wrongly, which is a
judgement. This decides only where the question arises, and it does that
exhaustively.

Exit 0 when the set has not grown, 1 when it has, 2 when the hooks directory
cannot be read -- which is could-not-look, and must never read as clean.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"
BASELINE = ROOT / "scripts" / "refusal_behind_failsoft_baseline.txt"

# A load whose failure ALLOWS: a source/dot line carrying `|| exit 0`.
_FAIL_OPEN_LOAD = re.compile(r"^\s*(?:source|\.)\s+.*\|\|\s*exit\s+0\b")

# The gate reaching its own refusal: exit 2, the python spelling of it, or a
# JSON permission deny. All three are how a refusal leaves a hook in this house.
_REFUSAL = re.compile(r"^\s*exit\s+2\b|sys\.exit\(\s*2\s*\)|permissionDecision.{0,6}deny")


def _first_line(lines: list[str], pattern: re.Pattern[str]) -> int | None:
    for n, line in enumerate(lines, start=1):
        if pattern.search(line):
            return n
    return None


def refusal_behind_failsoft(path: Path) -> bool | None:
    """True when this file's first refusal sits below its first fail-open load.

    None means COULD NOT READ, and it is a third answer rather than a False.

    I wrote this returning False on the unreadable path, and the staged-lines
    check next door caught it in the same run -- a file nobody could open would
    have counted as a file with nothing wrong. That is the exact conflation
    this whole script exists to find, written into the finder, an hour after
    repairing the same shape in the off-switch. It is the cheapest possible
    demonstration that the pattern is a gradient and not a lapse: knowing it
    cold did not stop my hands producing it.
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    load = _first_line(lines, _FAIL_OPEN_LOAD)
    refusal = _first_line(lines, _REFUSAL)
    if load is None or refusal is None:
        return False
    return refusal > load


def current_set() -> tuple[list[str], list[str]]:
    """``(behind, unreadable)`` -- kept apart, because they mean opposite things."""
    behind: list[str] = []
    unreadable: list[str] = []
    for p in sorted(HOOKS.glob("*.sh")):
        verdict = refusal_behind_failsoft(p)
        if verdict is None:
            unreadable.append(p.name)
        elif verdict:
            behind.append(p.name)
    return behind, unreadable


def baseline_set() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {
        s
        for s in (line.strip() for line in BASELINE.read_text(encoding="utf-8").splitlines())
        if s and not s.startswith("#")
    }


def main() -> int:
    if not HOOKS.is_dir():
        print(
            f"[refusal-order] CANNOT READ {HOOKS} -- this says nothing about the hooks.",
            file=sys.stderr,
        )
        return 2

    now, unreadable = current_set()
    known = baseline_set()
    new = [name for name in now if name not in known]
    fixed = sorted(known - set(now) - set(unreadable))

    if unreadable:
        # Said out loud and kept out of every other tally. A file this could
        # not open is not a file it cleared, and it is not a repair either --
        # folding it into "fixed" would let an unreadable hook quietly leave
        # the baseline and never come back.
        print(f"[refusal-order] COULD NOT READ {len(unreadable)} file(s); they are unjudged:")
        for name in unreadable:
            print(f"    {name}")

    if fixed:
        print(f"[refusal-order] {len(fixed)} repaired since the baseline: {', '.join(fixed)}")
        print("[refusal-order] drop them from the baseline file so the set keeps shrinking.")

    if new:
        print(f"[refusal-order] NEW: {len(new)} refusing gate(s) whose refusal sits behind a")
        print("                load that exits 0 on failure. If that load breaks, these allow.")
        for name in new:
            print(f"    {name}")
        print("[refusal-order] Put the load-bearing check ABOVE the load, the way")
        print("                corrigibility-tool-gate.sh now does, or add a baseline entry")
        print("                saying why this one must keep the order it has.")
        return 1

    print(f"[refusal-order] OK -- {len(now)} known, none new.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
