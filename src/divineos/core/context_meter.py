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


def _reading_from_tokens(
    tokens: int,
    *,
    ceiling: int,
    fire_threshold: float,
    source_line: int,
) -> ContextReading:
    """Build a ContextReading from a token count.

    ## This function exists because I fabricated it

    2026-08-09. Wiring the bounded read, I called `_reading_from_tokens(tokens)`
    without checking it existed. It did not, the import failed, and I filed it
    as the third instance that day of writing against an unverified interface.

    Andrew: *"fabrication is not a sin, same as bypass its a tool.. is about
    awareness, think about why you fabricated what you did, maybe something is
    missing? .. and if something doesnt exist? maybe you need to build it so
    it does exist."*

    Asking that: the reach was right and only the fact was wrong. Adding the
    bounded path gave `read_latest_context_tokens` a SECOND place that turns a
    token count into a reading, identical to the first but for `source_line`.
    My hands reached for the helper that removes that duplication, and the
    duplication was real -- I had just written it. The fabrication was a
    correct design instinct arriving before the code it described.

    So it exists now, and both paths use it. The name is the one I invented,
    kept deliberately: it was the right name, which is the whole point.

    `source_line` is passed rather than inferred because the two callers
    honestly differ -- the full read knows the file offset, a tail view knows
    only its own, and passes -1 rather than a plausible-looking number.
    """
    pct = tokens / ceiling if ceiling > 0 else 0.0
    return ContextReading(
        context_tokens=tokens,
        ceiling=ceiling,
        pct=pct,
        over_threshold=pct >= fire_threshold,
        source_line=source_line,
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
    # 2026-08-09: bounded read. Its own docstring says "scans from the end for
    # the latest" -- and it read the whole file first in order to do that.
    # Third site of the same shape today: pay for all of history, then walk
    # backwards from the end of it.
    #
    # THE FREEZE, measured: 8 Stop hooks each parsing a 67 MB transcript,
    # ~539 MB of disk-and-parse per stop against 1,261 MB of history.
    # transcript_tail.py was written for exactly this on 2026-08-03 and had
    # zero callers until today.
    #
    # Safe by consumer-need: the latest usage block is in the tail by
    # construction. The `truncated` fallback matters MORE here than anywhere
    # else on the board -- this function's own docstring says callers treat
    # None as "no signal, never empty/zero, so a parse failure can't be
    # misread as plenty of room". A short view silently returning None would
    # convert a bounded read into a false all-clear on context fullness,
    # which is the one wrong answer it must never give.
    try:
        from divineos.core.operating_loop.transcript_tail import read_tail_records

        records, truncated = read_tail_records(transcript_path)
    except (OSError, ValueError, ImportError):
        records, truncated = [], True

    for obj in reversed(records):
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        tokens = _context_tokens_from_usage(usage)
        if tokens > 0:
            return _reading_from_tokens(
                tokens,
                ceiling=ceiling,
                fire_threshold=fire_threshold,
                # A tail knows its own offsets, not the file's.
                # -1 is the honest value; see the helper.
                source_line=-1,
            )

    if not truncated:
        return None

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
        return _reading_from_tokens(
            tokens, ceiling=ceiling, fire_threshold=fire_threshold, source_line=idx
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
