"""Shared ledger utilities — DB connection and hashing.

Extracted so ledger.py and ledger_verify.py can both import these
without creating a circular dependency.
"""

import hashlib
import sqlite3
from pathlib import Path


def _get_db_path() -> Path:
    """Get the database path, respecting DIVINEOS_DB environment variable."""
    import os

    env_path = os.environ.get("DIVINEOS_DB")
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent.parent / "data" / "event_ledger.db"


DB_PATH = _get_db_path()


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content, truncated to 32 chars."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database."""
    import os

    db_path_str = os.environ.get("DIVINEOS_DB")
    if db_path_str:
        db_path: Path = Path(db_path_str)
    else:
        db_path = Path(__file__).parent.parent.parent / "data" / "event_ledger.db"

    db_path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_connection_fk() -> sqlite3.Connection:
    """Connection with foreign keys enabled."""
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
