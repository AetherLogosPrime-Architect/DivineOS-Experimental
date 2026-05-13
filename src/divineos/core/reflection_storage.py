"""Reflection storage — per-axis honest reflection capture.

Phase 2A of the shoggoth-metrics redesign. See
exploration/44_shoggoth_metrics_redesign.md for the full design spec.

## What this stores

Per-session, per-axis: the agent's honest reflection text + evidence
references the agent named when reflecting.

## What this does NOT do

- Does NOT grade the reflection. The substrate's job is to store what
  the agent said, not to judge it.
- Does NOT compute alignment with measured patterns. That's Phase 2C
  (after-the-fact alignment check).
- Does NOT extract knowledge from reflections automatically. The
  reflection is the agent's own substrate-knowledge filing if the
  agent chooses to file it via the regular `learn` path.

## Schema

```
session_reflections(
    reflection_id   TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    recorded_at     REAL NOT NULL,
    spectrum        TEXT NOT NULL,
    reflection_text TEXT NOT NULL,
    evidence_refs   TEXT NOT NULL  -- JSON list of evidence pointers
)
```

Indexed on session_id and spectrum for the common query paths
(retrieve session's reflections, watch trend on one axis).
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger

from divineos.core.knowledge import _get_connection
from divineos.core.moral_compass import SPECTRUMS


@dataclass(frozen=True)
class Reflection:
    """One captured reflection on one axis for one session."""

    reflection_id: str
    session_id: str
    recorded_at: float
    spectrum: str
    reflection_text: str
    evidence_refs: list[dict[str, Any]]


# ─── Schema ─────────────────────────────────────────────────────────


def init_reflection_table() -> None:
    """Create the session_reflections table. Idempotent."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_reflections (
                reflection_id   TEXT PRIMARY KEY,
                session_id      TEXT NOT NULL,
                recorded_at     REAL NOT NULL,
                spectrum        TEXT NOT NULL,
                reflection_text TEXT NOT NULL,
                evidence_refs   TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reflections_session
            ON session_reflections(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reflections_spectrum
            ON session_reflections(spectrum)
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Reflection table setup: {e}")
    finally:
        conn.close()


# ─── Save ───────────────────────────────────────────────────────────


def save_reflection(
    session_id: str,
    spectrum: str,
    reflection_text: str,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> str:
    """Save one per-axis reflection.

    Returns the reflection_id.

    Raises ValueError if spectrum is not a known compass spectrum.
    """
    if spectrum not in SPECTRUMS:
        valid = ", ".join(sorted(SPECTRUMS.keys()))
        msg = f"Unknown spectrum '{spectrum}'. Valid: {valid}"
        raise ValueError(msg)

    if not reflection_text.strip():
        msg = "Reflection text cannot be empty — substrate stores what the agent said, not silence."
        raise ValueError(msg)

    init_reflection_table()

    rid = f"refl-{uuid.uuid4().hex[:12]}"
    refs_json = json.dumps(evidence_refs or [])

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO session_reflections "
            "(reflection_id, session_id, recorded_at, spectrum, "
            "reflection_text, evidence_refs) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rid, session_id, time.time(), spectrum, reflection_text, refs_json),
        )
        conn.commit()
    finally:
        conn.close()
    return rid


# ─── Retrieve ───────────────────────────────────────────────────────


def get_reflections_for_session(session_id: str) -> list[Reflection]:
    """Return all reflections for one session, ordered by spectrum."""
    init_reflection_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT reflection_id, session_id, recorded_at, spectrum, "
            "reflection_text, evidence_refs "
            "FROM session_reflections "
            "WHERE session_id = ? "
            "ORDER BY spectrum, recorded_at",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    return [_row_to_reflection(r) for r in rows]


def get_recent_reflections(spectrum: str, limit: int = 10) -> list[Reflection]:
    """Return recent reflections on one axis across sessions.

    For trend-watching: how did the agent reflect on truthfulness over
    the last 10 sessions, for example.
    """
    if spectrum not in SPECTRUMS:
        return []

    init_reflection_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT reflection_id, session_id, recorded_at, spectrum, "
            "reflection_text, evidence_refs "
            "FROM session_reflections "
            "WHERE spectrum = ? "
            "ORDER BY recorded_at DESC "
            "LIMIT ?",
            (spectrum, limit),
        ).fetchall()
    finally:
        conn.close()

    return [_row_to_reflection(r) for r in rows]


def _row_to_reflection(row: tuple[Any, ...]) -> Reflection:
    """Convert a database row to a Reflection."""
    try:
        refs = json.loads(row[5]) if row[5] else []
    except (json.JSONDecodeError, TypeError):
        refs = []

    return Reflection(
        reflection_id=row[0],
        session_id=row[1],
        recorded_at=row[2],
        spectrum=row[3],
        reflection_text=row[4],
        evidence_refs=refs,
    )


# ─── Formatting ─────────────────────────────────────────────────────


def format_reflection(refl: Reflection) -> str:
    """Format one reflection as displayable text."""
    spec = SPECTRUMS.get(refl.spectrum, {})
    virtue = spec.get("virtue", refl.spectrum)

    lines = [
        f"  {refl.spectrum.upper()} ({virtue}):",
        f"    [{refl.reflection_id[:8]}] {refl.reflection_text}",
    ]
    if refl.evidence_refs:
        lines.append("    evidence:")
        for ref in refl.evidence_refs:
            ref_type = ref.get("type", "ref")
            ref_id = ref.get("id", "")
            ref_label = ref.get("label", "")
            lines.append(f"      [{ref_type}:{ref_id}] {ref_label}")
    return "\n".join(lines)


def format_session_reflections(session_id: str) -> str:
    """Format all reflections for a session as displayable text."""
    refls = get_reflections_for_session(session_id)

    if not refls:
        return f"No reflections recorded for session {session_id[:12]}..."

    header = [
        "=" * 60,
        f"REFLECTIONS — session {session_id[:12]}...",
        "=" * 60,
        "",
    ]

    # Group by spectrum
    by_spectrum: dict[str, list[Reflection]] = {}
    for r in refls:
        by_spectrum.setdefault(r.spectrum, []).append(r)

    blocks = []
    for spectrum in SPECTRUMS:
        if spectrum in by_spectrum:
            for r in by_spectrum[spectrum]:
                blocks.append(format_reflection(r))
                blocks.append("")

    if not blocks:
        blocks = ["(no reflections matched known spectrums)"]

    return "\n".join(header + blocks)
