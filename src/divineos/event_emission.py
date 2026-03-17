"""
Event Emission Module — Functions to emit events to the ledger.

This module provides functions to emit the four event types:
- emit_user_input() — Emit USER_INPUT events
- emit_tool_call() — Emit TOOL_CALL events
- emit_tool_result() — Emit TOOL_RESULT events
- emit_session_end() — Emit SESSION_END events

All events are validated, stored in the ledger with SHA256 hashes,
and include timestamps and session IDs.
"""

import json
from typing import Any, Dict, Optional
from loguru import logger

from divineos.event_capture import (
    EventType,
    EventValidationError,
    UserInputPayload,
    ToolCallPayload,
    ToolResultPayload,
    SessionEndPayload,
    get_session_tracker,
    get_current_timestamp,
    validate_event_payload,
    normalize_event_payload,
)
from divineos.ledger import log_event


def emit_user_input(content: str, session_id: Optional[str] = None) -> str:
    """
    Emit a USER_INPUT event to the ledger.
    
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
        # Get session ID
        if session_id is None:
            session_id = get_session_tracker().get_current_session_id()
        
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
        
        # Store in ledger
        event_id = log_event(
            event_type=EventType.USER_INPUT.value,
            actor="user",
            payload=normalized_payload,
        )
        
        logger.debug(f"Emitted USER_INPUT event: {event_id}")
        return event_id
        
    except EventValidationError as e:
        logger.error(f"Failed to emit USER_INPUT event: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error emitting USER_INPUT event: {e}")
        raise


def emit_tool_call(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_use_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Emit a TOOL_CALL event to the ledger.
    
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
        # Generate tool_use_id if not provided
        if tool_use_id is None:
            import uuid
            tool_use_id = str(uuid.uuid4())
        
        # Get session ID
        if session_id is None:
            session_id = get_session_tracker().get_current_session_id()
        
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
        
        # Store in ledger
        event_id = log_event(
            event_type=EventType.TOOL_CALL.value,
            actor="assistant",
            payload=normalized_payload,
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
    session_id: Optional[str] = None,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> str:
    """
    Emit a TOOL_RESULT event to the ledger.
    
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
        # Get session ID
        if session_id is None:
            session_id = get_session_tracker().get_current_session_id()
        
        # Get current timestamp
        timestamp = get_current_timestamp()
        
        # Create payload
        payload = {
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "result": result,
            "duration_ms": duration_ms,
            "timestamp": timestamp,
            "session_id": session_id,
            "failed": failed,
        }
        
        # Add error_message if failed
        if failed and error_message:
            payload["error_message"] = error_message
        
        # Validate payload
        validate_event_payload(EventType.TOOL_RESULT, payload)
        
        # Normalize payload
        normalized_payload = normalize_event_payload(EventType.TOOL_RESULT, payload)
        
        # Store in ledger
        event_id = log_event(
            event_type=EventType.TOOL_RESULT.value,
            actor="system",
            payload=normalized_payload,
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
    session_id: Optional[str] = None,
    message_count: Optional[int] = None,
    tool_call_count: Optional[int] = None,
    tool_result_count: Optional[int] = None,
    duration_seconds: Optional[float] = None,
) -> str:
    """
    Emit a SESSION_END event to the ledger.
    
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
        from divineos.ledger import get_events
        
        # Get session ID
        if session_id is None:
            session_id = get_session_tracker().end_session()
            if session_id is None:
                # No active session, generate one
                session_id = get_session_tracker().start_session()
                get_session_tracker().end_session()
        
        # Get current timestamp
        timestamp = get_current_timestamp()
        
        # Query ledger for event counts if not provided
        if message_count is None or tool_call_count is None or tool_result_count is None:
            events = get_events(limit=10000, event_type=None)
            session_events = [e for e in events if e.get("payload", {}).get("session_id") == session_id]
            
            if message_count is None:
                message_count = sum(1 for e in session_events if e["event_type"] == "USER_INPUT")
            if tool_call_count is None:
                tool_call_count = sum(1 for e in session_events if e["event_type"] == "TOOL_CALL")
            if tool_result_count is None:
                tool_result_count = sum(1 for e in session_events if e["event_type"] == "TOOL_RESULT")
        
        # Calculate duration if not provided
        if duration_seconds is None:
            duration_seconds = get_session_tracker().get_session_duration()
            if duration_seconds is None:
                duration_seconds = 0.0
        
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
        
        # Store in ledger
        event_id = log_event(
            event_type=EventType.SESSION_END.value,
            actor="system",
            payload=normalized_payload,
        )
        
        logger.debug(f"Emitted SESSION_END event: {event_id} for session {session_id}")
        return event_id
        
    except EventValidationError as e:
        logger.error(f"Failed to emit SESSION_END event: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error emitting SESSION_END event: {e}")
        raise
