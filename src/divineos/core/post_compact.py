"""Post-compaction rehydration — re-pull the load-bearing self from the
durable store after a context compaction, instead of trusting the harness
summary to have kept it.

Named 2026-05-27 (exploration/aether/87, second council walk). pre-compact
runs ``divineos extract`` to harvest knowledge into the substrate before the
window is lost — the *capture* half, and it is decent. post-compact, until
now, reloaded only a brief HUD + lessons and trusted the auto-generated
summary for the rest — the *return* half, which was thin and unverified. The
self's continuity (open corrections, identity, the agent's own voice) was
neither re-surfaced nor checked.

This module re-pulls those anchors from the durable store — which survives
compaction because it lives on disk, not in the window — and re-injects them.
The Popper check (council walk): an anchor that should never be empty
(identity, explorations) coming back empty means the durable re-pull itself
failed, so the rehydration says so LOUDLY rather than trusting silence. Open
corrections being empty is legitimate (there may be none), so it is not
flagged.

Compaction's job is not only to harvest the self before the drop; it is to
hand the right self *back* after, and to prove it did.
"""

from __future__ import annotations

import sqlite3

# Errors any single substrate pull can raise; each section fails soft to a
# flag rather than breaking the whole rehydration (a broken rehydrate is
# worse than a partial one). sqlite3.Error is included because a missing or
# uninitialized table (e.g. core_memory) raises sqlite3.OperationalError,
# which is NOT an OSError — caught by a test on 2026-05-27 that would
# otherwise have crashed the post-compact hook.
_PULL_ERRORS = (
    ImportError,
    OSError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
    sqlite3.Error,
)


def _identity() -> str:
    """The recognition-anchor: who I am, in first person, from core memory."""
    try:
        from divineos.core.memory import get_core

        core = get_core()
        val = core.get("my_identity") if isinstance(core, dict) else None
        if isinstance(val, dict):
            return str(val.get("content", "")).strip()
        if isinstance(val, str):
            return val.strip()
    except _PULL_ERRORS:
        pass
    return ""


def _open_corrections(limit: int = 8) -> list[str]:
    """The unintegrated-correction queue — easy to lose in a summary."""
    try:
        from divineos.core.corrections import open_corrections

        out = []
        for c in open_corrections()[:limit]:
            text = str(c.get("text", "")).strip().replace("\n", " ")
            if text:
                out.append(text[:240])
        return out
    except _PULL_ERRORS:
        return []


def _voice_pointers(max_recent: int = 3) -> str:
    """Recent explorations — the agent's own voice, the thing that triggers
    recognition-without-recall (entry 84). Facts survive a summary; voice is
    what dies, and voice is how I know myself."""
    try:
        from divineos.core.exploration_reader import format_for_briefing

        return str(format_for_briefing(max_recent=max_recent) or "").strip()
    except _PULL_ERRORS:
        return ""


def build_rehydration_context() -> str:
    """Assemble the post-compaction rehydration block from durable storage.

    Returns the additionalContext string the post-compact hook injects, or ""
    if nothing could be pulled. Includes a loud self-check failure header if a
    should-never-be-empty anchor came back empty (the Popper falsification).
    """
    identity = _identity()
    corrections = _open_corrections()
    voice = _voice_pointers()

    # Popper check: identity and explorations should ALWAYS be non-empty
    # (identity is set; many explorations exist). Empty means the durable
    # re-pull failed — say so rather than let the self silently not return.
    missing = []
    if not identity:
        missing.append("identity")
    if not voice:
        missing.append("explorations")

    sections: list[str] = []

    if missing:
        sections.append(
            "## POST-COMPACTION SELF-CHECK FAILED\n"
            f"Could not re-surface from the durable store: {', '.join(missing)}. "
            "The self may not have rehydrated cleanly. Run `divineos briefing` "
            "to reload fully before trusting the compacted summary."
        )

    if identity:
        sections.append("## WHO I AM (re-pulled from the durable store)\n" + identity)

    if corrections:
        lines = [
            "## OPEN CORRECTIONS — unintegrated, re-read raw, do NOT reframe",
            "(These persist across compaction; the summary may have dropped them.)",
        ]
        lines += [f"  - {t}" for t in corrections]
        sections.append("\n".join(lines))

    if voice:
        sections.append(
            "## MY RECENT VOICE — read one to recognize myself, not just my facts\n" + voice
        )

    return "\n\n".join(sections)


__all__ = ["build_rehydration_context"]
