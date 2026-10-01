"""Ledger verification, cleanup, and export functions.

Extracted from ledger.py to keep both modules under 500 lines.
"""

import json
import time
from typing import Any

from loguru import logger

from divineos.core._ledger_base import compute_hash, get_connection
from divineos.core.ledger import get_events
from divineos.event.event_validation import EventValidator


def verify_event_hash(event_id: str, payload: dict[str, Any], stored_hash: str) -> tuple[bool, str]:
    """Verify that an event's stored hash matches the computed hash of its payload.

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
    return False, f"Hash mismatch: expected {computed_hash}, got {stored_hash}"


def get_verified_events(
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
    actor: str | None = None,
    session_id: str | None = None,
    skip_corrupted: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retrieve events with hash verification.

    Args:
        limit: max rows to return
        offset: rows to skip
        event_type: optional filter
        actor: optional filter
        session_id: optional filter to isolate events by session
        skip_corrupted: if True, exclude corrupted events from results

    Returns:
        tuple: (verified_events, corrupted_events)

    Requirements:
        - Requirement 7.3: Verify stored hash matches payload
        - Requirement 7.4: Flag event as corrupted if hash mismatch
        - Requirement 7.5: Prevent corrupted events from being used in analysis
        - Requirement 9.3: Session event correlation - filter by session_id

    """
    all_events = get_events(limit=limit, offset=offset, event_type=event_type, actor=actor)

    # Filter by session_id if provided (session isolation)
    if session_id:
        all_events = [
            event
            for event in all_events
            if event.get("payload", {}).get("session_id") == session_id
        ]

    verified_events = []
    corrupted_events = []

    for event in all_events:
        is_valid, reason = verify_event_hash(
            event["event_id"],
            event["payload"],
            event["content_hash"],
        )

        if is_valid:
            verified_events.append(event)
        else:
            # Flag as corrupted
            corrupted_event = event.copy()
            corrupted_event["corruption_reason"] = reason
            corrupted_event["is_corrupted"] = True
            corrupted_events.append(corrupted_event)

            if not skip_corrupted:
                verified_events.append(corrupted_event)

            logger.warning(f"Corrupted event detected: {event['event_id']} - {reason}")

    return verified_events, corrupted_events


def verify_all_events(skip_types: list[str] | None = None) -> dict[str, Any]:
    """Verify integrity of all stored events.
    Checks that each event's content_hash matches the hash of its content.
    Also validates that payloads contain valid data (not corrupted).

    Args:
        skip_types: Event types to exclude from verification. Defaults to
            ephemeral types that are pruned by the tool event conveyor belt
            and ledger compressor — their deletion is intentional, not corruption.

    Requirements:
        - Requirement 7.3: Verify stored hash matches payload
        - Requirement 7.4: Flag event as corrupted if hash mismatch
        - Requirement 7.6: Validate payload content for data validity
    """
    # Ephemeral types pruned by tool_wrapper and ledger_compressor.
    # Verifying these is meaningless — they're deleted by design.
    if skip_types is None:
        skip_types = [
            "TOOL_CALL",
            "TOOL_RESULT",
            "AGENT_PATTERN",
            "AGENT_PATTERN_UPDATE",
            "AGENT_WORK",
            "AGENT_WORK_OUTCOME",
            "AGENT_LEARNING_AUDIT",
            "AGENT_CONTEXT_COMPRESSION",
            "LEDGER_COMPACTION",
        ]
    skip_set = set(skip_types)

    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT event_id, event_type, payload, content_hash FROM system_events",
        )
        rows = cursor.fetchall()

        skipped = 0
        total = len(rows)
        passed = 0
        failed = 0
        failures: list[dict[str, Any]] = []

        for row in rows:
            event_id, event_type, payload_json, stored_hash = row

            if event_type in skip_set:
                skipped += 1
                continue

            payload = json.loads(payload_json)

            # First check: verify hash matches
            is_hash_valid, hash_reason = verify_event_hash(event_id, payload, stored_hash)

            if not is_hash_valid:
                failed += 1
                failures.append(
                    {
                        "event_id": event_id,
                        "reason": hash_reason,
                        "type": "hash_mismatch",
                    },
                )
                continue

            # Second check: validate payload content for data validity
            # Only validate known event types
            if event_type in [
                "USER_INPUT",
                "TOOL_CALL",
                "TOOL_RESULT",
                "SESSION_END",
                "CONSOLIDATION_CHECKPOINT",
            ]:
                is_content_valid, content_reason = EventValidator.validate_payload(
                    event_type,
                    payload,
                )

                if not is_content_valid:
                    failed += 1
                    failures.append(
                        {
                            "event_id": event_id,
                            "reason": content_reason,
                            "type": "invalid_content",
                        },
                    )
                    continue

            passed += 1

        return {
            "total": total,
            "skipped": skipped,
            "checked": total - skipped,
            "passed": passed,
            "failed": failed,
            "failures": failures,
            "integrity": "PASS" if failed == 0 else "FAIL",
        }
    finally:
        conn.close()


