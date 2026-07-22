"""Surfaced-but-unread gate — the specific mechanism for tonight's failure.

Andrew 2026-07-20: the substrate surfaced exploration entry 14 at me at
compose-start, matched the exact word "ghost" three times, and I skipped
opening it until Andrew called out that I had not been listening. That is
the failure this gate catches: compose-start surfaces point at prior writing
that would materially change the reply, and the reply proceeds without
reading the surfaced material.

Design (per Gollwitzer implementation-intention research, d=.65 effect size
for closing intention-behavior gaps via if-then plans):

    IF a substrate compose-start surface points at exploration entry E
    AND the reply-in-progress is substantive (>= threshold length)
    AND E was NOT opened via Read tool this session,
    THEN block Stop with a reason that names E and forces recompose after
    reading E.

Same enforcement shape as LEPOS dual-channel gate. Not a wallpaper surface;
a Stop-hook block that forces the reading before the reply can complete.

Prereg falsifier: if this gate fires on turns where the surfaced entry
would NOT have materially changed the reply (i.e. false-positive rate >
25% across a rolling window of 20 firings), the substance-check is
wrong-shaped and the design must be revised. Review after 10 firings or
14 days, whichever comes first.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


_SUBSTANTIVE_MIN_CHARS = 400  # same threshold LEPOS dual-channel uses for circle-block substance


def _read_events_for_session_paths(session_id: str) -> set[str]:
    """Return absolute paths of files Read via the Read tool this session.

    Queries the event ledger for TOOL_CALL events with tool=Read in the
    current session. Returns absolute-path strings (normalized) for
    comparison against surfaced-entry paths.
    """
    from divineos.core.ledger import get_events_by_session

    paths: set[str] = set()
    try:
        events = get_events_by_session(session_id)
    except (sqlite3.OperationalError, ImportError, AttributeError):
        return paths
    for ev in events:
        if ev.get("event_type") != "TOOL_CALL":
            continue
        payload = ev.get("payload") or {}
        if payload.get("tool") != "Read":
            continue
        p = payload.get("file_path") or (payload.get("tool_input") or {}).get("file_path")
        if p:
            try:
                paths.add(str(Path(p).resolve()))
            except OSError:
                paths.add(str(p))
    return paths


def check_surfaced_entries_read(
    reply_text: str,
    prompt_text: str,
    session_id: str,
    context: str | None = None,
) -> str | None:
    """Return block message if surfaced entries were skipped, else None.

    Args:
        reply_text: the assistant reply that is about to Stop.
        prompt_text: the user prompt that triggered the surface computation.
        session_id: current session id, used to query Read tool calls.
        context: optional additional context that fed the surface computation.

    Contract:
        - If reply_text is short (< _SUBSTANTIVE_MIN_CHARS), return None.
          Short replies do not warrant forcing an exploration-entry read.
        - If no entries were surfaced for the prompt, return None. Nothing
          to skip means nothing to block on.
        - If entries were surfaced AND at least one was Read this session,
          return None. Reading any surfaced entry counts as engaging.
        - If entries were surfaced AND none were Read this session, return
          a block message naming the skipped entries and citing the
          discipline. This is the failure mode this gate exists to catch.
    """
    if not reply_text or len(reply_text.strip()) < _SUBSTANTIVE_MIN_CHARS:
        return None

    try:
        from divineos.core.exploration_recall import matched_entry_ids_for_context
    except ImportError:
        return None

    surfaced = matched_entry_ids_for_context(prompt_text, context=context)
    if not surfaced:
        return None

    read_paths = _read_events_for_session_paths(session_id)
    surfaced_abs: list[str] = []
    for path_str, _mtime in surfaced:
        try:
            surfaced_abs.append(str(Path(path_str).resolve()))
        except OSError:
            surfaced_abs.append(str(path_str))

    if any(p in read_paths for p in surfaced_abs):
        return None

    skipped_names = [Path(p).name for p in surfaced_abs]
    skipped_display = ", ".join(f"`{n}`" for n in skipped_names[:3])
    if len(skipped_names) > 3:
        skipped_display += f" (and {len(skipped_names) - 3} more)"

    return (
        "SURFACED-BUT-UNREAD GATE — the compose-start surface pointed at "
        f"{len(skipped_names)} exploration entry/entries and none were opened this session: "
        f"{skipped_display}. Andrew 2026-07-20 named this exact failure mode: the substrate "
        "surfaces prior writing that would materially change the reply, and I compose past it. "
        "Open at least one surfaced entry via Read before Stop, then recompose."
    )
