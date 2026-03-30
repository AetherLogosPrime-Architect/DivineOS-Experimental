"""Event Emission Module — Functions to emit events to the ledger.

This module provides functions to emit the four event types:
- emit_user_input() — Emit USER_INPUT events
- emit_tool_call() — Emit TOOL_CALL events
- emit_tool_result() — Emit TOOL_RESULT events
- emit_session_end() — Emit SESSION_END events

All events are validated, stored in the ledger with SHA256 hashes,
and include timestamps and session IDs.

Recursive Event Capture Prevention:
- Uses a thread-local flag to prevent infinite loops when events trigger more events
- When emit_event() is called while already emitting, the recursive call is skipped
- Prevents stack overflow and infinite loops in event capture
"""

import json
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.ledger import log_event
from divineos.core.session_manager import (
    get_or_create_session_id,
    get_session_duration,
)
from divineos.event._event_context import (  # noqa: F401
    _is_in_event_emission,
    _set_in_event_emission,
)
from divineos.event.event_capture import (
    EventType,
    EventValidationError,
    get_current_timestamp,
    normalize_event_payload,
    validate_event_payload,
)


def emit_user_input(content: str, session_id: str | None = None) -> str:
    """Emit a USER_INPUT event to the ledger.

    Args:
        content: The user message content (must not be empty or truncated)
        session_id: Optional session ID (uses current session if not provided)

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    """
    try:
        session_id = get_or_create_session_id(session_id)
        timestamp = get_current_timestamp()
        payload = {
            "content": content,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        validate_event_payload(EventType.USER_INPUT, payload)
        normalized_payload = normalize_event_payload(EventType.USER_INPUT, payload)
        event_id = log_event(
            event_type=EventType.USER_INPUT.value,
            actor="user",
            payload=normalized_payload,
            validate=True,
        )

        logger.debug(f"Emitted USER_INPUT event: {event_id}")
        return event_id

    except EventValidationError as e:
        logger.error(f"Failed to emit USER_INPUT event: {e}")
        raise
    except _EE_ERRORS as e:
        logger.error(f"Unexpected error emitting USER_INPUT event: {e}")
        raise


def emit_explanation(
    explanation_text: str,
    session_id: str | None = None,
) -> str:
    """Emit an EXPLANATION event to the ledger.

    This records an explanation before a tool call, enabling clarity tracking.

    Args:
        explanation_text: The explanation of what will be done and why
        session_id: Optional session ID (uses current session if not provided)

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    """
    try:
        session_id = get_or_create_session_id(session_id)
        timestamp = get_current_timestamp()
        payload = {
            "explanation_text": explanation_text,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        validate_event_payload(EventType.EXPLANATION, payload)
        normalized_payload = normalize_event_payload(EventType.EXPLANATION, payload)
        event_id = log_event(
            event_type=EventType.EXPLANATION.value,
            actor="assistant",
            payload=normalized_payload,
            validate=True,
        )

        logger.debug(f"Emitted EXPLANATION event: {event_id}")
        return event_id

    except EventValidationError as e:
        logger.error(f"Failed to emit EXPLANATION event: {e}")
        raise
    except _EE_ERRORS as e:
        logger.error(f"Unexpected error emitting EXPLANATION event: {e}")
        raise


def emit_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str | None = None,
    session_id: str | None = None,
) -> str:
    """Emit a TOOL_CALL event to the ledger.

    Args:
        tool_name: Name of the tool being called (e.g., "readFile", "strReplace")
        tool_input: Complete input parameters as a dictionary
        tool_use_id: Optional unique ID for this tool use (generates if not provided)
        session_id: Optional session ID (uses current session if not provided)

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    """
    try:
        session_id = get_or_create_session_id(session_id)
        if tool_use_id is None:
            import uuid

            tool_use_id = str(uuid.uuid4())

        timestamp = get_current_timestamp()

        # Size guard: truncate oversized tool_input to prevent DB bloat.
        # Full conversation contexts were being dumped as tool_input (80MB+).
        tool_input = _truncate_payload(tool_input, max_bytes=50_000)

        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_use_id": tool_use_id,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        validate_event_payload(EventType.TOOL_CALL, payload)
        normalized_payload = normalize_event_payload(EventType.TOOL_CALL, payload)
        event_id = log_event(
            event_type=EventType.TOOL_CALL.value,
            actor="assistant",
            payload=normalized_payload,
            validate=True,
        )

        logger.debug(f"Emitted TOOL_CALL event: {event_id} for tool {tool_name}")
        return event_id

    except EventValidationError as e:
        logger.error(f"Failed to emit TOOL_CALL event: {e}")
        raise
    except _EE_ERRORS as e:
        logger.error(f"Unexpected error emitting TOOL_CALL event: {e}")
        raise


def emit_tool_result(
    tool_name: str,
    tool_use_id: str,
    result: str,
    duration_ms: int,
    session_id: str | None = None,
    failed: bool = False,
    error_message: str | None = None,
) -> str:
    """Emit a TOOL_RESULT event to the ledger.

    Args:
        tool_name: Name of the tool that was executed
        tool_use_id: Unique ID matching the TOOL_CALL event
        result: Complete result output (must not be empty or truncated)
        duration_ms: Execution duration in milliseconds
        session_id: Optional session ID (uses current session if not provided)
        failed: Whether the tool execution failed
        error_message: Error message if failed=True

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    """
    try:
        session_id = get_or_create_session_id(session_id)
        timestamp = get_current_timestamp()
        # Size guard: truncate oversized results to prevent DB bloat.
        if len(result) > 50_000:
            result = result[:50_000] + f"\n[TRUNCATED: {len(result)} chars -> 50000]"

        payload = {
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "result": result,
            "duration_ms": duration_ms,
            "failed": failed,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        if failed and error_message:
            payload["error_message"] = error_message

        validate_event_payload(EventType.TOOL_RESULT, payload)
        normalized_payload = normalize_event_payload(EventType.TOOL_RESULT, payload)
        event_id = log_event(
            event_type=EventType.TOOL_RESULT.value,
            actor="system",
            payload=normalized_payload,
            validate=True,
        )

        logger.debug(f"Emitted TOOL_RESULT event: {event_id} for tool {tool_name}")
        return event_id

    except EventValidationError as e:
        logger.error(f"Failed to emit TOOL_RESULT event: {e}")
        raise
    except _EE_ERRORS as e:
        logger.error(f"Unexpected error emitting TOOL_RESULT event: {e}")
        raise


def emit_session_end(
    session_id: str | None = None,
    message_count: int | None = None,
    tool_call_count: int | None = None,
    tool_result_count: int | None = None,
    duration_seconds: float | None = None,
) -> str:
    """Emit a SESSION_END event to the ledger.

    Args:
        session_id: Optional session ID (uses current session if not provided)
        message_count: Optional count of USER_INPUT events (queries ledger if not provided)
        tool_call_count: Optional count of TOOL_CALL events (queries ledger if not provided)
        tool_result_count: Optional count of TOOL_RESULT events (queries ledger if not provided)
        duration_seconds: Optional session duration in seconds (calculates if not provided)

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    """
    try:
        from divineos.core.ledger import get_events

        session_id = get_or_create_session_id(session_id)
        timestamp = get_current_timestamp()

        # Query ledger for event counts if not provided
        if message_count is None or tool_call_count is None or tool_result_count is None:
            events = get_events(limit=10000, event_type=None)
            logger.debug(f"[DEBUG] Total events in ledger: {len(events)}")
            logger.debug(f"[DEBUG] Looking for session_id: {session_id}")

            session_events = [
                e for e in events if e.get("payload", {}).get("session_id") == session_id
            ]
            logger.debug(f"[DEBUG] Events matching session_id: {len(session_events)}")

            # FALLBACK: If no events found for this session_id, use the most recent events' session_id
            # This handles the case where session_id lookup got a stale or wrong session_id
            if not session_events and events:
                logger.debug(
                    f"[DEBUG] No events found for session_id {session_id}, using most recent events' session_id",
                )
                most_recent_session_id = events[0].get("payload", {}).get("session_id")
                if most_recent_session_id:
                    session_id = most_recent_session_id
                    session_events = [
                        e for e in events if e.get("payload", {}).get("session_id") == session_id
                    ]
                    logger.debug(
                        f"[DEBUG] Found {len(session_events)} events for fallback session_id: {session_id}",
                    )

            if message_count is None:
                message_count = sum(1 for e in session_events if e["event_type"] == "USER_INPUT")
            if tool_call_count is None:
                tool_call_count = sum(1 for e in session_events if e["event_type"] == "TOOL_CALL")
            if tool_result_count is None:
                tool_result_count = sum(
                    1 for e in session_events if e["event_type"] == "TOOL_RESULT"
                )

        if duration_seconds is None:
            duration_seconds = get_session_duration()
            logger.debug(f"[DEBUG] Using session manager duration: {duration_seconds}s")

        payload = {
            "session_id": session_id,
            "message_count": message_count,
            "tool_call_count": tool_call_count,
            "tool_result_count": tool_result_count,
            "duration_seconds": duration_seconds,
            "timestamp": timestamp,
        }

        validate_event_payload(EventType.SESSION_END, payload)
        normalized_payload = normalize_event_payload(EventType.SESSION_END, payload)
        event_id = log_event(
            event_type=EventType.SESSION_END.value,
            actor="system",
            payload=normalized_payload,
            validate=True,
        )

        logger.debug(f"Emitted SESSION_END event: {event_id} for session {session_id}")
        return event_id

    except EventValidationError as e:
        logger.error(f"Failed to emit SESSION_END event: {e}")
        raise
    except _EE_ERRORS as e:
        logger.error(f"Unexpected error emitting SESSION_END event: {e}")
        raise


def emit_clarity_violation(
    tool_name: str,
    tool_input: dict[str, Any],
    violation_severity: str,
    enforcement_mode: str,
    action_taken: str,
    context: list[str],
    session_id: str | None = None,
    user_role: str = "user",
    agent_name: str = "agent",
) -> str:
    """Emit a CLARITY_VIOLATION event to the ledger.

    Args:
        tool_name: Name of the tool that violated clarity
        tool_input: Input parameters for the tool
        violation_severity: Severity level (LOW, MEDIUM, HIGH)
        enforcement_mode: Enforcement mode (BLOCKING, LOGGING, PERMISSIVE)
        action_taken: Action taken in response to violation
        context: Preceding messages (conversation context)
        session_id: Optional session ID (uses current session if not provided)
        user_role: Role of the user
        agent_name: Name of the agent

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    """
    try:
        session_id = get_or_create_session_id(session_id)
        timestamp = get_current_timestamp()
        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "violation_severity": violation_severity,
            "enforcement_mode": enforcement_mode,
            "action_taken": action_taken,
            "context": context,
            "timestamp": timestamp,
            "session_id": session_id,
            "user_role": user_role,
            "agent_name": agent_name,
        }

        validate_event_payload(EventType.CLARITY_VIOLATION, payload)
        normalized_payload = normalize_event_payload(EventType.CLARITY_VIOLATION, payload)
        event_id = log_event(
            event_type=EventType.CLARITY_VIOLATION.value,
            actor="system",
            payload=normalized_payload,
            validate=True,
        )

        logger.debug(f"Emitted CLARITY_VIOLATION event: {event_id} for tool {tool_name}")
        return event_id

    except EventValidationError as e:
        logger.error(f"Failed to emit CLARITY_VIOLATION event: {e}")
        raise
    except _EE_ERRORS as e:
        logger.error(f"Unexpected error emitting CLARITY_VIOLATION event: {e}")
        raise


# ─── Payload Size Guard ───────────────────────────────────────────────

_MAX_PAYLOAD_BYTES = 50_000


def _truncate_payload(data: dict[str, Any], max_bytes: int = _MAX_PAYLOAD_BYTES) -> dict[str, Any]:
    """Truncate a payload dict if its JSON serialization exceeds max_bytes.

    Replaces the largest string values with truncation markers until
    the payload fits. Prevents DB bloat from oversized tool inputs.
    """
    serialized = json.dumps(data, default=str)
    if len(serialized) <= max_bytes:
        return data

    # Deep copy to avoid mutating the caller's dict
    import copy

    truncated = copy.deepcopy(data)

    # Find and truncate the largest string values
    for key in sorted(truncated, key=lambda k: len(str(truncated[k])), reverse=True):
        val = truncated[key]
        if isinstance(val, str) and len(val) > 500:
            truncated[key] = val[:500] + f"[TRUNCATED: {len(val)} chars]"
        elif isinstance(val, (dict, list)):
            val_str = json.dumps(val, default=str)
            if len(val_str) > 1000:
                truncated[key] = f"[TRUNCATED {type(val).__name__}: {len(val_str)} chars]"

        if len(json.dumps(truncated, default=str)) <= max_bytes:
            break

    return truncated


# Re-export dispatcher components for backward compatibility
from divineos.event.event_dispatch import (  # noqa: E402
    EventDispatcher as EventDispatcher,
    register_listener as register_listener,
    get_dispatcher as get_dispatcher,
    emit_event as emit_event,
)

_EE_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)
