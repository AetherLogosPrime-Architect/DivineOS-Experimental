"""The Immutable Event Ledger.

Append-only SQLite database. Single source of truth.
Rules: 1) Never update or delete. 2) Store raw data, not summaries.

Every row has:
  - content_hash: SHA256 of the payload (per-event self-integrity)
  - prior_hash: the chain_hash of the immediately preceding event (or
    GENESIS for the first event in the chain)
  - chain_hash: SHA256(prior_hash | event_id | timestamp | event_type |
    actor | payload_json | content_hash) — sequential chain. Any
    mutation of any event in the chain breaks every subsequent
    chain_hash, surfacing tampering when verify_chain runs.

Hash-chain pattern adapted from family/family_member_ledger.py
(Grok 2026-05-02 audit named main-ledger lack-of-chain as a real gap;
claim 223d0e44 tracked the work).
"""

import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from divineos.core._ledger_base import (
    DB_PATH as DB_PATH,
)
from divineos.core._ledger_base import (
    _get_db_path as _get_db_path,
)
from divineos.core._ledger_base import (
    compute_hash as compute_hash,
)
from divineos.core._ledger_base import (
    get_connection as get_connection,
)
from divineos.core._ledger_base import (
    get_connection_fk as get_connection_fk,
)
from divineos.event.event_validation import EventValidator

# Chain genesis — used as prior_hash for the first event.
_CHAIN_GENESIS = "0" * 64

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
_MAX_LOG_FILES = 3
try:
    _old_logs = sorted(_LOG_DIR.glob("divineos.*.log"), key=lambda p: p.stat().st_mtime)
    if len(_old_logs) > _MAX_LOG_FILES:
        for _stale in _old_logs[: len(_old_logs) - _MAX_LOG_FILES]:
            _stale.unlink()
except OSError:
    pass

# File-log level is configurable via DIVINEOS_LOG_LEVEL env var. Default INFO
# captures operational events (EMPIRICA decisions, mode changes, significant
# state transitions) without per-call trace noise — smaller log files, slower
# rotation. Set to DEBUG when deep traces are needed for troubleshooting.
# Valid levels: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL.
_VALID_LOG_LEVELS = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_configured_level = os.environ.get("DIVINEOS_LOG_LEVEL", "INFO").upper()
_FILE_LOG_LEVEL = _configured_level if _configured_level in _VALID_LOG_LEVELS else "INFO"

