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

import threading
from typing import Any

from loguru import logger

from divineos.core.ledger import log_event
from divineos.core.session_manager import (
    get_or_create_session_id,
    get_session_duration,
)
from divineos.event.event_capture import (
    EventType,
    EventValidationError,
    get_current_timestamp,
    normalize_event_payload,
    validate_event_payload,
)

# Thread-local storage for recursive event capture prevention
_event_emission_context = threading.local()


def _is_in_event_emission() -> bool:
    """Check if we're currently in event emission (recursive call detection)."""
    return getattr(_event_emission_context, "in_emission", False)


def _set_in_event_emission(value: bool) -> None:
    """Set the event emission flag."""
    _event_emission_context.in_emission = value


def emit_user_input(content: str, session_id: str | None = None) -> str:
    """Emit a USER_INPUT event to the ledger.

    Args:
        content: The user message content (must not be empty or truncated)
        session_id: Optional session ID (uses current session if not provided)

    Returns:
        event_id: The ID of the stored event

    Raises:
        EventValidationError: If payload validation fails

    Requirements:
        - Requirement 2.1: Emit USER_INPUT event with message content
        - Requirement 2.2: Content must not be empty or truncated
        - Requirement 2.3: Include timestamp in ISO8601 format
        - Requirement 2.4: Include session ID for correlation
        - Requirement 2.5: Store in ledger with SHA256 hash

    """
    try:
        # Get or create session ID using centralized helper
        session_id = get_or_create_session_id(session_id)

        # Get current timestamp
        timestamp = get_current_timestamp()

        # Create payload
        payload = {
            "content": content,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        # Validate payload
        validate_event_payload(EventType.USER_INPUT, payload)

        # Normalize payload
        normalized_payload = normalize_event_payload(EventType.USER_INPUT, payload)

        # Store in ledger with validation enabled
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
    except Exception as e:
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

    Requirements:
        - Requirement 6.1: Emit EXPLANATION event with explanation text
        - Requirement 6.2: Explanation text must not be empty
        - Requirement 6.3: Include timestamp in ISO8601 format
        - Requirement 6.4: Include session ID for correlation
        - Requirement 6.5: Store in ledger with SHA256 hash

    """
    try:
        # Get or create session ID using centralized helper
        session_id = get_or_create_session_id(session_id)

        # Get current timestamp
        timestamp = get_current_timestamp()

        # Create payload
        payload = {
            "explanation_text": explanation_text,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        # Validate payload
        validate_event_payload(EventType.EXPLANATION, payload)

        # Normalize payload
        normalized_payload = normalize_event_payload(EventType.EXPLANATION, payload)

        # Store in ledger with validation enabled
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
    except Exception as e:
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

    Requirements:
        - Requirement 3.1: Emit TOOL_CALL event with tool name and input
        - Requirement 3.2: Include tool name
        - Requirement 3.3: Include complete input parameters as JSON
        - Requirement 3.4: Include timestamp in ISO8601 format
        - Requirement 3.5: Include session ID for correlation
        - Requirement 3.6: Store in ledger with SHA256 hash

    """
    try:
        # Get or create session ID using centralized helper
        session_id = get_or_create_session_id(session_id)

        # Generate tool_use_id if not provided
        if tool_use_id is None:
            import uuid

            tool_use_id = str(uuid.uuid4())

        # Get current timestamp
        timestamp = get_current_timestamp()

        # Create payload
        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_use_id": tool_use_id,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        # Validate payload
        validate_event_payload(EventType.TOOL_CALL, payload)

        # Normalize payload
        normalized_payload = normalize_event_payload(EventType.TOOL_CALL, payload)

        # Store in ledger with validation enabled
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
    except Exception as e:
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

    Requirements:
        - Requirement 4.1: Emit TOOL_RESULT event with tool name, result, duration
        - Requirement 4.2: Include tool name
        - Requirement 4.3: Include complete result output (not truncated)
        - Requirement 4.4: Include execution duration in milliseconds
        - Requirement 4.5: Include timestamp in ISO8601 format
        - Requirement 4.6: Include session ID for correlation
        - Requirement 4.7: Store in ledger with SHA256 hash
        - Requirement 4.9: Handle tool failures with error message and failed flag

    """
    try:
        # Get or create session ID using centralized helper
        session_id = get_or_create_session_id(session_id)

        # Get current timestamp
        timestamp = get_current_timestamp()

        # Create payload
        payload = {
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "result": result,
            "duration_ms": duration_ms,
            "failed": failed,
            "timestamp": timestamp,
            "session_id": session_id,
        }

        # Add error_message if failed
        if failed and error_message:
            payload["error_message"] = error_message

        # Validate payload
        validate_event_payload(EventType.TOOL_RESULT, payload)

        # Normalize payload
        normalized_payload = normalize_event_payload(EventType.TOOL_RESULT, payload)

        # Store in ledger with validation enabled
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
    except Exception as e:
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

    Requirements:
        - Requirement 5.1: Emit SESSION_END event with session ID and metadata
        - Requirement 5.2: Include session ID
        - Requirement 5.3: Include actual count of USER_INPUT events
        - Requirement 5.4: Include actual count of TOOL_CALL events
        - Requirement 5.5: Include actual count of TOOL_RESULT events
        - Requirement 5.6: Include session duration in seconds (calculated from first to last event)
        - Requirement 5.7: Include timestamp in ISO8601 format
        - Requirement 5.8: Store in ledger with SHA256 hash
        - Requirement 5.9: No empty or zero-value fields (except where legitimately zero)

    """
    try:
        from divineos.core.ledger import get_events

        # Get or create session ID using centralized helper
        session_id = get_or_create_session_id(session_id)

        # Get current timestamp
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

        # Calculate duration if not provided - use canonical session_manager function
        if duration_seconds is None:
            duration_seconds = get_session_duration()
            logger.debug(f"[DEBUG] Using session manager duration: {duration_seconds}s")

        # Create payload
        payload = {
            "session_id": session_id,
            "message_count": message_count,
            "tool_call_count": tool_call_count,
            "tool_result_count": tool_result_count,
            "duration_seconds": duration_seconds,
            "timestamp": timestamp,
        }

        # Validate payload
        validate_event_payload(EventType.SESSION_END, payload)

        # Normalize payload
        normalized_payload = normalize_event_payload(EventType.SESSION_END, payload)

        # Store in ledger with validation enabled
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
    except Exception as e:
        logger.error(f"Unexpected error emitting SESSION_END event: {e}")
        raise


# ============================================================================
# Event Dispatcher Pattern (Consolidated from event_dispatcher.py)
# ============================================================================
# This section consolidates the listener/callback pattern from event_dispatcher.py
# into the canonical event_emission.py module.


class EventDispatcher:
    """Central event emission and listener management."""

    def __init__(self) -> None:
        """Initialize the event dispatcher."""
        self.listeners: dict[str, list[Any]] = {}

    def register(self, event_type: str, callback: Any) -> None:
        """Register a listener for an event type.

        Args:
            event_type: Type of event to listen for (e.g., 'USER_INPUT')
            callback: Function to call when event is emitted
                     Signature: callback(event_type: str, payload: dict) -> None

        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        logger.debug(f"Registered listener for {event_type}")

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        actor: str = "system",
        validate: bool = True,
    ) -> str:
        """Emit an event to all listeners and log to ledger.

        Args:
            event_type: Type of event (e.g., 'USER_INPUT', 'TOOL_CALL')
            payload: Event data dict
            actor: Who triggered the event (default: 'system')
            validate: Whether to validate payload before storing (default: True)

        Returns:
            event_id: UUID of the logged event

        Raises:
            ValueError: If payload is invalid

        """
        if not isinstance(payload, dict):
            raise ValueError(f"Payload must be dict, got {type(payload)}")

        # Call registered listeners
        for callback in self.listeners.get(event_type, []):
            try:
                callback(event_type, payload)
            except Exception as e:
                logger.error(f"Listener failed for {event_type}: {e}")

        # Log to ledger
        try:
            event_id = log_event(event_type, actor, payload, validate=validate)
            logger.debug(f"Emitted {event_type} event: {event_id}")
            return event_id
        except Exception as e:
            logger.error(f"Failed to log event {event_type}: {e}")
            raise


# Global dispatcher instance
_dispatcher = EventDispatcher()


def register_listener(event_type: str, callback: Any) -> None:
    """Register a callback for an event type.

    Args:
        event_type: Type of event to listen for
        callback: Function to call when event is emitted

    """
    _dispatcher.register(event_type, callback)


def get_dispatcher() -> EventDispatcher:
    """Get the global dispatcher instance."""
    return _dispatcher


def emit_event(
    event_type: str,
    payload: dict[str, Any],
    actor: str = "system",
    validate: bool = True,
) -> str | None:
    """Emit an event to all listeners and log to ledger.

    This is a wrapper around the global dispatcher's emit method,
    providing the same interface as the original event_dispatcher module.

    Recursive Event Capture Prevention:
    - If this function is called while already emitting an event, the recursive
      call is skipped to prevent infinite loops
    - This prevents stack overflow when event listeners or ledger operations
      trigger additional events

    Args:
        event_type: Type of event (e.g., 'USER_INPUT', 'TOOL_CALL')
        payload: Event data dict
        actor: Who triggered the event (default: 'system')
        validate: Whether to validate payload before storing (default: True)

    Returns:
        event_id: UUID of the logged event, or None if recursive call was skipped

    """
    # Check for recursive event emission
    if _is_in_event_emission():
        logger.debug(f"Skipping recursive event emission: {event_type}")
        return None

    # Set flag to prevent recursive calls
    _set_in_event_emission(True)
    try:
        return _dispatcher.emit(event_type, payload, actor, validate=validate)
    finally:
        # Always clear the flag, even if an exception occurs
        _set_in_event_emission(False)
