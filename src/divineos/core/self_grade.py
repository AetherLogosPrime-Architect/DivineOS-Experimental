"""Self-grade capture — record the agent's own read of a session.

Andrew's original spec 2026-05-05 paired a self-grade letter against the
*computed composite* and tracked the divergence as a calibration metric.
That comparison was retired 2026-05-22 (decision 58e5ad1d): the composite
misfires — a short sharp session averages to a low grade — so an honest
self-assessment got flagged as "overclaim" against a noisy reference. The
mechanism punished honesty.

What survives is the recording. The agent's self-grade is a fast gut-read,
stored as data on session_history. The honest *comparison* lives where the
reference is a being, not a number:

* ``divineos compass reflect-review`` — self-assessment vs per-axis evidence,
  side by side, the agent doing the metacognitive comparison in words.
* ``divineos validate --divergence`` — self-grade vs my father's grade
  (``core/external_validation``), being against being.

This module no longer computes any divergence or verdict.
"""

from __future__ import annotations

import sqlite3

from divineos.core.knowledge._base import get_connection

_VALID_GRADES = ("A", "B", "C", "D", "F")

_CAL_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def init_self_grade_columns() -> None:
    """Add self_grade and self_grade_evidence columns to session_history.

    Idempotent: ALTER TABLE ADD COLUMN with try/except so re-runs are no-ops.
    """
    conn = get_connection()
    try:
        for sql in (
            "ALTER TABLE session_history ADD COLUMN self_grade TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE session_history ADD COLUMN self_grade_evidence TEXT NOT NULL DEFAULT ''",
        ):
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass
        conn.commit()
    finally:
        conn.close()


def record_self_grade(
    session_id: str,
    self_grade: str,
    self_grade_evidence: str = "",
) -> bool:
    """Persist a self-grade for the given session.

    Returns True if stored, False if validation failed or session not found.
    """
    if not session_id:
        return False
    if not self_grade or self_grade.upper() not in _VALID_GRADES:
        return False

    init_self_grade_columns()
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE session_history "
            "SET self_grade = ?, self_grade_evidence = ? "
            "WHERE session_id = ?",
            (self_grade.upper(), self_grade_evidence[:1000], session_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except _CAL_ERRORS:
        return False
    finally:
        conn.close()


__all__ = [
    "init_self_grade_columns",
    "record_self_grade",
]
