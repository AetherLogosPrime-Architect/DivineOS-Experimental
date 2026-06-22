"""SQLite schema for the andrew_state observation channel.

Per docs/andrew_state_design.md schema section. The table is append-only
in spirit (no row updates except verification fields); corrections create
NEW rows linked via superseded_by, preserving lineage.

The DB file lives at DIVINEOS_HOME/andrew_state.db (defaults to ~/.divineos/).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS andrew_state (
    observation_id      TEXT PRIMARY KEY,
    ts                  REAL NOT NULL,
    axis                TEXT NOT NULL,
    observation         TEXT NOT NULL,
    cited_span          TEXT NOT NULL,
    source_event_id     TEXT NOT NULL,
    source_event_ts     REAL NOT NULL,
    content_link_token  TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    verification_ts     REAL,
    verification_note   TEXT,
    superseded_by       TEXT,
    observer            TEXT NOT NULL DEFAULT 'aether',
    integration_event   TEXT
);

CREATE INDEX IF NOT EXISTS idx_andrew_state_unverified
    ON andrew_state(verification_status)
    WHERE verification_status = 'UNVERIFIED';

CREATE INDEX IF NOT EXISTS idx_andrew_state_ts
    ON andrew_state(ts DESC);

CREATE INDEX IF NOT EXISTS idx_andrew_state_superseded
    ON andrew_state(superseded_by);
"""


def db_path() -> Path:
    """Resolve the andrew_state DB path.

    Honors DIVINEOS_HOME for test isolation (per the pytest pattern used
    throughout the codebase). Defaults to ~/.divineos/andrew_state.db.
    """
    home = os.environ.get("DIVINEOS_HOME")
    base = Path(home) if home else Path.home() / ".divineos"
    base.mkdir(parents=True, exist_ok=True)
    return base / "andrew_state.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection, ensuring schema exists.

    Each caller is responsible for closing the connection. Per the
    pattern used in other core modules — see ledger.py, knowledge/_base.py.
    """
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn
