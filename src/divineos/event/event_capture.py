"""Event Capture Infrastructure — Core data structures and validation for IDE events.

This module provides:
- Event type enums (USER_INPUT, TOOL_CALL, TOOL_RESULT, CONSOLIDATION_CHECKPOINT,
  SESSION_END for historical compat)
- Payload schemas for each event type
- Validation functions for event payloads
- Event normalization and enrichment

Note: Session ID generation and tracking has been consolidated into
core/session_manager.py. This module imports get_session_tracker for
backward compatibility only.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Supported event types for IDE integration.

    SESSION_END is retained for historical events (the ledger is append-only;
    events written before the 2026-04-20 rename stay under that label).
    CONSOLIDATION_CHECKPOINT is the current name for the same semantic event:
    "run the learning pipeline, analyze, promote knowledge, reset counters."
    See CONSOLIDATION_EVENT_TYPES below for the compat union that readers use.
    """

    USER_INPUT = "USER_INPUT"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    EXPLANATION = "EXPLANATION"
    SESSION_END = "SESSION_END"  # historical label; retained for old ledger rows
    CONSOLIDATION_CHECKPOINT = "CONSOLIDATION_CHECKPOINT"
    CLARITY_VIOLATION = "CLARITY_VIOLATION"


# Compat union — readers that want to find "any consolidation-style event"
# should check this set, not a single literal. Contains both the historical
# SESSION_END label and the current CONSOLIDATION_CHECKPOINT label.
# Use: `if event.get("event_type") in CONSOLIDATION_EVENT_TYPES: ...`
CONSOLIDATION_EVENT_TYPES = frozenset(
    {
        EventType.SESSION_END.value,
        EventType.CONSOLIDATION_CHECKPOINT.value,
    }
)


class EventValidationError(Exception):
    """Raised when event payload validation fails."""


