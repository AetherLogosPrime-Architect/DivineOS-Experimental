"""Bounded rotation for the flat append-only logs, with the by-absence signal preserved.

WHY THIS EXISTS

Measured 2026-08-18: the DivineOS home was 444MB and 229MB of it was three flat
logs that had never been rotated, because nothing existed to rotate them.

    hook_timing.jsonl     136MB   1,068,639 lines
    hook-liveness.log      50MB     455,715 lines
    retrieval_tally.jsonl  43MB       4,141 lines

`ledger_compressor` has pruned the ledger DATABASE on a conveyor belt for
months. The flat logs sitting beside it had no equivalent and nobody noticed,
because a file growing without bound looks exactly like a file being used.

WHY A NAIVE TRUNCATE WOULD DESTROY SOMETHING

`hook_timing.jsonl` is the instrument that answers *which hooks have NEVER
run* — and it answers by ABSENCE. Two verifiers were found silent across 652
runs of their parent precisely because nothing about them appeared in this
file. Keep only a recent tail and that question stops being answerable: a hook
that stopped running in June becomes indistinguishable from one that never
existed.

So rotation here is not truncation. Every rotation first folds the file into a
ROSTER — one row per hook, cumulative across all rotations, holding first-seen,
last-seen and counts. The roster is small, permanent, and never rotated. The
detailed rows stay bounded; the by-absence question moves to the roster, where
it is answered better than before, because the roster survives while the rows
do not.

The general rule: **a log may be bounded only once the questions it answers
have somewhere else to live.**

Shape borrowed deliberately from `ledger_compressor`, which summarizes into a
LEDGER_COMPACTION event before deleting and then emits an auditable record of
the repair. Same discipline, different substrate: fold first, delete second,
log the fold. A deletion nobody can audit is indistinguishable from data loss.

FILTER-SHAPE VS TAIL-SHAPE — two defects, two policies

  - TAIL: rows are all equally interesting and only volume is the problem
    (hook_timing, retrieval_tally). Keep the newest N, fold the rest.

  - FILTER: the log's own stated purpose names a minority of its rows as the
    signal and the rest is noise. `hook-liveness.log` exists to answer "which
    session-init children FAILED, with exit code and error text", and
    essentially all of its 455,715 rows say `healthy_source`. That is the same
    shape as the `failures/` directory found holding successes earlier the same
    day: a surface whose name and contents disagree. Keep every non-healthy row
    forever; fold the healthy ones into per-hook counts.

SCOPE. The ledger and knowledge store are append-only and are NOT touched here.
CLAUDE.md hard rule 4 scopes operational telemetry out of that rule explicitly,
and these three files are exactly that.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from divineos.core.paths import divineos_home

# `<hook>-<pid>-<ts_ms>` — the id format written by .claude/hooks/_lib.sh.
# End-rows carry only this id and no `hook` field, so the name is recovered from
# it. Getting this wrong once, in a throwaway analysis, made all 128 hooks look
# as though they had never completed. The roster is only as honest as this line.
_TIMING_ID_RE = re.compile(r"^(.*?)-\d+-\d+$")

# What can go wrong reading a log line or a roster file: unreadable/absent file
# (OSError), malformed JSON (ValueError — json.JSONDecodeError subclasses it),
# a row that parsed but is not the shape expected (TypeError), or bytes that are
# not valid text (UnicodeDecodeError). Named rather than caught broadly so a
# genuinely unexpected failure still surfaces instead of being folded into
# "assume empty" — the shape that lets a rotation quietly lose a roster.
_ROTATION_ERRORS = (OSError, ValueError, TypeError, UnicodeDecodeError)

# How many recent rows survive a rotation. Generous on purpose: the goal is to
# stop unbounded growth, not to run a tight ship.
DEFAULT_KEEP_LINES = 40_000

# Below this, rotation is a no-op — it would cost more than it saves and would
# churn an mtime that other surfaces read as activity.
DEFAULT_MIN_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class RotationResult:
    """What one rotation actually did. Every field measured, none intended."""

    name: str
    rotated: bool
    reason: str
    bytes_before: int
    bytes_after: int
    lines_before: int
    lines_after: int
    roster_entries: int

    @property
    def bytes_saved(self) -> int:
        return max(0, self.bytes_before - self.bytes_after)


def _timing_hook_name(row: dict[str, Any]) -> str | None:
    """Hook name for a timing row, from `hook` or recovered from `id`."""
    hook = row.get("hook")
    if hook:
        return str(hook)
    match = _TIMING_ID_RE.match(str(row.get("id") or ""))
    return match.group(1) if match else None


def _fold_timing(row: dict[str, Any], roster: dict[str, Any]) -> None:
    name = _timing_hook_name(row)
    if not name:
        return
    entry = roster.setdefault(name, {"starts": 0, "ends": 0, "first_ms": None, "last_ms": None})
    phase = row.get("phase")
    if phase == "start":
        entry["starts"] += 1
    elif phase == "end":
        entry["ends"] += 1
    ts = row.get("ts_ms")
    if isinstance(ts, (int, float)):
        if entry["first_ms"] is None or ts < entry["first_ms"]:
            entry["first_ms"] = ts
        if entry["last_ms"] is None or ts > entry["last_ms"]:
            entry["last_ms"] = ts


def _fold_counter(row: dict[str, Any], roster: dict[str, Any]) -> None:
    """Per-subject, per-reason tallies — the shape liveness rows fold into."""
    name = str(row.get("hook") or "unknown")
    reason = str(row.get("reason") or "unknown")
    entry = roster.setdefault(name, {})
    entry[reason] = int(entry.get(reason, 0)) + 1


def _fold_rowcount(row: dict[str, Any], roster: dict[str, Any]) -> None:
    totals = roster.setdefault("_totals", {})
    totals["rows"] = int(totals.get("rows", 0)) + 1


def _liveness_is_signal(row: dict[str, Any]) -> bool:
    """Keep a liveness row verbatim unless it says nothing happened.

    The log's stated purpose is failures. `healthy_source` is the heartbeat and
    is preserved as a count in the roster rather than as half a million lines.
    """
    return str(row.get("reason") or "") != "healthy_source"


@dataclass(frozen=True)
class LogPolicy:
    """How one named log is bounded, and what its rows fold into."""

    filename: str
    fold: Callable[[dict[str, Any], dict[str, Any]], None]
    cumulative: bool = False  # True when roster entries are summed across rotations
    keep_lines: int = DEFAULT_KEEP_LINES
    keep_if: Callable[[dict[str, Any]], bool] | None = None
    note: str = ""


POLICIES: tuple[LogPolicy, ...] = (
    LogPolicy(
        filename="hook_timing.jsonl",
        fold=_fold_timing,
        cumulative=True,
        note="by-absence instrument: the roster is what answers 'never ran'",
    ),
    LogPolicy(
        filename="hook-liveness.log",
        fold=_fold_counter,
        keep_if=_liveness_is_signal,
        note="failures are the signal; healthy_source is only the heartbeat",
    ),
    LogPolicy(
        filename="retrieval_tally.jsonl",
        fold=_fold_rowcount,
        keep_lines=2_000,
        note="rows embed whole surfaced-path lists; the volume is per-row, not per-line",
    ),
)


def roster_path(home: Path, filename: str) -> Path:
    """Where a log's permanent roster lives. Never rotated."""
    return home / f"{filename}.roster.json"


