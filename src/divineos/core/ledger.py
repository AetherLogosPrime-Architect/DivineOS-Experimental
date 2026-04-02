"""The Immutable Event Ledger.

Append-only SQLite database. Single source of truth.
Rules: 1) Never update or delete. 2) Store raw data, not summaries.

Every row has a SHA256 content_hash for integrity verification.
"""

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from divineos.core._ledger_base import (
    DB_PATH as DB_PATH,
    _get_db_path as _get_db_path,
    compute_hash as compute_hash,
    get_connection as get_connection,
    get_connection_fk as get_connection_fk,
)

__all__ = [
    "logger",
    "Ledger",
    "get_ledger",
    "get_connection",
    "log_event",
    "get_events",
    "search_events",
    "get_recent_context",
    "count_events",
    "verify_event_hash",
    "get_verified_events",
    "verify_all_events",
    "clean_corrupted_events",
    "export_to_markdown",
]

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="WARNING",
)

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

# Clean up old rotated logs on startup (loguru retention doesn't always fire on Windows)
_MAX_LOG_FILES = 5
try:
    _old_logs = sorted(_LOG_DIR.glob("divineos.*.log"), key=lambda p: p.stat().st_mtime)
    if len(_old_logs) > _MAX_LOG_FILES:
        for _stale in _old_logs[: len(_old_logs) - _MAX_LOG_FILES]:
            _stale.unlink()
except OSError:
    pass

logger.add(
    _LOG_DIR / "divineos.log",
    rotation="10 MB",
    retention=_MAX_LOG_FILES,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

# Keep backward compat for internal usage in this file
_get_connection = get_connection


def init_db() -> None:
    """Creates the system_events table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                event_id     TEXT PRIMARY KEY,
                timestamp    REAL NOT NULL,
                event_type   TEXT NOT NULL,
                actor        TEXT NOT NULL,
                payload      TEXT NOT NULL,
                content_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON system_events(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON system_events(event_type)
        """)
        conn.commit()
    finally:
        conn.close()


def log_event(event_type: str, actor: str, payload: dict[str, Any], validate: bool = True) -> str:
    """Appends an event to the ledger. Returns the event_id.

    Args:
        event_type: e.g. 'USER_INPUT', 'SYSTEM_PROMPT', 'TOOL_CALL', 'ERROR'
        actor: e.g. 'user', 'assistant', 'system'
        payload: raw data dict for the event
        validate: if True, validate payload before storing (default: True)

    Fidelity: Computes and stores content_hash for integrity verification.

    Validation: Validates payload before storing to prevent corrupted data.

    """
    # Validate payload before storing (only for known event types)
    if validate and event_type in ["USER_INPUT", "TOOL_CALL", "TOOL_RESULT", "SESSION_END"]:
        from divineos.event.event_validation import EventValidator

        is_valid, validation_msg = EventValidator.validate_payload(event_type, payload)
        if not is_valid:
            logger.error(f"Event validation failed for {event_type}: {validation_msg}")
            raise ValueError(f"Invalid event payload: {validation_msg}")

    event_id = str(uuid.uuid4())
    timestamp = time.time()
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    # Compute hash of the content for fidelity verification
    # Always hash the entire payload to ensure complete data integrity
    content_hash = compute_hash(payload_json)

    # Store hash in payload for round-trip verification
    payload["content_hash"] = content_hash
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO system_events (event_id, timestamp, event_type, actor, payload, content_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, timestamp, event_type, actor, payload_json, content_hash),
        )
        conn.commit()
    finally:
        conn.close()

    return event_id