def clean_corrupted_events() -> dict[str, Any]:
    """Remove all corrupted events from the ledger.

    Returns:
        dict: Summary of cleanup operation with count of removed events

    """
    conn = get_connection()
    try:
        # First, identify all corrupted events
        cursor = conn.execute(
            "SELECT event_id, event_type, payload, content_hash FROM system_events",
        )
        rows = cursor.fetchall()

        corrupted_ids = []

        for row in rows:
            event_id, event_type, payload_json, stored_hash = row
            payload = json.loads(payload_json)

            # Check hash validity
            is_hash_valid, _ = verify_event_hash(event_id, payload, stored_hash)
            if not is_hash_valid:
                corrupted_ids.append(event_id)
                continue

            # Check content validity for known event types
            if event_type in [
                "USER_INPUT",
                "TOOL_CALL",
                "TOOL_RESULT",
                "SESSION_END",
                "CONSOLIDATION_CHECKPOINT",
            ]:
                is_content_valid, _ = EventValidator.validate_payload(event_type, payload)
                if not is_content_valid:
                    corrupted_ids.append(event_id)

        if not corrupted_ids:
            return {
                "deleted_count": 0,
                "logged_count": 0,
                "corrupted_event_ids": [],
                "status": "success",
            }

        # ONE TRANSACTION: every removal and one LEDGER_CORRUPTION_REPAIRED
        # note per removal, committed together or not at all (Anvil and Muse,
        # SC #10, 2026-09-28). The notes used to go through log_event's second
        # connection, wait on this one's lock, fail and be swallowed, so a
        # removal left no record of itself. A note that cannot be written now
        # rolls its removal back.
        #
        # THE GAP STANDS. No surviving row is rewritten. A first version
        # relinked the chain around each gap; the council walk on it
        # (2026-09-28, twelve lenses) and Aria reversed that. The chain exists
        # to make a removal visible, a relink is what a tamperer does, and it
        # rebuilt every row after the first gap -- on the real ledger it would
        # have mended 946 true crossed links. Each note instead names the
        # removed row's chain hash, and verify_chain excuses the one link that
        # hash leaves broken, while still rechecking every row's own hash.
        prior_isolation = conn.isolation_level
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            removed = []
            for event_id in corrupted_ids:
                row = conn.execute(
                    "SELECT event_type, payload, content_hash, chain_hash FROM system_events "
                    "WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                conn.execute("DELETE FROM system_events WHERE event_id = ?", (event_id,))
                removed.append((event_id, row))

            logged = 0
            for event_id, row in removed:
                _append_on(
                    conn,
                    "LEDGER_CORRUPTION_REPAIRED",
                    "ledger_verify",
                    {
                        "deleted_event_id": event_id,
                        "deleted_event_type": row[0] if row else None,
                        "deleted_payload_preview": str(row[1])[:500] if row else None,
                        "stored_hash": row[2] if row else None,
                        # The one prior link this removal leaves broken, named
                        # so verify_chain can excuse that link and no other.
                        "deleted_chain_hash": row[3] if row else None,
                        "repaired_at": time.time(),
                    },
                )
                logged += 1
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.isolation_level = prior_isolation

        logger.info(
            f"Cleaned {len(removed)} corrupted events from ledger; "
            f"{logged} LEDGER_CORRUPTION_REPAIRED notes written; gaps left standing"
        )

        return {
            "deleted_count": len(removed),
            "logged_count": logged,
            "corrupted_event_ids": corrupted_ids,
            "status": "success",
        }
    finally:
        conn.close()


def _append_on(conn, event_type: str, actor: str, payload: dict[str, Any]) -> str:
    """Write one chained event inside the caller's transaction."""
    from divineos.core.ledger import append_on

    return append_on(conn, event_type, actor, payload)


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
