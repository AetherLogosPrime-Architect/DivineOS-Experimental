"""Watchmen database schema — audit_rounds and audit_findings tables.

Tier + review-chain columns added 2026-04-21 (commit A of the tiered-audit
redesign). See the ``_migrate_tier_columns`` function for backward-compat
behavior on existing databases.
"""

import sqlite3

from loguru import logger

from divineos.core.knowledge import _get_connection


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check whether a column already exists on a table. ALTER TABLE ADD
    COLUMN is not idempotent in SQLite, so we check first.
    """
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _migrate_tier_columns(conn: sqlite3.Connection) -> None:
    """Additive migration: add tier + review-chain columns to existing tables.

    New columns default to 'WEAK' so that existing rows (filed before the
    tier system existed) don't get retroactively credited with medium or
    strong status without evidence. Operators who want to retrotier historical
    rows can do so with targeted UPDATE statements against specific actors.
    """
    if not _column_exists(conn, "audit_rounds", "tier"):
        conn.execute("ALTER TABLE audit_rounds ADD COLUMN tier TEXT NOT NULL DEFAULT 'WEAK'")

    if not _column_exists(conn, "audit_findings", "tier"):
        conn.execute("ALTER TABLE audit_findings ADD COLUMN tier TEXT NOT NULL DEFAULT 'WEAK'")

    if not _column_exists(conn, "audit_findings", "reviewed_finding_id"):
        conn.execute(
            "ALTER TABLE audit_findings ADD COLUMN reviewed_finding_id TEXT NOT NULL DEFAULT ''"
        )

    if not _column_exists(conn, "audit_findings", "review_stance"):
        conn.execute("ALTER TABLE audit_findings ADD COLUMN review_stance TEXT NOT NULL DEFAULT ''")


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
                notes          TEXT NOT NULL DEFAULT '',
                tier           TEXT NOT NULL DEFAULT 'WEAK'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_rounds_actor
            ON audit_rounds(actor)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_findings (
                finding_id          TEXT PRIMARY KEY,
                round_id            TEXT NOT NULL,
                created_at          REAL NOT NULL,
                actor               TEXT NOT NULL,
                severity            TEXT NOT NULL,
                category            TEXT NOT NULL,
                title               TEXT NOT NULL,
                description         TEXT NOT NULL,
                recommendation      TEXT NOT NULL DEFAULT '',
                status              TEXT NOT NULL DEFAULT 'OPEN',
                resolution_notes    TEXT NOT NULL DEFAULT '',
                routed_to           TEXT NOT NULL DEFAULT '',
                tags                TEXT NOT NULL DEFAULT '[]',
                tier                TEXT NOT NULL DEFAULT 'WEAK',
                reviewed_finding_id TEXT NOT NULL DEFAULT '',
                review_stance       TEXT NOT NULL DEFAULT '',
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

        # Migration must run BEFORE indexes on new columns — a legacy DB
        # will have the tables but not the tier/reviewed_finding_id columns,
        # and CREATE INDEX on a missing column raises OperationalError which
        # would previously cascade into silently skipping the migration.
        _migrate_tier_columns(conn)

        # Indexes on migration-added columns. Safe after the migration has
        # guaranteed the columns exist on both fresh and legacy databases.
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_tier
            ON audit_findings(tier)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_reviewed
            ON audit_findings(reviewed_finding_id)
        """)

        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Watchmen table setup: {e}")
    finally:
        conn.close()
