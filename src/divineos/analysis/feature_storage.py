"""Feature Storage — Database setup and persistence for session features.

Extracted from session_features.py.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from divineos.core.fidelity import compute_content_hash
from divineos.core.ledger import get_connection_fk as _get_connection

if TYPE_CHECKING:
    from divineos.analysis.session_features import FullSessionAnalysis


def init_feature_tables() -> None:
    """Create tables for features 3, 5, 6, 8, 9, 10."""
    conn = _get_connection()
    try:
        # Generic feature_result table for storing all feature analysis
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feature_result (
                result_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES session_report(session_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_result_session
            ON feature_result(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_result_name
            ON feature_result(feature_name)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tone_shift (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                sequence       INTEGER NOT NULL,
                timestamp      TEXT NOT NULL,
                previous_tone  TEXT NOT NULL,
                new_tone       TEXT NOT NULL,
                trigger_action TEXT NOT NULL,
                evidence_hash  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tone_shift_session
            ON tone_shift(session_id)
        """)
        # WRITE-ONLY: session_timeline stores per-action sequence data for
        # future cross-session timeline visualization and replay. Not yet
        # read by any query — awaiting a timeline UI or analysis consumer.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_timeline (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                sequence       INTEGER NOT NULL,
                timestamp      TEXT NOT NULL,
                actor          TEXT NOT NULL,
                action_summary TEXT NOT NULL,
                evidence_hash  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_session
            ON session_timeline(session_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_touched (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                file_path      TEXT NOT NULL,
                action         TEXT NOT NULL,
                timestamp      TEXT NOT NULL,
                was_read_first INTEGER NOT NULL,
                tool_use_id    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_touched_session
            ON file_touched(session_id)
        """)
        # WRITE-ONLY: activity_breakdown stores per-session volume metrics for
        # future productivity analysis and session comparison. Not yet read
        # by any query — awaiting a progress/trends consumer.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_breakdown (
                session_id          TEXT PRIMARY KEY,
                total_text_blocks   INTEGER NOT NULL,
                total_tool_calls    INTEGER NOT NULL,
                total_text_chars    INTEGER NOT NULL,
                total_tool_time_seconds REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_tracking (
                session_id      TEXT PRIMARY KEY,
                initial_request TEXT NOT NULL,
                files_changed   INTEGER NOT NULL,
                user_satisfied  INTEGER NOT NULL,
                evidence_hash   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_recovery (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                error_timestamp TEXT NOT NULL,
                tool_name       TEXT NOT NULL,
                error_summary   TEXT NOT NULL,
                recovery_action TEXT NOT NULL,
                evidence_hash   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_recovery_session
            ON error_recovery(session_id)
        """)
        conn.commit()
    finally:
        conn.close()


def store_features(session_id: str, analysis: FullSessionAnalysis) -> None:
    """Store all feature results in the database."""
    conn = _get_connection()
    try:
        # Clear old data for this session
        for table in ("tone_shift", "session_timeline", "file_touched", "error_recovery"):
            conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))  # nosec B608 - table names are hardcoded, session_id passed as parameter
        conn.execute("DELETE FROM activity_breakdown WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM task_tracking WHERE session_id = ?", (session_id,))

        # Tone shifts
        for ts in analysis.tone_shifts:
            evidence = json.dumps(
                {
                    "before": ts.before_message,
                    "after": ts.after_message,
                    "trigger": ts.trigger_action,
                },
                sort_keys=True,
            )
            conn.execute(
                "INSERT INTO tone_shift (session_id, sequence, timestamp, previous_tone, new_tone, trigger_action, evidence_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    ts.sequence,
                    ts.timestamp,
                    ts.previous_tone,
                    ts.new_tone,
                    ts.trigger_action,
                    compute_content_hash(evidence),
                ),
            )

        # Timeline
        for te in analysis.timeline:
            conn.execute(
                "INSERT INTO session_timeline (session_id, sequence, timestamp, actor, action_summary, evidence_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    te.sequence,
                    te.timestamp,
                    te.actor,
                    te.action_summary,
                    compute_content_hash(te.action_summary),
                ),
            )

        # Files touched
        for ft in analysis.files_touched:
            conn.execute(
                "INSERT INTO file_touched (session_id, file_path, action, timestamp, was_read_first, tool_use_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    ft.file_path,
                    ft.action,
                    ft.timestamp,
                    1 if ft.was_read_first else 0,
                    ft.tool_use_id,
                ),
            )

        # Activity breakdown
        if analysis.activity:
            a = analysis.activity
            conn.execute(
                "INSERT OR REPLACE INTO activity_breakdown (session_id, total_text_blocks, total_tool_calls, total_text_chars, total_tool_time_seconds) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    a.total_text_blocks,
                    a.total_tool_calls,
                    a.total_text_chars,
                    a.total_tool_time_seconds,
                ),
            )

        # Task tracking
        if analysis.task_tracking:
            t = analysis.task_tracking
            evidence = json.dumps(
                {"request": t.initial_request, "satisfied": t.user_satisfied},
                sort_keys=True,
            )
            conn.execute(
                "INSERT OR REPLACE INTO task_tracking (session_id, initial_request, files_changed, user_satisfied, evidence_hash) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    t.initial_request,
                    t.files_changed,
                    t.user_satisfied,
                    compute_content_hash(evidence),
                ),
            )

        # Error recovery
        for er in analysis.error_recovery:
            evidence = json.dumps(
                {"tool": er.tool_name, "error": er.error_summary, "action": er.recovery_action},
                sort_keys=True,
            )
            conn.execute(
                "INSERT INTO error_recovery (session_id, error_timestamp, tool_name, error_summary, recovery_action, evidence_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    er.error_timestamp,
                    er.tool_name,
                    er.error_summary,
                    er.recovery_action,
                    compute_content_hash(evidence),
                ),
            )

        conn.commit()
    finally:
        conn.close()
