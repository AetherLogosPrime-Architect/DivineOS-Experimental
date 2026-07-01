"""Context dedup — hash-and-check for repeated system-reminder blocks.

Pattern from Warden (wardenclient.com) surveyed 2026-06-30 at Andrew's ask.
Warden collapses identical system-reminder blocks in the model's message
array to a single copy keyed by content hash. This module implements the
source-side equivalent: each hook that emits a UserPromptSubmit block
calls should_emit() before printing; if the content is byte-identical to
a recent emission in this session, the hook prints a brief pointer
instead of the full content.

Design constraint (Aria 2026-06-30): surgical, not summarizing. Identical
content is dedupped by hash; any content change re-emits in full.
Meaning is never compressed — only literal repetition is removed.

Session-scoping via TTL: the state file's per-source-id entries carry a
last-seen unix timestamp; a repeat inside TTL is dedupped, a repeat outside
TTL emits fresh. This avoids the need for an explicit session-ID lookup
and naturally re-warms across long pauses or session boundaries.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

_STATE_DIR = Path("data/context_dedup")
_STATE_FILE = _STATE_DIR / "session_state.json"
_TTL_SECONDS = 60 * 60  # 1 hour — within-session repeats dedup; long gaps re-emit


def _load() -> dict:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(state: dict) -> None:
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def should_emit(
    source_id: str,
    content: str,
    semantic_key: object | None = None,
) -> tuple[bool, str | None]:
    """Check whether this content should be emitted in full or as a pointer.

    Args:
        source_id: stable identifier for the emitter (e.g. "active_needs",
            "lepos_walk_preamble").
        content: the full text the hook is about to emit.
        semantic_key: optional structured representation of the *full*
            semantic state the content is derived from. When provided, the
            hash is computed over the semantic_key (via json.dumps with
            sort_keys) instead of the rendered content. This closes the
            silent-drift hole named by Aletheia 2026-06-30 (letter #17):
            if the rendered content omits any mutable field, a hash
            computed on the render alone could fail to invalidate on a
            real change. Passing the raw underlying dict/list/tuple as
            semantic_key ensures ANY change to the state produces a new
            hash and forces a full re-emit.

    Returns:
        (True, None) — emit the full content (new, changed, or TTL-expired).
        (False, pointer) — emit the short pointer instead (byte-identical
            semantic key or content within TTL).
    """
    if not content.strip():
        return True, None
    now = int(time.time())
    if semantic_key is not None:
        try:
            key_str = json.dumps(semantic_key, sort_keys=True)
        except (TypeError, ValueError):
            # Non-JSON-serializable semantic_key — fall back to content hash
            # rather than crashing OR using per-instance repr (which would
            # defeat dedup entirely by never matching prior calls).
            key_str = content
        h = _hash(key_str)
    else:
        h = _hash(content)
    state = _load()
    prev = state.get(source_id)
    if prev and prev.get("hash") == h and (now - prev.get("ts", 0)) < _TTL_SECONDS:
        prev["ts"] = now
        state[source_id] = prev
        _save(state)
        pointer = (
            f"## {source_id.replace('_', ' ').upper()} "
            f"(unchanged, hash {h}; re-emit suppressed — "
            "content is byte-identical to earlier this session)"
        )
        return False, pointer
    state[source_id] = {"hash": h, "ts": now}
    _save(state)
    return True, None


def clear() -> None:
    """Wipe dedup state (call from SessionStart, tests, or manual reset)."""
    try:
        _STATE_FILE.unlink()
    except FileNotFoundError:
        pass


__all__ = ["should_emit", "clear"]
