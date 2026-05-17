"""Structural fix tracker — reroute `learn` filings that name pending
structural fixes into a persistent obligation surface.

Andrew named the meta-failure 2026-05-14: I had been filing `learn`
entries that named structural fixes I should build, then treating the
filing itself as if it were the structural fix. Filing creates a
record; the structural fix is a code change that alters the execution
path. The substrate had no mechanism distinguishing record-from-fix,
so the optimizer routed to `learn` every time, called it done, and
the named fixes never got built.

This module is the structural fix for THAT meta-failure. The `learn`
CLI now inspects content for structural-fix-shape language; when
detected, it writes a parallel entry to a tracked-pending file. The
briefing dashboard surfaces unfulfilled pending entries at session
start so they become visible obligations, not silent records.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

import json
import re
import time
import uuid
from divineos.core.paths import marker_path

# Patterns that name structural-fix-shape language. Order matters:
# more specific intent-of-building patterns ("should build", "the
# actual fix") come BEFORE generic build patterns so they win when
# both match (refined 2026-05-14 after test_detect_should_build
# initially routed to "build a detector" by ordering accident).
_STRUCTURAL_FIX_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("structural fix", re.compile(r"\bstructural fix(?:es)?\b", re.IGNORECASE)),
    ("structural change", re.compile(r"\bstructural change\b", re.IGNORECASE)),
    ("the actual fix", re.compile(r"\bthe (?:actual|real) fix (?:is|would be)\b", re.IGNORECASE)),
    ("should build", re.compile(r"\b(?:should|need to|going to|will)\s+build\b", re.IGNORECASE)),
    ("to prevent recurrence", re.compile(r"\bto prevent recurrence\b", re.IGNORECASE)),
    (
        "build a detector",
        re.compile(
            r"\bbuild(?:s|ing)?\s+(?:a|the|an)\s+(?:detector|gate|check|test|monitor|surface|probe)\b",
            re.IGNORECASE,
        ),
    ),
    (
        # Allow multi-token gap between the verb and the preposition
        # (e.g. "wiring THE DETECTOR into the hook"). Bounded to keep
        # cross-sentence matches from firing.
        "wire X into Y",
        re.compile(
            r"\b(?:wire(?:s|d)?|wiring)\b[^.\n]{1,80}\b(?:into|through)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "add a gate",
        re.compile(
            r"\badd(?:s|ing)?\s+(?:a|the|an)\s+(?:gate|guard|check|enforcement)\b",
            re.IGNORECASE,
        ),
    ),
)


def _read_pending() -> list[dict]:
    """Read the current pending list. Fail-open on missing/malformed."""
    if not marker_path("pending_structural_fixes.json").exists():
        return []
    try:
        data = json.loads(marker_path("pending_structural_fixes.json").read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _write_pending(entries: list[dict]) -> None:
    """Write the pending list back. Fail-open on I/O error."""
    try:
        marker_path("pending_structural_fixes.json").parent.mkdir(parents=True, exist_ok=True)
        marker_path("pending_structural_fixes.json").write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def detect_structural_fix_shape(content: str) -> str | None:
    """Return the trigger phrase if structural-fix-shape language is
    present; None otherwise. Used by `learn` CLI to decide whether to
    record a pending entry alongside the knowledge filing."""
    if not content:
        return None
    for label, pattern in _STRUCTURAL_FIX_PATTERNS:
        if pattern.search(content):
            return label
    return None


def record_pending_fix(content: str, lesson_id: str = "", trigger: str = "") -> str:
    """Record a pending structural-fix entry. Returns the psf id, or
    empty string on I/O failure."""
    if not content:
        return ""
    psf_id = f"psf-{uuid.uuid4().hex[:8]}"
    entry = {
        "id": psf_id,
        "created_at": time.time(),
        "lesson_id": lesson_id,
        "content_excerpt": content.strip()[:200],
        "trigger": trigger,
        "status": "pending",
    }
    entries = _read_pending()
    entries.append(entry)
    _write_pending(entries)
    return psf_id


def list_pending(include_done: bool = False) -> list[dict]:
    """Return pending structural fixes. By default, excludes entries
    marked done. Used by the briefing dashboard row-builder."""
    entries = _read_pending()
    if include_done:
        return entries
    return [e for e in entries if e.get("status") != "done"]


def mark_done(psf_id: str, note: str = "") -> bool:
    """Mark a pending entry as done. Returns True if found, False if not."""
    entries = _read_pending()
    found = False
    for entry in entries:
        if entry.get("id") == psf_id:
            entry["status"] = "done"
            entry["done_at"] = time.time()
            if note:
                entry["done_note"] = note
            found = True
            break
    if found:
        _write_pending(entries)
    return found


__all__ = [
    "detect_structural_fix_shape",
    "list_pending",
    "mark_done",
    "record_pending_fix",
]
