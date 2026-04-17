"""Shared ledger utilities — DB connection and hashing.

Extracted so ledger.py and ledger_verify.py can both import these
without creating a circular dependency.

Single source of truth: ``_get_db_path()``. Both the module-level ``DB_PATH``
attribute (resolved dynamically via PEP 562 ``__getattr__``) and
``get_connection()`` route through it. This means:

* Setting ``DIVINEOS_DB`` at any time — import-time or runtime — takes effect
  immediately on the next access. No stale import-time capture.
* Tests that ``monkeypatch.setattr(module, "DB_PATH", p)`` still work: real
  attributes take precedence over ``__getattr__``.
* ``DB_PATH`` and ``get_connection()`` can never disagree, which was the
  correctness risk Dijkstra flagged in his 2026-04-16 audit.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Declare DB_PATH's type for static analysis. At runtime the attribute
    # is served dynamically by __getattr__ below (PEP 562) so callers always
    # see a fresh Path. This declaration lets mypy still infer Path at call
    # sites like `DB_PATH.parent / "hud"` without a real module attribute.
    DB_PATH: Path


def _get_db_path() -> Path:
    """Get the database path, respecting DIVINEOS_DB environment variable.

    Called every time ``DB_PATH`` or ``get_connection()`` resolves. There is
    deliberately no module-level caching — the env var is the source of truth
    and runtime changes must propagate.
    """
    import os

    env_path = os.environ.get("DIVINEOS_DB")
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent.parent / "data" / "event_ledger.db"


def __getattr__(name: str) -> object:
    """PEP 562 module-level attribute resolution.

    Makes ``DB_PATH`` a dynamic lookup instead of an import-time constant, so
    it can never drift out of sync with ``get_connection()``. Real attributes
    set via ``setattr`` (including monkeypatch) take precedence, preserving
    the existing test override pattern.
    """
    if name == "DB_PATH":
        return _get_db_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content, truncated to 32 chars."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database."""
    db_path = _get_db_path()
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