logger.add(
    _LOG_DIR / "divineos.log",
    rotation="10 MB",
    retention=_MAX_LOG_FILES,
    level=_FILE_LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

# Keep backward compat for internal usage in this file
_get_connection = get_connection


def init_db() -> None:
    """Creates the system_events table if it doesn't exist.

    Schema includes prior_hash and chain_hash columns for sequential
    hash-chaining (see module docstring for the chain formula). Existing
    databases are migrated additively: ALTER TABLE adds the columns if
    they're missing; backfill_chain_hashes() populates them for
    pre-chain events.
    """
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                event_id     TEXT PRIMARY KEY,
                timestamp    REAL NOT NULL,
                event_type   TEXT NOT NULL,
                actor        TEXT NOT NULL,
                payload      TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                prior_hash   TEXT,
                chain_hash   TEXT
            )
        """)
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(system_events)")}
        if "prior_hash" not in existing_cols:
            conn.execute("ALTER TABLE system_events ADD COLUMN prior_hash TEXT")
        if "chain_hash" not in existing_cols:
            conn.execute("ALTER TABLE system_events ADD COLUMN chain_hash TEXT")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON system_events(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON system_events(event_type)
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_chain_hash ON system_events(chain_hash)"
        )
        conn.commit()
    finally:
        conn.close()


def _compute_chain_hash(
    prior_hash: str,
    event_id: str,
    timestamp: float,
    event_type: str,
    actor: str,
    payload_json: str,
    content_hash: str,
) -> str:
    """SHA256 of the canonical pipe-separated content for chain integrity.

    Format: prior_hash|event_id|timestamp|event_type|actor|payload_json|content_hash

    Mutating any field of any event breaks every subsequent chain_hash.
    """
    data = f"{prior_hash}|{event_id}|{timestamp}|{event_type}|{actor}|{payload_json}|{content_hash}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _latest_chain_hash(conn) -> str:
    """Return the chain_hash of the most-recent event, or GENESIS if empty
    or if no events have chain_hash set yet (pre-migration state)."""
    row = conn.execute(
        "SELECT chain_hash FROM system_events "
        "WHERE chain_hash IS NOT NULL "
        "ORDER BY timestamp DESC, rowid DESC LIMIT 1"
    ).fetchone()
    if not row or not row[0]:
        return _CHAIN_GENESIS
    return str(row[0])


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
    if validate and event_type in [
        "USER_INPUT",
        "TOOL_CALL",
        "TOOL_RESULT",
        "SESSION_END",
        "CONSOLIDATION_CHECKPOINT",
    ]:
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
        prior_hash = _latest_chain_hash(conn)
        chain_hash = _compute_chain_hash(
            prior_hash=prior_hash,
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            actor=actor,
            payload_json=payload_json,
            content_hash=content_hash,
        )
        conn.execute(
            "INSERT INTO system_events "
            "(event_id, timestamp, event_type, actor, payload, content_hash, prior_hash, chain_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                timestamp,
                event_type,
                actor,
                payload_json,
                content_hash,
                prior_hash,
                chain_hash,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Increment the write counter that drives the consolidation trigger.
    # Consolidation events themselves are excluded — see increment_write_count
    # for the guard. Wrapped in try/except because this is a low-priority
    # side effect; the event write itself must not be blocked by a counter
    # persistence error.
    try:
        from divineos.core.session_checkpoint import increment_write_count

        increment_write_count(event_type)
    except Exception:  # noqa: BLE001 — counter is best-effort
        pass

    return event_id


def get_events(
    limit: int = 100,
    offset: int = 0,
    event_type: str | list[str] | frozenset[str] | set[str] | None = None,
    actor: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieves events ordered by timestamp ASC.

    Args:
        limit: max rows to return
        offset: rows to skip
        event_type: optional filter. Accepts a single string or a
            collection of strings (list/set/frozenset). A collection
            becomes an SQL IN clause — useful for compat unions like
            CONSOLIDATION_EVENT_TYPES that match both historical
            SESSION_END rows and new CONSOLIDATION_CHECKPOINT rows.
        actor: optional filter

    """
    conn = _get_connection()
    try:
        query = "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events"
        conditions: list[str] = []
        params: list[Any] = []

        if event_type:
            if isinstance(event_type, str):
                conditions.append("event_type = ?")
                params.append(event_type)
            else:
                # Collection — expand into IN clause
                types_list = list(event_type)
                if types_list:
                    placeholders = ",".join("?" for _ in types_list)
                    conditions.append(f"event_type IN ({placeholders})")  # nosec B608
                    params.extend(types_list)
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
    # These event types are internal bookkeeping — not useful as working memory.
    # Without this filter, context is dominated by OS gate cycling
    # (preflight/briefing/ask resets) instead of actual work events.
    _NOISE_TYPES = {
        "AGENT_PATTERN",
        "AGENT_PATTERN_UPDATE",
        "TOOL_CALL",
        "TOOL_RESULT",
        "OS_QUERY",  # internal engagement resets (ask, recall, decide)
        "CLARITY_SUMMARY",  # post-session analysis noise
        "CLARITY_DEVIATION",  # post-session analysis noise
        "CLARITY_LESSON",  # post-session analysis noise
    }

    conn = _get_connection()
    try:
        if meaningful_only:
            placeholders = ",".join("?" for _ in _NOISE_TYPES)
            cursor = conn.execute(
                f"SELECT event_id, timestamp, event_type, actor, payload, content_hash "  # nosec B608: table/column names from module constants; values parameterized
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
    clean_corrupted_events as clean_corrupted_events,
)
from divineos.core.ledger_verify import (  # noqa: E402
    export_to_markdown as export_to_markdown,
)
from divineos.core.ledger_verify import (  # noqa: E402
    get_verified_events as get_verified_events,
)
from divineos.core.ledger_verify import (  # noqa: E402
    verify_all_events as verify_all_events,
)
from divineos.core.ledger_verify import (  # noqa: E402
    verify_event_hash as verify_event_hash,
)


