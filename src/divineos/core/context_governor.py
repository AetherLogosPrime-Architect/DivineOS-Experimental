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
CONSOLIDATION_THRESHOLD = 920_000
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


__all__ = [
    "COMPACTION_CEILING",
    "CONSOLIDATION_THRESHOLD",
    "clear_consolidated",
    "consolidation_due",
    "current_context_tokens",
    "is_consolidated",
    "mark_consolidated",
]
