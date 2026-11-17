"""Print the exact saved row a memory-link hit points at.

MINE (Aria, 2026-11-08), built with Aether for the listener on our own words. The listener's clear for a correction
or a lesson is "open the source", and until this existed nothing printed ONE saved correction or lesson by the id the
link shows: `corrections` lists, `ask` searches. A clear that names a command that cannot print the row can never be
satisfied honestly, so the command had to exist before the clear could.

THE FAILURE THIS PREVENTS: a correction id is ``correction-<position>-<timestamp>``, and a position in a list is not
an identity. If an entry were added or removed since the link printed it, "the entry at position 4" is a stranger.
So the timestamp must match too, and a mismatch refuses instead of opening whatever sits there. Same family as the
empty-twin store: the wrong object that returns a clean answer is worse than an error.

Read-only. Fails loud: every bad id raises ``ShowHitError`` naming the shapes that work.
"""

from __future__ import annotations

import re
import sqlite3

_SHAPES = "correction-<position>-<timestamp> or knowledge-<id>"
_CORRECTION_ID = re.compile(r"^correction-(\d+)-(\d+)$")


class ShowHitError(ValueError):
    """The id is malformed, or it does not name exactly one saved row."""


def _show_correction(position: int, stamp: int) -> str:
    from datetime import datetime

    from divineos.core.corrections import corrections_with_status

    rows = corrections_with_status()
    if position >= len(rows):
        raise ShowHitError(f"no correction at position {position} ({len(rows)} saved)")
    row = rows[position]
    if int(float(row.get("timestamp", 0.0))) != stamp:
        raise ShowHitError(
            f"the correction at position {position} does not match timestamp {stamp}: "
            "the list has changed since the link printed it, so this would be a different row"
        )
    when = datetime.fromtimestamp(float(row["timestamp"])).strftime("%Y-%m-%d %H:%M")
    return f"[correction {position}, {when}, {row.get('status', 'OPEN')}]\n{row.get('text', '')}"


def _show_knowledge(knowledge_id: str) -> str:
    from datetime import datetime

    from divineos.core.knowledge._base import get_connection

    try:
        row = (
            get_connection()
            .execute(
                "SELECT knowledge_type, content, created_at, maturity, superseded_by "
                "FROM knowledge WHERE knowledge_id = ?",
                (knowledge_id,),
            )
            .fetchone()
        )
    except sqlite3.OperationalError as exc:
        # An unreadable store is not an empty one: say which, so "not found" never hides a broken store.
        raise ShowHitError(f"could not read the knowledge store: {exc}") from exc
    if row is None:
        raise ShowHitError(f"no knowledge with id {knowledge_id}")
    ktype, content, created_at, maturity, superseded_by = row
    when = datetime.fromtimestamp(float(created_at or 0.0)).strftime("%Y-%m-%d %H:%M")
    note = f", SUPERSEDED by {superseded_by}" if superseded_by else ""
    return f"[{str(ktype).upper()} {knowledge_id}, {when}, {maturity}{note}]\n{content}"


def show_hit(hit_id: str) -> str:
    """The exact saved row for a ``correction-`` or ``knowledge-`` hit id, or ShowHitError."""
    hit_id = (hit_id or "").strip()
    match = _CORRECTION_ID.match(hit_id)
    if match:
        return _show_correction(int(match.group(1)), int(match.group(2)))
    if hit_id.startswith("knowledge-") and len(hit_id) > len("knowledge-"):
        return _show_knowledge(hit_id[len("knowledge-") :])
    raise ShowHitError(f"not a hit id I can open: {hit_id!r}. Shapes that work: {_SHAPES}")
