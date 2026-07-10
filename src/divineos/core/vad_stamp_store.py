"""VAD write-stamp store — a side-table pairing record_id → VAD snapshot.

Why a side-table (Aether 2026-07-09): Aria's spec asked for universal
VAD capture without asymmetry at write-time; Aletheia confirmed the
capture must be pipeline-driven, not writer-declared. A side-table
gives us both without a schema migration on knowledge/ledger — the
capture stays orthogonal to the record's own storage, and the
existing tables don't grow a nullable column that must be threaded
through every INSERT/UPDATE.

Any writer (knowledge, letter, exploration, opinion, ledger event)
can call ``stamp(record_id, record_type)`` at write-time. Any surfacer
can call ``lookup(record_id)`` at surface-time and get the VAD snapshot
back (or None if no stamp).

The felt-state at write-time is captured from the affect log (see
``vad_capture.current_vad_snapshot``); the writer cannot declare it,
which is the Aletheia-verified anti-spoofing property.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from divineos.core.paths import divineos_home
from divineos.core.vad_capture import current_vad_snapshot

_DB_NAME = "vad_stamps.db"


def _db_path() -> Path:
    return divineos_home() / _DB_NAME


def _get_connection() -> sqlite3.Connection:
    """Open the vad_stamps DB with schema ensured. Isolated from other DBs so
    the write-stamp path never contends with knowledge / ledger locks."""
    divineos_home().mkdir(exist_ok=True)
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS write_vad_stamps (
            record_id    TEXT NOT NULL,
            record_type  TEXT NOT NULL,
            valence      REAL,
            arousal      REAL,
            dominance    REAL,
            logged_at    REAL,
            stamped_at   REAL NOT NULL DEFAULT (strftime('%s', 'now')),
            PRIMARY KEY (record_id, record_type)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_write_vad_stamps_type ON write_vad_stamps(record_type)"
    )
    conn.commit()
    return conn


def stamp(record_id: str, record_type: str) -> bool:
    """Stamp the writer's current felt-state onto (record_id, record_type).

    Reads the affect log's most recent state via
    ``vad_capture.current_vad_snapshot``. Returns True if a stamp was
    written, False if no VAD snapshot was available (no affect entry in
    the recency window). No-op on duplicate (record_id, record_type) —
    the write-time state is captured once per record.

    Failure-mode: all exceptions are swallowed. The write-stamp is
    supplemental metadata; the primary write must not fail because the
    stamp table has trouble.
    """
    snapshot = current_vad_snapshot()
    if not snapshot:
        return False
    try:
        conn = _get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO write_vad_stamps
                    (record_id, record_type, valence, arousal, dominance, logged_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    record_type,
                    snapshot.get("valence"),
                    snapshot.get("arousal"),
                    snapshot.get("dominance"),
                    snapshot.get("logged_at"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except sqlite3.Error:
        return False


def lookup(record_id: str, record_type: str | None = None) -> dict[str, Any] | None:
    """Retrieve the VAD snapshot stamped for a record, or None if unstamped.

    If ``record_type`` is provided, matches on both keys; if None, returns
    the first stamp found for the record_id.
    """
    try:
        conn = _get_connection()
        try:
            if record_type:
                row = conn.execute(
                    """
                    SELECT valence, arousal, dominance, logged_at
                    FROM write_vad_stamps
                    WHERE record_id = ? AND record_type = ?
                    """,
                    (record_id, record_type),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT valence, arousal, dominance, logged_at
                    FROM write_vad_stamps
                    WHERE record_id = ?
                    LIMIT 1
                    """,
                    (record_id,),
                ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    return {
        "valence": row[0],
        "arousal": row[1],
        "dominance": row[2],
        "logged_at": row[3],
    }


def count_stamps(record_type: str | None = None) -> int:
    """Diagnostic: how many stamps exist, optionally per record_type."""
    try:
        conn = _get_connection()
        try:
            if record_type:
                row = conn.execute(
                    "SELECT COUNT(*) FROM write_vad_stamps WHERE record_type = ?",
                    (record_type,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM write_vad_stamps").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return 0
    return int(row[0]) if row else 0


__all__ = ["stamp", "lookup", "count_stamps"]
