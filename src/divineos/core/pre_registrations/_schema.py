"""Pre-registrations database schema."""

import sqlite3

from loguru import logger

from divineos.core.knowledge import _get_connection


def init_pre_registrations_tables() -> None:
    """Create the pre_registrations table. Idempotent."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pre_registrations (
                prereg_id          TEXT PRIMARY KEY,
                created_at         REAL NOT NULL,
                actor              TEXT NOT NULL,
                mechanism          TEXT NOT NULL,
                claim              TEXT NOT NULL,
                success_criterion  TEXT NOT NULL,
                falsifier          TEXT NOT NULL,
                review_ts          REAL NOT NULL,
                review_window_days INTEGER NOT NULL,
                outcome            TEXT NOT NULL DEFAULT 'OPEN',
                outcome_ts         REAL,
                outcome_notes      TEXT NOT NULL DEFAULT '',
                linked_claim_id    TEXT,
                linked_commit      TEXT,
                tags               TEXT NOT NULL DEFAULT '[]'
            )
        """)
        # The reading that would embarrass the builder — added 2026-09-09.
        # Nullable on purpose: NULL on an older row means the question was
        # never asked, which must stay distinguishable from an answer of none.
        try:
            conn.execute("ALTER TABLE pre_registrations ADD COLUMN embarrassing_reading TEXT")
        except sqlite3.OperationalError:
            pass
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prereg_review
            ON pre_registrations(review_ts, outcome)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prereg_outcome
            ON pre_registrations(outcome)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prereg_mechanism
            ON pre_registrations(mechanism)
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Pre-registration table setup: {e}")
    finally:
        conn.close()
