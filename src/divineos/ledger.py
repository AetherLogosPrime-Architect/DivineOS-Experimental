"""
The Immutable Event Ledger

Append-only SQLite database. Single source of truth.
Rules: 1) Never update or delete. 2) Store raw data, not summaries.

Every row has a SHA256 content_hash for integrity verification.
"""

import hashlib
import json
import sqlite3
import uuid
import time
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
logger.add(
    _LOG_DIR / "divineos.log",
    rotation="10 MB",
    retention="1 week",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)


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


def _get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database."""
    import os
    # Check environment variable each time to support test isolation
    db_path = os.environ.get("DIVINEOS_DB")
    if db_path:
        db_path = Path(db_path)
    else:
        db_path = Path(__file__).parent.parent.parent / "data" / "event_ledger.db"
    
    db_path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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


def log_event(event_type: str, actor: str, payload: dict) -> str:
    """
    Appends an event to the ledger. Returns the event_id.

    Args:
        event_type: e.g. 'USER_INPUT', 'SYSTEM_PROMPT', 'TOOL_CALL', 'ERROR'
        actor: e.g. 'user', 'assistant', 'system'
        payload: raw data dict for the event

    Fidelity: Computes and stores content_hash for integrity verification.
    """
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
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
) -> list[dict]:
    """
    Retrieves events ordered by timestamp ASC.

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
        params: list = []

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

        return [
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
    finally:
        conn.close()


def search_events(keyword: str, limit: int = 50) -> list[dict]:
    """Search events where the payload contains a keyword (case-insensitive)."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events WHERE payload LIKE ? ORDER BY timestamp ASC LIMIT ?",
            (f"%{keyword}%", limit),
        )
        rows = cursor.fetchall()

        return [
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
    finally:
        conn.close()


def get_recent_context(n: int = 20) -> list[dict]:
    """Get the last N events for context injection."""
    conn = _get_connection()
    try:
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


def count_events() -> dict:
    """Returns event counts by type and actor."""
    conn = _get_connection()
    try:
        by_type = {}
        for row in conn.execute(
            "SELECT event_type, COUNT(*) FROM system_events GROUP BY event_type"
        ):
            by_type[row[0]] = row[1]

        by_actor = {}
        for row in conn.execute("SELECT actor, COUNT(*) FROM system_events GROUP BY actor"):
            by_actor[row[0]] = row[1]

        total = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]

        return {"total": total, "by_type": by_type, "by_actor": by_actor}
    finally:
        conn.close()


def verify_event_hash(event_id: str, payload: dict, stored_hash: str) -> tuple[bool, str]:
    """
    Verify that an event's stored hash matches the computed hash of its payload.
    
    Args:
        event_id: The event ID (for logging)
        payload: The event payload dictionary
        stored_hash: The stored hash from the ledger
        
    Returns:
        tuple: (is_valid, reason) where is_valid is True if hash matches
        
    Requirements:
        - Requirement 7.3: Verify stored hash matches payload
        - Requirement 7.4: Flag event as corrupted if hash mismatch
    """
    # Always hash the entire payload (excluding content_hash field) to ensure complete data integrity
    # Remove content_hash from payload before hashing to avoid circular dependency
    payload_copy = {k: v for k, v in payload.items() if k != "content_hash"}
    payload_json = json.dumps(payload_copy, ensure_ascii=False, sort_keys=True)
    computed_hash = compute_hash(payload_json)
    
    if computed_hash == stored_hash:
        return True, "Hash verified"
    else:
        return False, f"Hash mismatch: expected {computed_hash}, got {stored_hash}"


def get_verified_events(
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    skip_corrupted: bool = True,
) -> tuple[list[dict], list[dict]]:
    """
    Retrieve events with hash verification.
    
    Args:
        limit: max rows to return
        offset: rows to skip
        event_type: optional filter
        actor: optional filter
        skip_corrupted: if True, exclude corrupted events from results
        
    Returns:
        tuple: (verified_events, corrupted_events)
        
    Requirements:
        - Requirement 7.3: Verify stored hash matches payload
        - Requirement 7.4: Flag event as corrupted if hash mismatch
        - Requirement 7.5: Prevent corrupted events from being used in analysis
    """
    all_events = get_events(limit=limit, offset=offset, event_type=event_type, actor=actor)
    
    verified_events = []
    corrupted_events = []
    
    for event in all_events:
        is_valid, reason = verify_event_hash(
            event["event_id"],
            event["payload"],
            event["content_hash"]
        )
        
        if is_valid:
            verified_events.append(event)
        else:
            # Flag as corrupted
            corrupted_event = event.copy()
            corrupted_event["corruption_reason"] = reason
            corrupted_event["is_corrupted"] = True
            corrupted_events.append(corrupted_event)
            
            logger.warning(f"Corrupted event detected: {event['event_id']} - {reason}")
    
    return verified_events, corrupted_events


def verify_all_events() -> dict:
    """
    Verify integrity of all stored events.
    Checks that each event's content_hash matches the hash of its content.
    
    Requirements:
        - Requirement 7.3: Verify stored hash matches payload
        - Requirement 7.4: Flag event as corrupted if hash mismatch
    """
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT event_id, payload, content_hash FROM system_events")
        rows = cursor.fetchall()

        total = len(rows)
        passed = 0
        failed = 0
        failures = []

        for row in rows:
            event_id, payload_json, stored_hash = row
            payload = json.loads(payload_json)

            is_valid, reason = verify_event_hash(event_id, payload, stored_hash)

            if is_valid:
                passed += 1
            else:
                failed += 1
                failures.append(
                    {
                        "event_id": event_id,
                        "reason": reason,
                    }
                )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "failures": failures,
            "integrity": "PASS" if failed == 0 else "FAIL",
        }
    finally:
        conn.close()


def export_to_markdown() -> str:
    """Export all events to markdown format for round-trip verification."""
    events = get_events(limit=10000)
    lines = []

    for event in events:
        actor = event["actor"].upper()
        payload = event["payload"]
        content = payload.get("content", "")

        if actor == "USER":
            lines.append(f"## User\n\n{content}\n")
        elif actor == "ASSISTANT":
            lines.append(f"## Assistant\n\n{content}\n")
        elif event["event_type"] == "TOOL_CALL":
            tool_name = payload.get("tool_name", "unknown")
            lines.append(f"## Tool Call: {tool_name}\n\n```json\n{content}\n```\n")
        elif event["event_type"] == "TOOL_RESULT":
            lines.append(f"## Tool Result\n\n```\n{content}\n```\n")
        else:
            lines.append(f"## {event['event_type']}\n\n{content}\n")

    return "\n".join(lines)