# ---------------------------------------------------------------------------
# Hash-chain backfill + verification
# ---------------------------------------------------------------------------


def backfill_chain_hashes() -> dict[str, Any]:
    """Populate prior_hash + chain_hash for any system_events that lack
    them. Walks events in (timestamp, rowid) order to ensure deterministic
    chain construction. Returns a dict with counts.

    Idempotent: events that already have chain_hash set keep their values.
    Safe to run multiple times.
    """
    conn = _get_connection()
    try:
        rows = list(
            conn.execute(
                "SELECT rowid, event_id, timestamp, event_type, actor, payload, content_hash, "
                "chain_hash FROM system_events ORDER BY timestamp ASC, rowid ASC"
            )
        )
        prior_hash = _CHAIN_GENESIS
        backfilled = 0
        for row in rows:
            rowid, event_id, ts, etype, actor, payload_json, content_hash, existing_chain = row
            if existing_chain:
                prior_hash = existing_chain
                continue
            chain_hash = _compute_chain_hash(
                prior_hash=prior_hash,
                event_id=event_id,
                timestamp=ts,
                event_type=etype,
                actor=actor,
                payload_json=payload_json,
                content_hash=content_hash,
            )
            conn.execute(
                "UPDATE system_events SET prior_hash = ?, chain_hash = ? WHERE rowid = ?",
                (prior_hash, chain_hash, rowid),
            )
            prior_hash = chain_hash
            backfilled += 1
        conn.commit()
        return {"total_events": len(rows), "backfilled": backfilled}
    finally:
        conn.close()


def verify_chain() -> dict[str, Any]:
    """Walk the chain and verify each chain_hash. Returns dict with
    ok (bool), total (int), broken_at (event_id or None),
    broken_reason (str or None).
    """
    conn = _get_connection()
    try:
        rows = list(
            conn.execute(
                "SELECT event_id, timestamp, event_type, actor, payload, content_hash, "
                "prior_hash, chain_hash FROM system_events "
                "ORDER BY timestamp ASC, rowid ASC"
            )
        )
        if not rows:
            return {"ok": True, "total": 0, "broken_at": None, "broken_reason": None}

        expected_prior = _CHAIN_GENESIS
        for row in rows:
            event_id, ts, etype, actor, payload_json, content_hash, stored_prior, stored_chain = row
            if not stored_chain:
                continue
            if stored_prior != expected_prior:
                return {
                    "ok": False,
                    "total": len(rows),
                    "broken_at": event_id,
                    "broken_reason": (
                        f"prior_hash mismatch: stored={(stored_prior or '')[:12]}..., "
                        f"expected={expected_prior[:12]}..."
                    ),
                }
            recomputed = _compute_chain_hash(
                prior_hash=stored_prior,
                event_id=event_id,
                timestamp=ts,
                event_type=etype,
                actor=actor,
                payload_json=payload_json,
                content_hash=content_hash,
            )
            if recomputed != stored_chain:
                return {
                    "ok": False,
                    "total": len(rows),
                    "broken_at": event_id,
                    "broken_reason": (
                        f"chain_hash mismatch: stored={stored_chain[:12]}..., "
                        f"recomputed={recomputed[:12]}..."
                    ),
                }
            expected_prior = stored_chain
        return {"ok": True, "total": len(rows), "broken_at": None, "broken_reason": None}
    finally:
        conn.close()