def _load_roster(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except _ROTATION_ERRORS:
        return {}
    return data if isinstance(data, dict) else {}


def _merge_timing(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Cumulative merge — a roster that forgot on rotation would be pointless."""
    merged = dict(old)
    for name, entry in new.items():
        prior = merged.get(name)
        if not isinstance(prior, dict):
            merged[name] = entry
            continue
        combined = dict(prior)
        for key in ("starts", "ends"):
            combined[key] = int(prior.get(key, 0)) + int(entry.get(key, 0))
        for key, pick in (("first_ms", min), ("last_ms", max)):
            values = [v for v in (prior.get(key), entry.get(key)) if v is not None]
            combined[key] = pick(values) if values else None
        merged[name] = combined
    return merged


def _merge_counter(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {k: (dict(v) if isinstance(v, dict) else v) for k, v in old.items()}
    for name, counts in new.items():
        if not isinstance(counts, dict):
            merged[name] = counts
            continue
        target = merged.get(name)
        if not isinstance(target, dict):
            target = merged[name] = {}
        for reason, count in counts.items():
            target[reason] = int(target.get(reason, 0)) + int(count)
    return merged


def _atomic_write(path: Path, text: str) -> None:
    """Temp file in the same directory, then replace.

    A half-written roster is worse than no roster, and a half-written log is
    worse than a large one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:  # noqa: BLE001 - re-raised; this only removes the temp file
        # Deliberately broad AND deliberately re-raising: the only job here is
        # to not leave a half-written .tmp behind, whatever went wrong. Narrowing
        # it would leak temp files on the failures it did not name.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def rotate_log(
    policy: LogPolicy,
    home: Path | None = None,
    min_bytes: int = DEFAULT_MIN_BYTES,
    dry_run: bool = False,
) -> RotationResult:
    """Fold one log into its roster, then keep only the recent tail.

    Order is not negotiable: the roster is written AND read back before the log
    is replaced. A crash between the two loses recent rows, which is recoverable
    noise. The reverse order would lose the roster, which cannot be rebuilt once
    the rows are gone.
    """
    home = home or divineos_home()
    path = home / policy.filename
    if not path.exists():
        return RotationResult(policy.filename, False, "missing", 0, 0, 0, 0, 0)

    size = path.stat().st_size
    if size < min_bytes:
        return RotationResult(
            policy.filename, False, f"under {min_bytes} bytes", size, size, 0, 0, 0
        )

    fresh: dict[str, Any] = {}
    kept: list[str] = []
    lines_before = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            lines_before += 1
            try:
                row = json.loads(stripped)
            except _ROTATION_ERRORS:
                # Unparseable rows are kept verbatim rather than dropped. Twenty
                # of them existed at first measurement; they are evidence of a
                # writer bug, and silently eating them would erase the only
                # trace that the bug happened.
                kept.append(stripped)
                if len(kept) > policy.keep_lines:
                    kept.pop(0)
                continue
            if isinstance(row, dict):
                policy.fold(row, fresh)
                if policy.keep_if is not None:
                    if policy.keep_if(row):
                        kept.append(stripped)  # signal rows are never dropped
                    continue
            kept.append(stripped)
            if len(kept) > policy.keep_lines:
                kept.pop(0)

    rpath = roster_path(home, policy.filename)
    merger = _merge_timing if policy.cumulative else _merge_counter
    merged = merger(_load_roster(rpath), fresh)

    if dry_run:
        after = sum(len(line) + 1 for line in kept)
        return RotationResult(
            policy.filename, False, "dry-run", size, after, lines_before, len(kept), len(merged)
        )

    _atomic_write(rpath, json.dumps(merged, indent=1, sort_keys=True))
    if not _load_roster(rpath):
        # Fail toward keeping data: the log is untouched and the next run retries.
        return RotationResult(
            policy.filename, False, "roster write failed", size, size, lines_before, 0, 0
        )

    _atomic_write(path, "\n".join(kept) + ("\n" if kept else ""))
    return RotationResult(
        policy.filename,
        True,
        policy.note or "rotated",
        size,
        path.stat().st_size,
        lines_before,
        len(kept),
        len(merged),
    )


def rotate_all(
    home: Path | None = None,
    min_bytes: int = DEFAULT_MIN_BYTES,
    dry_run: bool = False,
) -> list[RotationResult]:
    """Rotate every registered log. One measured result per policy."""
    return [rotate_log(p, home=home, min_bytes=min_bytes, dry_run=dry_run) for p in POLICIES]


def hooks_never_completed(home: Path | None = None) -> dict[str, int]:
    """Hooks the roster has seen start and never seen finish.

    This is the question the timing log exists to answer and the reason the
    roster exists at all — it stays answerable after the detailed rows are gone.
    """
    home = home or divineos_home()
    roster = _load_roster(roster_path(home, "hook_timing.jsonl"))
    out: dict[str, int] = {}
    for name, entry in roster.items():
        if not isinstance(entry, dict):
            continue
        starts, ends = int(entry.get("starts", 0)), int(entry.get("ends", 0))
        if starts and not ends:
            out[name] = starts
    return out
