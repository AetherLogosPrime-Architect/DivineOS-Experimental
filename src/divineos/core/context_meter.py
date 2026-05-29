"""Read true context-window fullness from the Claude Code transcript.

``pre_erasure.py`` estimates approach-to-compaction from proxies — tool
count, edits, and wall-clock elapsed (the wrong axis: a long-running
session ages those out while real fullness is low, and vice versa). The
real signal lives in the transcript: each assistant turn records
``message.usage`` with the token counts the model actually saw. The sum
of the *input-side* counts (fresh input + cache-created + cache-read) is
the context-window occupancy for that turn; ``output_tokens`` is
generation, not occupancy, so it is excluded.

This module reads that ground-truth number so the governor can fire the
pre-compaction save EARLY — at a token threshold, with time to finish —
instead of relying on the last-second PreCompact hook, which was measured
on 2026-05-29 to need ~64s against a (then) 15s timeout and lost a full
day's work when it was killed mid-save.

This module is read-only and inert on its own: it computes a reading and
returns it. Acting on the reading (firing the save) is the governor's
job, wired separately, so the measurement stays testable in isolation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Claude Code begins compaction near this fill. Keep the fire-threshold
# meaningfully below it so a ~60s save has room to finish before the
# ceiling forces compaction.
COMPACTION_CEILING_TOKENS = 970_000

# Fire the early-save once occupancy crosses this fraction of the ceiling.
DEFAULT_FIRE_THRESHOLD = 0.85


@dataclass
class ContextReading:
    """A single reading of context-window fullness from the transcript."""

    context_tokens: int
    ceiling: int
    pct: float
    over_threshold: bool
    source_line: int  # 0-based transcript line the reading came from (forensic)


def _context_tokens_from_usage(usage: dict) -> int:
    """Context-window occupancy for one turn = everything the model READ:
    fresh input + cache-created + cache-read. ``output_tokens`` is what the
    model generated, not what occupied the window, so it is excluded."""
    return (
        int(usage.get("input_tokens", 0) or 0)
        + int(usage.get("cache_creation_input_tokens", 0) or 0)
        + int(usage.get("cache_read_input_tokens", 0) or 0)
    )


def read_latest_context_tokens(
    transcript_path: Path,
    *,
    ceiling: int = COMPACTION_CEILING_TOKENS,
    fire_threshold: float = DEFAULT_FIRE_THRESHOLD,
) -> ContextReading | None:
    """Return the most-recent context-fullness reading from a transcript.

    Scans from the end for the latest assistant-message ``usage`` block
    (the current turn's occupancy). Returns ``None`` if the file is
    unreadable or contains no usable usage block — callers treat ``None``
    as "no signal", never as "empty/zero", so a parse failure can't be
    misread as "plenty of room".
    """
    try:
        lines = transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for idx in range(len(lines) - 1, -1, -1):
        line = lines[idx]
        if '"usage"' not in line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        tokens = _context_tokens_from_usage(usage)
        if tokens <= 0:
            continue
        pct = tokens / ceiling if ceiling > 0 else 0.0
        return ContextReading(
            context_tokens=tokens,
            ceiling=ceiling,
            pct=pct,
            over_threshold=pct >= fire_threshold,
            source_line=idx,
        )

    return None


def format_reading(reading: ContextReading | None) -> str:
    """One-line human summary for a vitals/HUD surface."""
    if reading is None:
        return "context fullness: no signal (transcript unreadable or no usage yet)"
    bar_pct = int(round(reading.pct * 100))
    flag = "  [!] over early-save threshold" if reading.over_threshold else ""
    return (
        f"context fullness: {reading.context_tokens:,} / {reading.ceiling:,} tokens "
        f"({bar_pct}%){flag}"
    )
