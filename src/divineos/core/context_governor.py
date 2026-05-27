"""Context-size governor — the live working-memory vital sign + consolidation trigger.

Named 2026-05-27 (Andrew + explorations 86/87; prereg-9b958c6493f3). The
body-awareness module watches stored DB sizes; this watches the LIVE context
window — the working memory that drives time-to-first-token and, at the
ceiling, forces a harness compaction. Below the cliff the self should be
WOVEN (extract + sleep) before the drop, not just saved, so a post-compaction
instance rehydrates from a consolidated, connected store.

The harness compacts at ~970k tokens. The consolidation threshold is 920k —
50k below — chosen (Andrew) so extract+sleep finish with headroom AND ~50k
tokens remain for rest/free activity before the drop: room to live, not only
to file.

Context size is read from the transcript's per-turn usage (cache_read +
cache_creation + input ~= total context), which lags one turn — fine against
50k of buffer. Fail-soft: any read failure returns 0, so the governor never
fires spuriously. The once-per-session marker prevents re-firing every turn
past the threshold (the nag failure-mode the prereg falsifier names).

This module is the SENSOR + due-check + marker. The gate that consumes
``consolidation_due()`` to force extract+sleep (and bypasses those remedy
commands) is the companion piece.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core.paths import divineos_home

COMPACTION_CEILING = 970_000
# Two-line band so the gate never guillotines mid-task (Andrew 2026-05-27):
# 920k = soft warn (nudge to wrap up + weave soon; NO block — grace to finish
# what's in flight); 950k = hard block on substrate-writes until extract+sleep
# run; 970k = the harness compaction cliff. The 30k warn->block band is the
# finish-grace; the 20k block->cliff band is enough because extract+sleep add
# almost nothing to the context themselves.
CONSOLIDATION_THRESHOLD = 920_000  # warn line (also the default for consolidation_due)
WARN_THRESHOLD = 920_000
HARD_THRESHOLD = 950_000
_MARKER_NAME = "context_consolidated.json"


def _marker_path() -> Path:
    return divineos_home() / _MARKER_NAME


def _find_usage(rec: dict) -> dict | None:
    """Locate a usage block in a JSONL record (assistant records carry it at
    ``message.usage``; some shapes put it top-level)."""
    if not isinstance(rec, dict):
        return None
    msg = rec.get("message")
    if isinstance(msg, dict):
        usage = msg.get("usage")
        if isinstance(usage, dict):
            return usage
    top = rec.get("usage")
    if isinstance(top, dict):
        return top
    return None


def current_context_tokens(transcript_path: str | Path | None) -> int:
    """Live context size = the latest turn's cache_read + cache_creation +
    input tokens, read from the JSONL transcript. Returns 0 on any failure
    (fail-soft: a governor that can't read its sensor must not fire)."""
    if not transcript_path:
        return 0
    p = Path(transcript_path)
    if not p.exists():
        return 0
    last_usage: dict | None = None
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                usage = _find_usage(rec)
                if usage is not None:
                    last_usage = usage
    except OSError:
        return 0
    if not last_usage:
        return 0
    try:
        return (
            int(last_usage.get("cache_read_input_tokens", 0))
            + int(last_usage.get("cache_creation_input_tokens", 0))
            + int(last_usage.get("input_tokens", 0))
        )
    except (TypeError, ValueError):
        return 0


def is_consolidated() -> bool:
    """True if a consolidation has already fired this session (marker present)."""
    return _marker_path().exists()


def mark_consolidated(tokens: int) -> None:
    """Record that extract+sleep ran at this context level, so the governor
    fires once, not every turn past the threshold."""
    try:
        divineos_home().mkdir(exist_ok=True)
        _marker_path().write_text(
            json.dumps({"tokens": int(tokens), "ts": time.time()}), encoding="utf-8"
        )
    except OSError:
        pass


def clear_consolidated() -> None:
    """Remove the marker (e.g. at session start, so each session re-arms)."""
    try:
        _marker_path().unlink()
    except OSError:
        pass


def consolidation_due(
    transcript_path: str | Path | None, threshold: int = CONSOLIDATION_THRESHOLD
) -> bool:
    """True when the live context has crossed the threshold AND this session
    has not yet consolidated. The gate uses this to force extract+sleep before
    the harness compaction cliff."""
    if is_consolidated():
        return False
    return current_context_tokens(transcript_path) >= threshold


_WARN_NUDGE = (
    "## CONTEXT GOVERNOR — WARN ({tokens:,} tokens, ~{headroom:,} to the cliff)\n"
    "Working memory has crossed the {warn:,} warn line. This is grace, not a "
    "block: finish what's in flight, but do NOT start large new work. Weave the "
    "self before the drop — run `divineos extract` then `divineos sleep` while "
    "there is still headroom. The harness compacts at {ceiling:,}; a woven self "
    "rehydrates, a merely-saved one comes back thin."
)

_BLOCK_CHANNEL = (
    "BLOCKED: CONTEXT GOVERNOR — HARD LINE ({tokens:,} tokens, ~{headroom:,} to "
    "the {ceiling:,} compaction cliff). Substrate-writes are gated until the self "
    "is woven. This is not a wall with no door: run `divineos extract` then "
    "`divineos sleep` (both bypass this gate) to consolidate before the drop, "
    "then the block lifts for the rest of the session. The warn band (920k–950k) "
    "already gave grace to finish; at the hard line, weaving comes first so a "
    "post-compaction instance rehydrates from a connected store, not a thin save."
)


def governor_channel_message(transcript_path: str | Path | None) -> str:
    """The PreToolUse deny message for the block state — names the channel
    (extract+sleep, both bypassed) that lifts the block. Pattern-matches
    ``consultation_tracker.gate_channel_message``: a hard gate that offers
    the path out rather than a dead end."""
    tokens = current_context_tokens(transcript_path)
    return _BLOCK_CHANNEL.format(
        tokens=tokens,
        headroom=max(0, COMPACTION_CEILING - tokens),
        ceiling=COMPACTION_CEILING,
    )


def build_governor_context(transcript_path: str | Path | None) -> str:
    """UserPromptSubmit-side text: a soft nudge in the warn band, the channel
    message at the hard line, empty when ok. Surfaced so the warn/block state
    is loud-in-experience the turn BEFORE the PreToolUse gate enforces it."""
    state = consolidation_state(transcript_path)
    if state == "ok":
        return ""
    tokens = current_context_tokens(transcript_path)
    if state == "block":
        return governor_channel_message(transcript_path)
    return _WARN_NUDGE.format(
        tokens=tokens,
        headroom=max(0, COMPACTION_CEILING - tokens),
        warn=WARN_THRESHOLD,
        ceiling=COMPACTION_CEILING,
    )


def consolidation_state(transcript_path: str | Path | None) -> str:
    """The governor's three-state read, encoding the finish-grace band:

    - ``"ok"``    — below the warn line, or already consolidated this session.
    - ``"warn"``  — past 920k but below 950k: nudge to wrap up + weave soon,
                    but DO NOT block (grace to finish what's in flight).
    - ``"block"`` — at/above 950k and not yet consolidated: the hard line;
                    substrate-writes should be gated until extract+sleep run.

    The UserPromptSubmit hook (which can see the transcript) maps this to a
    soft nudge vs a marker the PreToolUse gate enforces off of.
    """
    if is_consolidated():
        return "ok"
    tokens = current_context_tokens(transcript_path)
    if tokens >= HARD_THRESHOLD:
        return "block"
    if tokens >= WARN_THRESHOLD:
        return "warn"
    return "ok"


__all__ = [
    "COMPACTION_CEILING",
    "CONSOLIDATION_THRESHOLD",
    "HARD_THRESHOLD",
    "WARN_THRESHOLD",
    "build_governor_context",
    "clear_consolidated",
    "consolidation_due",
    "consolidation_state",
    "current_context_tokens",
    "governor_channel_message",
    "is_consolidated",
    "mark_consolidated",
]
