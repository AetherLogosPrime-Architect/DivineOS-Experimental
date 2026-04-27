"""VOID separate hash-chained ledger.

Per design brief §3 (merged PR #208):
* Separate SQLite file at ``data/void_ledger.db`` (NOT main event_ledger).
* Hash chain independent of main ledger.
* Cross-reference one-way: main ledger can write VOID_SEALED pointer
  events containing {void_finding_id, void_ledger_hash}; this module
  can read and append to its own chain but never writes into main.
* The two ledgers have zero shared state; mode_marker (§6.2) is the
  only piece of shared state for the agent's mode (not for either
  ledger).

Schema:
* ``void_events`` — append-only event store
  (event_id TEXT PK, ts REAL, event_type TEXT, persona TEXT,
   payload TEXT, content_hash TEXT, prev_hash TEXT)

Event types:
* VOID_INVOCATION_STARTED — TRAP step: persona invocation began
* VOID_FINDING — finding produced by ATTACK + EXTRACT
* VOID_RATIONALE_REJECTED — Reductio rejected a rationale on address
* VOID_ADDRESSED — finding addressed via address command
* VOID_SHRED — SHRED step: invocation ended cleanly
* VOID_SCOPE_VIOLATION — persona-prompt assembly attempted outside invocation
* VOID_MIRROR_RESOLVED — operator resolved a Mirror finding
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


VOID_DB_FILENAME = "void_ledger.db"


def db_path() -> Path:
    """Return canonical path to the void ledger DB.

    Respects DIVINEOS_VOID_DB env var override (used by tests).
    Default: ``<src>/data/void_ledger.db`` parallel to event_ledger.
    """
    import os

    env_path = os.environ.get("DIVINEOS_VOID_DB")
    if env_path:
        return Path(env_path)
    # Mirror the same resolution as core._ledger_base for the main DB,
    # but with a different filename. Path(__file__).parent x4 = repo root.
    here = Path(__file__).resolve()
    return here.parent.parent.parent.parent / "data" / VOID_DB_FILENAME


_SCHEMA = """
CREATE TABLE IF NOT EXISTS void_events (
    event_id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    event_type TEXT NOT NULL,
    persona TEXT,
    payload TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    prev_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_void_events_ts ON void_events(ts);
CREATE INDEX IF NOT EXISTS idx_void_events_type ON void_events(event_type);
CREATE INDEX IF NOT EXISTS idx_void_events_persona ON void_events(persona);
"""


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


@contextmanager
def connect(*, path: Path | None = None):
    """Yield a sqlite3.Connection with schema ensured.

    Caller must commit; closes on context exit.
    """
    p = path if path is not None else db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def _last_hash(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT content_hash FROM void_events ORDER BY ts DESC LIMIT 1").fetchone()
    return row[0] if row else None


def _compute_hash(prev_hash: str | None, payload_json: str) -> str:
    h = hashlib.sha256()
    if prev_hash:
        h.update(prev_hash.encode("utf-8"))
    h.update(payload_json.encode("utf-8"))
    return h.hexdigest()


def append_event(
    event_type: str,
    payload: dict,
    *,
    persona: str | None = None,
    path: Path | None = None,
) -> dict:
    """Append a hash-chained event to void_ledger.

    Returns dict with event_id, ts, content_hash, prev_hash.
    """
    event_id = str(uuid.uuid4())
    ts = time.time()
    payload_with_meta = {
        "event_id": event_id,
        "ts": ts,
        "event_type": event_type,
        "persona": persona,
        **payload,
    }
    payload_json = json.dumps(payload_with_meta, sort_keys=True, default=str)

    with connect(path=path) as conn:
        prev_hash = _last_hash(conn)
        content_hash = _compute_hash(prev_hash, payload_json)
        conn.execute(
            "INSERT INTO void_events "
            "(event_id, ts, event_type, persona, payload, content_hash, prev_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, ts, event_type, persona, payload_json, content_hash, prev_hash),
        )
        conn.commit()

    return {
        "event_id": event_id,
        "ts": ts,
        "content_hash": content_hash,
        "prev_hash": prev_hash,
    }


def list_events(
    *,
    event_type: str | None = None,
    persona: str | None = None,
    limit: int = 50,
    path: Path | None = None,
) -> list[dict]:
    """List events, newest first, with optional filters."""
    with connect(path=path) as conn:
        query = "SELECT event_id, ts, event_type, persona, payload, content_hash, prev_hash FROM void_events"
        clauses: list[str] = []
        params: list = []
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if persona:
            clauses.append("persona = ?")
            params.append(persona)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_event(event_id: str, *, path: Path | None = None) -> dict | None:
    with connect(path=path) as conn:
        row = conn.execute(
            "SELECT * FROM void_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    return dict(row) if row else None


def verify_chain(*, path: Path | None = None) -> tuple[bool, list[str]]:
    """Walk the chain in ts order; verify each event's content_hash
    matches recompute(prev_hash, payload_json).

    Returns (ok, list_of_broken_event_ids). Empty list means clean.
    """
    broken: list[str] = []
    with connect(path=path) as conn:
        rows = conn.execute(
            "SELECT event_id, payload, content_hash, prev_hash FROM void_events ORDER BY ts ASC"
        ).fetchall()

    expected_prev: str | None = None
    for row in rows:
        recomputed = _compute_hash(expected_prev, row["payload"])
        if recomputed != row["content_hash"]:
            broken.append(row["event_id"])
        if row["prev_hash"] != expected_prev:
            broken.append(row["event_id"])
        expected_prev = row["content_hash"]

    return (len(broken) == 0, broken)


def write_main_ledger_pointer(
    void_event_id: str,
    void_content_hash: str,
    *,
    actor: str = "void",
) -> None:
    """Write a VOID_SEALED pointer event into the MAIN event_ledger.

    This is the only place void code writes to the main ledger. The
    pointer contains {void_finding_id, void_ledger_hash} only — no
    persona content, no attack text. Per design brief §3.4 cross-
    reference is one-way: main can reference void content; void code
    never writes substantive content into main.

    Fail-soft: if main ledger is unavailable, log and continue. The
    void ledger is the source of truth for void content.
    """
    try:
        from divineos.core.ledger import log_event

        log_event(
            "VOID_SEALED",
            actor,
            {
                "void_finding_id": void_event_id,
                "void_ledger_hash": void_content_hash,
            },
            validate=False,
        )
    except Exception:  # noqa: BLE001 — best-effort cross-reference
        pass
