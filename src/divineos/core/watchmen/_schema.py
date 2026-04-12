"""Watchmen database schema — audit_rounds and audit_findings tables."""

import sqlite3

from loguru import logger

from divineos.core.knowledge._base import _get_connection


def init_watchmen_tables() -> None:
    """Create the audit_rounds and audit_findings tables. Idempotent."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_rounds (
                round_id       TEXT PRIMARY KEY,
                created_at     REAL NOT NULL,
                actor          TEXT NOT NULL,
                focus          TEXT NOT NULL,
                expert_count   INTEGER NOT NULL DEFAULT 0,
                finding_count  INTEGER NOT NULL DEFAULT 0,
                notes          TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_rounds_actor
            ON audit_rounds(actor)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_findings (
                finding_id       TEXT PRIMARY KEY,
                round_id         TEXT NOT NULL,
                created_at       REAL NOT NULL,
                actor            TEXT NOT NULL,
                severity         TEXT NOT NULL,
                category         TEXT NOT NULL,
                title            TEXT NOT NULL,
                description      TEXT NOT NULL,
                recommendation   TEXT NOT NULL DEFAULT '',
                status           TEXT NOT NULL DEFAULT 'OPEN',
                resolution_notes TEXT NOT NULL DEFAULT '',
                routed_to        TEXT NOT NULL DEFAULT '',
                tags             TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (round_id) REFERENCES audit_rounds(round_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_round
            ON audit_findings(round_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_status
            ON audit_findings(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_severity
            ON audit_findings(severity)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_category
            ON audit_findings(category)
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Watchmen table setup: {e}")
    finally:
        conn.close()
