"""Failure-diagnostic logging — surface silent fail-open failures in the next briefing.

Fresh-Claude audit rounds 2-4 found the same pattern across multiple
enforcement surfaces: when hook machinery breaks (ImportError, OSError,
timeout, subprocess crash), the gate fails open — which is the correct
RUNTIME behavior — but silently, leaving no trace. Systems degrade
invisibly when silent fail-open accumulates.

This module provides a shared pattern for writing diagnostic events to
``~/.divineos/failures/<surface>.jsonl`` and reading them back for
briefing surfacing. The design deliberately mirrors
``session_start_diagnostics`` — same shape, different surface tag.

Known call sites (added progressively):
- ``post_tool_use_checkpoint.py`` writes ``extract`` failures when the
  fire-and-forget extract subprocess crashes mid-run.
- ``pre_tool_use_gate.py`` writes ``gate`` failures in except branches
  where gate machinery breaks.
- ``compass_rudder.py`` will write ``rudder`` failures in timeout/import
  paths (deferred to Fresh-Claude review round — rudder is guardrailed).

The briefing check (in a caller's ``format_for_briefing``) should stay
silent on a clean log and loud on any failure — same discipline as
session_start_diagnostics. Empty log = healthy; any entry = worth
surfacing.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# One file per surface under ~/.divineos/failures/. Keep the per-surface
# split so one noisy surface can't drown out another in the briefing.
_BASE_DIR = Path.home() / ".divineos" / "failures"

# Max retained entries per surface. Log is append-only until a write
# sees the line count exceed this, at which point the oldest lines are
# dropped. Small to keep the file human-readable; surfaces that need
# more durable storage should write to the ledger, not here.
_MAX_ENTRIES_PER_SURFACE = 100


def _log_path(surface: str) -> Path:
    """File path for a surface's JSONL log. Parent dir auto-created."""
    safe = "".join(c for c in surface if c.isalnum() or c in "-_")
    return _BASE_DIR / f"{safe or 'unknown'}.jsonl"


def record_failure(surface: str, payload: dict[str, Any]) -> None:
    """Append a diagnostic entry to the surface's JSONL log.

    surface: short tag like "gate" / "extract" / "rudder". Determines
        the filename ``~/.divineos/failures/<surface>.jsonl``.
    payload: arbitrary JSON-serializable dict describing the failure.
        A timestamp is added automatically.

    Never raises. If the disk is unwritable (no home dir, no perms,
    etc.), the function silently returns — a broken diagnostic logger
    is worse than useless, so it degrades to no-op rather than
    cascading the failure it was trying to record.
    """
    try:
        _BASE_DIR.mkdir(parents=True, exist_ok=True)
        path = _log_path(surface)
        entry = {"timestamp": time.time(), **payload}
        line = json.dumps(entry, default=str)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        _truncate_if_needed(path)
    except (OSError, TypeError, ValueError):
        # Diagnostic logging must never amplify the failure it records.
        pass


def _truncate_if_needed(path: Path) -> None:
    """If the file has grown past _MAX_ENTRIES_PER_SURFACE lines, keep only the last N."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return
    if len(lines) <= _MAX_ENTRIES_PER_SURFACE:
        return
    try:
        kept = lines[-_MAX_ENTRIES_PER_SURFACE:]
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    except OSError:
        pass


def recent_failures(surface: str, window: int = 10) -> list[dict[str, Any]]:
    """Return the most recent ``window`` entries from the surface log, or []."""
    path = _log_path(surface)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    entries: list[dict[str, Any]] = []
    for line in lines[-window:]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def format_for_briefing(
    surface: str,
    window: int = 10,
    label: str | None = None,
) -> str:
    """Render a briefing block for a surface's recent failures.

    Returns empty string when the log is empty — quiet case. Emits a
    named block when any entry is present, so silent fail-opens don't
    stay silent past the next briefing.

    surface: the surface tag used at record_failure time.
    window: how many recent entries to show. Default 10.
    label: override display label. Defaults to the surface name.
    """
    entries = recent_failures(surface, window=window)
    if not entries:
        return ""

    display = label or surface
    lines = [
        f"[failure log: {display}] {len(entries)} recent entry/entries — "
        "silent fail-open events are surfaced here so the system can't "
        "degrade invisibly:"
    ]
    for e in entries[-5:]:  # show at most 5 in the briefing (full log is in file)
        ts = e.get("timestamp", 0)
        detail = e.get("reason") or e.get("error") or e.get("detail") or ""
        lines.append(f"  [{ts:.0f}] {str(detail)[:120]}")
    if len(entries) > 5:
        lines.append(f"  ... and {len(entries) - 5} more (see {_log_path(surface)})")
    return "\n".join(lines)