@dataclass
class UserInputPayload:
    """Payload schema for USER_INPUT events."""

    content: str
    timestamp: str
    session_id: str

    def validate(self) -> None:
        """Validate USER_INPUT payload."""
        if not isinstance(self.content, str):
            msg = "content must be a string"
            raise EventValidationError(msg)
        if not self.content:
            msg = "content cannot be empty"
            raise EventValidationError(msg)
        if len(self.content) > 1000000:  # 1MB limit
            msg = "content exceeds maximum length (1MB)"
            raise EventValidationError(msg)

        if not isinstance(self.timestamp, str):
            msg = "timestamp must be a string"
            raise EventValidationError(msg)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            msg = "timestamp must be valid ISO8601 format"
            raise EventValidationError(msg)

        if not isinstance(self.session_id, str):
            msg = "session_id must be a string"
            raise EventValidationError(msg)
        if not self.session_id:
            msg = "session_id cannot be empty"
            raise EventValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ToolCallPayload:
    """Payload schema for TOOL_CALL events."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    timestamp: str
    session_id: str

    def validate(self) -> None:
        """Validate TOOL_CALL payload."""
        if not isinstance(self.tool_name, str):
            msg = "tool_name must be a string"
            raise EventValidationError(msg)
        if not self.tool_name:
            msg = "tool_name cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.tool_input, dict):
            msg = "tool_input must be a dictionary"
            raise EventValidationError(msg)

        if not isinstance(self.tool_use_id, str):
            msg = "tool_use_id must be a string"
            raise EventValidationError(msg)
        if not self.tool_use_id:
            msg = "tool_use_id cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.timestamp, str):
            msg = "timestamp must be a string"
            raise EventValidationError(msg)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            msg = "timestamp must be valid ISO8601 format"
            raise EventValidationError(msg)

        if not isinstance(self.session_id, str):
            msg = "session_id must be a string"
            raise EventValidationError(msg)
        if not self.session_id:
            msg = "session_id cannot be empty"
            raise EventValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ToolResultPayload:
    """Payload schema for TOOL_RESULT events."""

    tool_name: str
    tool_use_id: str
    result: str
    duration_ms: int
    timestamp: str
    session_id: str
    failed: bool = False
    error_message: str | None = None

    def validate(self) -> None:
        """Validate TOOL_RESULT payload."""
        if not isinstance(self.tool_name, str):
            msg = "tool_name must be a string"
            raise EventValidationError(msg)
        if not self.tool_name:
            msg = "tool_name cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.tool_use_id, str):
            msg = "tool_use_id must be a string"
            raise EventValidationError(msg)
        if not self.tool_use_id:
            msg = "tool_use_id cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.result, str):
            msg = "result must be a string"
            raise EventValidationError(msg)
        if len(self.result) > 10000000:  # 10MB limit
            msg = "result exceeds maximum length (10MB)"
            raise EventValidationError(msg)

        if not isinstance(self.duration_ms, int):
            msg = "duration_ms must be an integer"
            raise EventValidationError(msg)
        if self.duration_ms < 0:
            msg = "duration_ms cannot be negative"
            raise EventValidationError(msg)

        if not isinstance(self.timestamp, str):
            msg = "timestamp must be a string"
            raise EventValidationError(msg)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            msg = "timestamp must be valid ISO8601 format"
            raise EventValidationError(msg)

        if not isinstance(self.session_id, str):
            msg = "session_id must be a string"
            raise EventValidationError(msg)
        if not self.session_id:
            msg = "session_id cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.failed, bool):
            msg = "failed must be a boolean"
            raise EventValidationError(msg)

        if self.failed and not self.error_message:
            msg = "error_message required when failed=True"
            raise EventValidationError(msg)
        if self.error_message and not isinstance(self.error_message, str):
            msg = "error_message must be a string"
            raise EventValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class ExplanationPayload:
    """Payload schema for EXPLANATION events."""

    explanation_text: str
    timestamp: str
    session_id: str

    def validate(self) -> None:
        """Validate EXPLANATION payload."""
        if not isinstance(self.explanation_text, str):
            msg = "explanation_text must be a string"
            raise EventValidationError(msg)
        if not self.explanation_text:
            msg = "explanation_text cannot be empty"
            raise EventValidationError(msg)
        if len(self.explanation_text) > 1000000:  # 1MB limit
            msg = "explanation_text exceeds maximum length (1MB)"
            raise EventValidationError(msg)

        if not isinstance(self.timestamp, str):
            msg = "timestamp must be a string"
            raise EventValidationError(msg)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            msg = "timestamp must be valid ISO8601 format"
            raise EventValidationError(msg)

        if not isinstance(self.session_id, str):
            msg = "session_id must be a string"
            raise EventValidationError(msg)
        if not self.session_id:
            msg = "session_id cannot be empty"
            raise EventValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SessionEndPayload:
    """Payload schema for SESSION_END and CONSOLIDATION_CHECKPOINT events.

    The two event types share this schema: they carry the same semantic content
    (a checkpoint summary of what the session did). Only the event_type label
    differs — SESSION_END for historical rows, CONSOLIDATION_CHECKPOINT for new
    writes after the 2026-04-20 rename. See ConsolidationCheckpointPayload
    below — it's an alias to this class so callers can use the current name.
    """

    session_id: str
    message_count: int
    tool_call_count: int
    tool_result_count: int
    duration_seconds: float
    timestamp: str

    def validate(self) -> None:
        """Validate SESSION_END / CONSOLIDATION_CHECKPOINT payload."""
        if not isinstance(self.session_id, str):
            msg = "session_id must be a string"
            raise EventValidationError(msg)
        if not self.session_id:
            msg = "session_id cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.message_count, int):
            msg = "message_count must be an integer"
            raise EventValidationError(msg)
        if self.message_count < 0:
            msg = "message_count cannot be negative"
            raise EventValidationError(msg)

        if not isinstance(self.tool_call_count, int):
            msg = "tool_call_count must be an integer"
            raise EventValidationError(msg)
        if self.tool_call_count < 0:
            msg = "tool_call_count cannot be negative"
            raise EventValidationError(msg)

        if not isinstance(self.tool_result_count, int):
            msg = "tool_result_count must be an integer"
            raise EventValidationError(msg)
        if self.tool_result_count < 0:
            msg = "tool_result_count cannot be negative"
            raise EventValidationError(msg)

        if not isinstance(self.duration_seconds, (int, float)):
            msg = "duration_seconds must be a number"
            raise EventValidationError(msg)
        if self.duration_seconds < 0:
            msg = "duration_seconds cannot be negative"
            raise EventValidationError(msg)

        if not isinstance(self.timestamp, str):
            msg = "timestamp must be a string"
            raise EventValidationError(msg)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            msg = "timestamp must be valid ISO8601 format"
            raise EventValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# Current name for the same payload shape. Use this when writing new
# CONSOLIDATION_CHECKPOINT events; SessionEndPayload remains for historical
# SESSION_END reads. Both resolve to the same dataclass at runtime.
ConsolidationCheckpointPayload = SessionEndPayload


@dataclass
class ClarityViolationPayload:
    """Payload schema for CLARITY_VIOLATION events."""

    tool_name: str
    tool_input: dict[str, Any]
    violation_severity: str
    enforcement_mode: str
    action_taken: str
    context: list[str]
    timestamp: str
    session_id: str
    user_role: str = "user"
    agent_name: str = "agent"

    def validate(self) -> None:
        """Validate CLARITY_VIOLATION payload."""
        if not isinstance(self.tool_name, str):
            msg = "tool_name must be a string"
            raise EventValidationError(msg)
        if not self.tool_name:
            msg = "tool_name cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.tool_input, dict):
            msg = "tool_input must be a dictionary"
            raise EventValidationError(msg)

        if not isinstance(self.violation_severity, str):
            msg = "violation_severity must be a string"
            raise EventValidationError(msg)
        if self.violation_severity not in ("LOW", "MEDIUM", "HIGH"):
            msg = "violation_severity must be LOW, MEDIUM, or HIGH"
            raise EventValidationError(msg)

        if not isinstance(self.enforcement_mode, str):
            msg = "enforcement_mode must be a string"
            raise EventValidationError(msg)
        if self.enforcement_mode not in ("BLOCKING", "LOGGING", "PERMISSIVE"):
            msg = "enforcement_mode must be BLOCKING, LOGGING, or PERMISSIVE"
            raise EventValidationError(msg)

        if not isinstance(self.action_taken, str):
            msg = "action_taken must be a string"
            raise EventValidationError(msg)
        if not self.action_taken:
            msg = "action_taken cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.context, list):
            msg = "context must be a list"
            raise EventValidationError(msg)
        for item in self.context:
            if not isinstance(item, str):
                msg = "context items must be strings"
                raise EventValidationError(msg)

        if not isinstance(self.timestamp, str):
            msg = "timestamp must be a string"
            raise EventValidationError(msg)
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            msg = "timestamp must be valid ISO8601 format"
            raise EventValidationError(msg)

        if not isinstance(self.session_id, str):
            msg = "session_id must be a string"
            raise EventValidationError(msg)
        if not self.session_id:
            msg = "session_id cannot be empty"
            raise EventValidationError(msg)

        if not isinstance(self.user_role, str):
            msg = "user_role must be a string"
            raise EventValidationError(msg)

        if not isinstance(self.agent_name, str):
            msg = "agent_name must be a string"
            raise EventValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# Session Tracker (Consolidated into core/session_manager.py)
# ============================================================================
# This import provides backward compatibility for code that imports
# get_session_tracker from event_capture.py. New code should import from
# core/session_manager.py instead.

from divineos.core.session_manager import (  # noqa: E402, F401
    SessionTracker,
    get_session_tracker,
)


def get_current_timestamp() -> str:
    """Get current timestamp in ISO8601 format.

    Returns:
        timestamp: ISO8601 formatted timestamp with UTC timezone

    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_event_payload(event_type: EventType, payload: dict[str, Any]) -> None:
    """Validate an event payload against its schema.

    Args:
        event_type: Type of event
        payload: Event payload dictionary

    Raises:
        EventValidationError: If payload is invalid

    """
    try:
        p: (
            UserInputPayload
            | ToolCallPayload
            | ToolResultPayload
            | ExplanationPayload
            | SessionEndPayload
            | ClarityViolationPayload
        )
        if event_type == EventType.USER_INPUT:
            p = UserInputPayload(**payload)
            p.validate()
        elif event_type == EventType.TOOL_CALL:
            p = ToolCallPayload(**payload)
            p.validate()
        elif event_type == EventType.TOOL_RESULT:
            p = ToolResultPayload(**payload)
            p.validate()
        elif event_type == EventType.EXPLANATION:
            p = ExplanationPayload(**payload)
            p.validate()
        elif event_type in (EventType.SESSION_END, EventType.CONSOLIDATION_CHECKPOINT):
            p = SessionEndPayload(**payload)
            p.validate()
        elif event_type == EventType.CLARITY_VIOLATION:
            p = ClarityViolationPayload(**payload)
            p.validate()
        else:
            raise EventValidationError(f"Unknown event type: {event_type}")
    except TypeError as e:
        raise EventValidationError(f"Missing required fields: {e}") from e


def normalize_event_payload(event_type: EventType, payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize an event payload to ensure consistency.

    Args:
        event_type: Type of event
        payload: Event payload dictionary

    Returns:
        normalized_payload: Normalized payload dictionary

    """
    p: (
        UserInputPayload
        | ToolCallPayload
        | ToolResultPayload
        | ExplanationPayload
        | SessionEndPayload
        | ClarityViolationPayload
    )
    if event_type == EventType.USER_INPUT:
        p = UserInputPayload(**payload)
        return p.to_dict()
    if event_type == EventType.TOOL_CALL:
        p = ToolCallPayload(**payload)
        return p.to_dict()
    if event_type == EventType.TOOL_RESULT:
        p = ToolResultPayload(**payload)
        return p.to_dict()
    if event_type == EventType.EXPLANATION:
        p = ExplanationPayload(**payload)
        return p.to_dict()
    if event_type in (EventType.SESSION_END, EventType.CONSOLIDATION_CHECKPOINT):
        p = SessionEndPayload(**payload)
        return p.to_dict()
    if event_type == EventType.CLARITY_VIOLATION:
        p = ClarityViolationPayload(**payload)
        return p.to_dict()
    raise EventValidationError(f"Unknown event type: {event_type}")
