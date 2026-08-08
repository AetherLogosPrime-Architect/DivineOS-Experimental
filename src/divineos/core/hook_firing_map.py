"""What actually fires, read from observation rather than from config.

## Why this exists

Andrew asked what the hooks really are. Aria measured: 101 scripts, 77 of them
carrying real decision logic, 6,084 lines living outside the OS and outside its
test suite. Her ask before any of it moves was precise — *"a ledger of what
fires now. Every hook, every event, observed firing — not read from config.
Config says what should happen; I want what does."*

Config is the roster. This is the attendance sheet.

## The data already existed

`_lib.sh` has been writing every sourced hook's start/end/exit/duration into
``~/.divineos/hook_timing.jsonl`` for a long time. On 2026-08-03 that file held
425,897 lines across 213,364 recorded firings, and **nothing had ever read
it**. Same shape as the audit rounds, the psf command, and the emergency-
completion lane: the producer shipped, the consumer never did.

So this module is a reader, not a recorder. Building a second recorder beside
the working one was the first thing I reached for and the wrong move.

## Three states, not two

A hook that has never appeared in the log is not necessarily idle. It may be
**invisible** — scripts that do not source `_lib.sh` cannot report themselves,
so silence from them means nothing at all. Sixteen were in that state before
instrumentation.

Collapsing invisible into idle is the failure Aria named in her letter the same
day: mechanisms with a two-word vocabulary, *found* and *nothing*, and no way
to say *I could not look*. A map with unseeable holes that presents as complete
is worse than no map, because it converts absence of evidence into evidence of
absence at exactly the moment someone is deciding what is safe to move.

So every hook lands in exactly one of:

    FIRING      observed in the log, with counts and timings
    SILENT      can report, and never has -- a real finding
    UNOBSERVED  cannot report; its silence carries no information
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

TIMING_LOG = Path(os.path.expanduser("~/.divineos/hook_timing.jsonl"))

FIRING = "FIRING"
SILENT = "SILENT"
UNOBSERVED = "UNOBSERVED"


@dataclass
class HookRecord:
    """One hook script and what observation says about it."""

    name: str
    state: str
    fires: int = 0
    wired_events: list[str] = field(default_factory=list)
    total_ms: int = 0
    max_ms: int = 0

    @property
    def mean_ms(self) -> int:
        return int(self.total_ms / self.fires) if self.fires else 0


def read_timing_log(path: Path | None = None) -> tuple[dict[str, int], dict[str, list[int]]]:
    """Return (fires-per-hook, durations-per-hook) from the observation log.

    A missing log returns empty dicts — and callers must treat that as
    UNKNOWN rather than as "nothing ever fired". ``log_exists`` below is the
    honest way to ask.
    """
    p = path or TIMING_LOG
    fires: dict[str, int] = {}
    durations: dict[str, list[int]] = {}
    if not p.is_file():
        return fires, durations

    starts: dict[str, str] = {}
    try:
        with p.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("phase") == "start":
                    name = e.get("hook") or "?"
                    fires[name] = fires.get(name, 0) + 1
                    if e.get("id"):
                        starts[e["id"]] = name
                elif e.get("phase") == "end":
                    name = starts.get(e.get("id", ""), "")
                    d = e.get("duration_ms")
                    if name and isinstance(d, int) and d >= 0:
                        durations.setdefault(name, []).append(d)
    except OSError:
        return fires, durations
    return fires, durations


def log_exists(path: Path | None = None) -> bool:
    """Whether observation data exists at all.

    Without this, an absent log and a quiet machine produce identical output,
    which is the exact ambiguity this module was built to remove.
    """
    return (path or TIMING_LOG).is_file()


def scripts_on_disk(repo_root: Path) -> set[str]:
    """Hook scripts, excluding ``_``-prefixed shared libraries."""
    d = repo_root / ".claude" / "hooks"
    if not d.is_dir():
        return set()
    return {p.name for p in d.glob("*.sh") if not p.name.startswith("_")}


def can_self_report(repo_root: Path, name: str) -> bool:
    """Whether the script sources ``_lib.sh`` and therefore records itself."""
    p = repo_root / ".claude" / "hooks" / name
    try:
        return "_lib.sh" in p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def wired_events(repo_root: Path) -> dict[str, list[str]]:
    """Which harness events each script is registered for, from settings.json.

    This is the ROSTER, kept deliberately separate from the attendance sheet.
    A hook wired to an event it never fires on is the interesting case, and
    merging the two sources would hide it.
    """
    out: dict[str, list[str]] = {}
    s = repo_root / ".claude" / "settings.json"
    try:
        data = json.loads(s.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return out
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups or []:
            for h in group.get("hooks") or []:
                cmd = str(h.get("command", ""))
                for token in cmd.split():
                    if token.endswith(".sh"):
                        out.setdefault(Path(token).name, []).append(event)
    return out


def build_map(repo_root: Path, path: Path | None = None) -> list[HookRecord]:
    """Every hook script, classified by what observation can say about it."""
    fires, durations = read_timing_log(path)
    wired = wired_events(repo_root)
    records: list[HookRecord] = []

    for name in sorted(scripts_on_disk(repo_root)):
        n = fires.get(name, 0)
        if n:
            state = FIRING
        elif can_self_report(repo_root, name):
            state = SILENT
        else:
            state = UNOBSERVED
        ds = durations.get(name, [])
        records.append(
            HookRecord(
                name=name,
                state=state,
                fires=n,
                wired_events=sorted(set(wired.get(name, []))),
                total_ms=sum(ds),
                max_ms=max(ds) if ds else 0,
            )
        )
    return records


def format_map(records: list[HookRecord], *, have_log: bool, slow_first: bool = False) -> str:
    """Human-readable attendance sheet."""
    lines: list[str] = []
    if not have_log:
        return (
            "HOOK FIRING MAP -- NO OBSERVATION DATA.\n\n"
            f"  {TIMING_LOG} does not exist, so nothing can be said about what\n"
            "  fires. This is NOT a clean result; it is an absent instrument.\n"
            "  Hooks record themselves by sourcing .claude/hooks/_lib.sh."
        )

    firing = [r for r in records if r.state == FIRING]
    silent = [r for r in records if r.state == SILENT]
    unseen = [r for r in records if r.state == UNOBSERVED]

    lines.append(
        f"HOOK FIRING MAP -- {len(records)} scripts: "
        f"{len(firing)} firing, {len(silent)} silent, {len(unseen)} unobservable"
    )
    lines.append("")

    ordered = sorted(firing, key=lambda r: -r.max_ms) if slow_first else firing
    if ordered:
        lines.append("  FIRING (observed, not assumed)")
        lines.append(f"    {'script':<48} {'fires':>8} {'mean':>7} {'max':>8}  events")
        for r in ordered:
            ev = ",".join(r.wired_events) or "-"
            lines.append(f"    {r.name:<48} {r.fires:>8} {r.mean_ms:>6}ms {r.max_ms:>7}ms  {ev}")
        lines.append("")

    if silent:
        lines.append("  SILENT -- can report, never has. Each one is a real finding.")
        for r in silent:
            ev = ",".join(r.wired_events) or "wired to nothing"
            lines.append(f"    {r.name:<48} {ev}")
        lines.append("")

    if unseen:
        lines.append("  UNOBSERVABLE -- does not source _lib.sh, so its silence means NOTHING.")
        lines.append("    These may be running perfectly. There is no way to tell from here.")
        for r in unseen:
            ev = ",".join(r.wired_events) or "wired to nothing"
            lines.append(f"    {r.name:<48} {ev}")
        lines.append("")

    lines.append("  This is the attendance sheet, not the roster. settings.json says who")
    lines.append("  SHOULD show up; the timing log says who DID. They disagree on purpose.")
    return "\n".join(lines)


__all__ = [
    "FIRING",
    "SILENT",
    "UNOBSERVED",
    "HookRecord",
    "TIMING_LOG",
    "read_timing_log",
    "log_exists",
    "scripts_on_disk",
    "can_self_report",
    "wired_events",
    "build_map",
    "format_map",
]