def get_events(
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
    actor: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieves events ordered by timestamp ASC.

    Args:
        limit: max rows to return
        offset: rows to skip
        event_type: optional filter
        actor: optional filter

    """
    conn = _get_connection()
    try:
        query = "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events"
        conditions: list[str] = []
        params: list[Any] = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if actor:
            conditions.append("actor = ?")
            params.append(actor)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        events = []
        for row in rows:
            try:
                payload = json.loads(row[4])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Skipping event {row[0]}: corrupted JSON payload")
                continue
            events.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "actor": row[3],
                    "payload": payload,
                    "content_hash": row[5],
                }
            )
        return events
    finally:
        conn.close()


def search_events(keyword: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search events where the payload contains a keyword (case-insensitive)."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events WHERE payload LIKE ? ORDER BY timestamp ASC LIMIT ?",
            (f"%{keyword}%", limit),
        )
        rows = cursor.fetchall()

        events = []
        for row in rows:
            try:
                payload = json.loads(row[4])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Skipping event {row[0]}: corrupted JSON payload")
                continue
            events.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "actor": row[3],
                    "payload": payload,
                    "content_hash": row[5],
                }
            )
        return events
    finally:
        conn.close()


def get_recent_context(n: int = 20, meaningful_only: bool = True) -> list[dict[str, Any]]:
    """Get the last N events for context injection.

    When meaningful_only is True, filters out high-volume internal events
    (pattern tracking, health checks) to surface what actually happened:
    user decisions, agent actions, errors, and session milestones.
    """
    # These event types are internal bookkeeping — not useful as working memory
    _NOISE_TYPES = {
        "AGENT_PATTERN",
        "AGENT_PATTERN_UPDATE",
        "TOOL_CALL",
        "TOOL_RESULT",
    }

    conn = _get_connection()
    try:
        if meaningful_only:
            placeholders = ",".join("?" for _ in _NOISE_TYPES)
            cursor = conn.execute(
                f"SELECT event_id, timestamp, event_type, actor, payload, content_hash "
                f"FROM system_events "
                f"WHERE event_type NOT IN ({placeholders}) "
                f"ORDER BY timestamp DESC LIMIT ?",
                (*_NOISE_TYPES, n),
            )
        else:
            cursor = conn.execute(
                "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events ORDER BY timestamp DESC LIMIT ?",
                (n,),
            )
        rows = cursor.fetchall()

        events = [
            {
                "event_id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "actor": row[3],
                "payload": json.loads(row[4]),
                "content_hash": row[5],
            }
            for row in rows
        ]
        events.reverse()  # chronological order
        return events
    finally:
        conn.close()


def count_events() -> dict[str, Any]:
    """Returns event counts by type and actor."""
    conn = _get_connection()
    try:
        by_type: dict[str, int] = {}
        for row in conn.execute(
            "SELECT event_type, COUNT(*) FROM system_events GROUP BY event_type",
        ):
            by_type[row[0]] = row[1]

        by_actor: dict[str, int] = {}
        for row in conn.execute("SELECT actor, COUNT(*) FROM system_events GROUP BY actor"):
            by_actor[row[0]] = row[1]

        total = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]

        return {"total": total, "by_type": by_type, "by_actor": by_actor}
    finally:
        conn.close()


class Ledger:
    """Ledger class for code that needs an object-based API.

    Provides supersession-specific operations (store_fact, query_facts, etc.)
    and delegates basic operations to the module-level functions.
    """

    def log_event(
        self, event_type: str, actor: str, payload: dict[str, Any], validate: bool = True
    ) -> str:
        return log_event(event_type, actor, payload, validate)

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        return get_events(limit, offset, event_type, actor)

    def store_fact(self, fact: dict[str, Any]) -> str:
        """Store a fact as a FACT_STORED event. Returns fact ID."""
        fact_id: str = fact.get("id", str(uuid.uuid4()))
        log_event("FACT_STORED", "supersession", fact, validate=False)
        return fact_id

    def store_event(self, event: dict[str, Any]) -> str:
        """Store a SUPERSESSION event. Returns event ID."""
        event_id: str = event.get("event_id", str(uuid.uuid4()))
        log_event("SUPERSESSION", "supersession", event, validate=False)
        return event_id

    def query_facts(
        self, fact_type: str | None = None, fact_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Query FACT_STORED events, optionally filtering by type/key."""
        events = get_events(event_type="FACT_STORED", limit=10000)
        facts = []
        for event in events:
            payload = event.get("payload", {})
            if fact_type and payload.get("fact_type") != fact_type:
                continue
            if fact_key and payload.get("fact_key") != fact_key:
                continue
            facts.append(payload)
        return facts

    def query_supersession_events(
        self,
        superseded_fact_id: str | None = None,
        superseding_fact_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query SUPERSESSION events, optionally filtering by fact IDs."""
        events = get_events(event_type="SUPERSESSION", limit=10000)
        result = []
        for event in events:
            payload = event.get("payload", {})
            if superseded_fact_id and payload.get("superseded_fact_id") != superseded_fact_id:
                continue
            if superseding_fact_id and payload.get("superseding_fact_id") != superseding_fact_id:
                continue
            result.append(payload)
        return result


_ledger_instance: Ledger | None = None


def get_ledger() -> Ledger:
    """Get the global Ledger instance."""
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = Ledger()
    return _ledger_instance


# Backward-compat re-exports: verification/cleanup/export now live in ledger_verify.py
from divineos.core.ledger_verify import (  # noqa: E402
    verify_event_hash as verify_event_hash,
    get_verified_events as get_verified_events,
    verify_all_events as verify_all_events,
    clean_corrupted_events as clean_corrupted_events,
    export_to_markdown as export_to_markdown,
)
