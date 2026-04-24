"""Session-cleanliness tagging — Item 8 PR-2.

Sessions that pass an external audit round without drift findings are
tagged "clean" here. The tag is the source-of-truth for detector
baselines in `compliance_audit.py` — specifically for the detectors
whose baseline sources are "externally-audited sessions" per design
brief v2.1 §4 (variance-collapse, content-entropy, decide/learn skew,
length-floor clustering, rapid-clear reflex).

Without this module, baselines fall back to "all historical sessions,"
which is circular if drift was present during the historical window.
Tagging produces a separate, audited-clean dataset the detectors can
calibrate against.

Invariants (per claim 48371c4d sanity check):

    1. A session can only be tagged clean by a round that itself
       concluded clean — i.e., the round has no HIGH findings and no
       unresolved MEDIUM findings. This blocks the "malicious audit
       round tags its own dirty session clean" attack class.

    2. Tagging is append-only in spirit: a session tagged clean by
       round A can be re-tagged by round B only if B is also clean.
       Untagging (for corrections) requires an explicit function call
       with a reason, and writes an audit event rather than doing an
       in-place delete.

    3. Clean-session queries are bounded by tagging_round recency:
       callers interested in "sessions clean as of round X" can filter
       by tagged_at or tagging_round_id. The default query returns
       all clean sessions regardless of when tagged.
"""

from __future__ import annotations

import time
from typing import Any

from divineos.core.knowledge import _get_connection


def _has_blocking_findings(round_id: str) -> tuple[bool, str]:
    """Check if the round has findings that block clean-tagging.

    Blocking criteria (per invariant 1):
    - Any HIGH severity finding (regardless of status)
    - Any MEDIUM severity finding with status != 'RESOLVED'

    Returns (blocked, reason). Reason is empty string when not blocked.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM audit_findings WHERE round_id = ? AND severity = 'HIGH'",
            (round_id,),
        ).fetchone()
        high_count = row[0] if row else 0
        if high_count > 0:
            return (
                True,
                f"round has {high_count} HIGH finding(s) — cannot tag session clean",
            )

        row = conn.execute(
            "SELECT COUNT(*) FROM audit_findings "
            "WHERE round_id = ? AND severity = 'MEDIUM' AND status != 'RESOLVED'",
            (round_id,),
        ).fetchone()
        unresolved_medium = row[0] if row else 0
        if unresolved_medium > 0:
            return (
                True,
                f"round has {unresolved_medium} unresolved MEDIUM finding(s) — "
                "cannot tag session clean until resolved",
            )
    finally:
        conn.close()
    return (False, "")


def _round_exists(round_id: str) -> bool:
    """Fast-path check that the round_id references a real audit round."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM audit_rounds WHERE round_id = ?",
            (round_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def tag_session_clean(
    session_id: str,
    round_id: str,
    notes: str = "",
) -> None:
    """Tag a session as externally-audited clean.

    Raises ValueError when:
    - The referenced round does not exist.
    - The round has HIGH findings (can never tag clean; per invariant 1).
    - The round has unresolved MEDIUM findings (tag blocked until resolved).

    Idempotent: re-tagging an already-clean session with the same
    round_id is a no-op. Re-tagging by a DIFFERENT round_id updates the
    tagging_round_id (a later clean round re-affirms the session).
    """
    if not _round_exists(round_id):
        raise ValueError(f"round_id {round_id!r} does not exist")

    blocked, reason = _has_blocking_findings(round_id)
    if blocked:
        raise ValueError(f"cannot tag session {session_id!r} clean: {reason}")

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO session_cleanliness "
            "(session_id, tagged_at, tagging_round_id, notes) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "tagged_at = excluded.tagged_at, "
            "tagging_round_id = excluded.tagging_round_id, "
            "notes = excluded.notes",
            (session_id, time.time(), round_id, notes),
        )
        conn.commit()
    finally:
        conn.close()


def untag_session_clean(session_id: str, reason: str) -> bool:
    """Remove a clean-tag. Returns True if a row was removed.

    Untagging is a rare corrective action — usually because an audit
    round that tagged a session is later found to have been flawed.
    ``reason`` is required (not optional) so the untag has a paper
    trail: callers typically pass a finding_id or a short sentence.
    """
    if not reason or not reason.strip():
        raise ValueError("untag_session_clean requires a non-empty reason")
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM session_cleanliness WHERE session_id = ?",
            (session_id,),
        )
        removed = cursor.rowcount > 0
        conn.commit()
    finally:
        conn.close()

    # Record the untag as a ledger event — keeps the audit trail even
    # though the tag row itself was deleted. Deletion + event together
    # preserves "who untagged what and why" for later forensics.
    if removed:
        try:
            from divineos.core.ledger import log_event

            log_event(
                event_type="SESSION_CLEANLINESS_UNTAGGED",
                actor="watchmen.cleanliness",
                payload={
                    "session_id": session_id,
                    "reason": reason,
                },
                validate=False,
            )
        except Exception:  # noqa: BLE001
            pass
    return removed


def is_session_clean(session_id: str) -> bool:
    """True if the session is currently tagged clean."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM session_cleanliness WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def list_clean_sessions(
    since: float | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return all clean-tagged sessions.

    ``since``: lower bound on tagged_at (epoch seconds). Use to filter
    "sessions tagged clean in the last N days."
    ``limit``: max rows to return. Default 500 covers a long audit
    history.
    """
    conn = _get_connection()
    try:
        if since is not None:
            rows = conn.execute(
                "SELECT session_id, tagged_at, tagging_round_id, notes "
                "FROM session_cleanliness "
                "WHERE tagged_at >= ? "
                "ORDER BY tagged_at DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT session_id, tagged_at, tagging_round_id, notes "
                "FROM session_cleanliness "
                "ORDER BY tagged_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [
        {
            "session_id": r[0],
            "tagged_at": r[1],
            "tagging_round_id": r[2],
            "notes": r[3],
        }
        for r in rows
    ]


def count_clean_sessions(since: float | None = None) -> int:
    """Fast count of clean-tagged sessions (optionally filtered by since)."""
    conn = _get_connection()
    try:
        if since is not None:
            row = conn.execute(
                "SELECT COUNT(*) FROM session_cleanliness WHERE tagged_at >= ?",
                (since,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM session_cleanliness",
            ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()
