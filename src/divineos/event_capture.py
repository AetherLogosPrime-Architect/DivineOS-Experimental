"""
Event Capture Infrastructure — Core data structures and validation for IDE events.

This module provides:
- Event type enums (USER_INPUT, TOOL_CALL, TOOL_RESULT, SESSION_END)
- Payload schemas for each event type
- Validation functions for event payloads
- Session ID generation and tracking
- Event normalization and enrichment
"""

import json
import uuid
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Dict
from dataclasses import dataclass, asdict
from loguru import logger


class EventType(str, Enum):
    """Supported event types for IDE integration."""
    USER_INPUT = "USER_INPUT"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    EXPLANATION = "EXPLANATION"
    SESSION_END = "SESSION_END"


class EventValidationError(Exception):
    """Raised when event payload validation fails."""
    pass


@dataclass
class UserInputPayload:
    """Payload schema for USER_INPUT events."""
    content: str
    timestamp: str
    session_id: str

    def validate(self) -> None:
        """Validate USER_INPUT payload."""
        if not isinstance(self.content, str):
            raise EventValidationError("content must be a string")
        if not self.content:
            raise EventValidationError("content cannot be empty")
        if len(self.content) > 1000000:  # 1MB limit
            raise EventValidationError("content exceeds maximum length (1MB)")
        
        if not isinstance(self.timestamp, str):
            raise EventValidationError("timestamp must be a string")
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise EventValidationError("timestamp must be valid ISO8601 format")
        
        if not isinstance(self.session_id, str):
            raise EventValidationError("session_id must be a string")
        if not self.session_id:
            raise EventValidationError("session_id cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ToolCallPayload:
    """Payload schema for TOOL_CALL events."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_use_id: str
    timestamp: str
    session_id: str

    def validate(self) -> None:
        """Validate TOOL_CALL payload."""
        if not isinstance(self.tool_name, str):
            raise EventValidationError("tool_name must be a string")
        if not self.tool_name:
            raise EventValidationError("tool_name cannot be empty")
        
        if not isinstance(self.tool_input, dict):
            raise EventValidationError("tool_input must be a dictionary")
        
        if not isinstance(self.tool_use_id, str):
            raise EventValidationError("tool_use_id must be a string")
        if not self.tool_use_id:
            raise EventValidationError("tool_use_id cannot be empty")
        
        if not isinstance(self.timestamp, str):
            raise EventValidationError("timestamp must be a string")
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise EventValidationError("timestamp must be valid ISO8601 format")
        
        if not isinstance(self.session_id, str):
            raise EventValidationError("session_id must be a string")
        if not self.session_id:
            raise EventValidationError("session_id cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
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
    error_message: Optional[str] = None

    def validate(self) -> None:
        """Validate TOOL_RESULT payload."""
        if not isinstance(self.tool_name, str):
            raise EventValidationError("tool_name must be a string")
        if not self.tool_name:
            raise EventValidationError("tool_name cannot be empty")
        
        if not isinstance(self.tool_use_id, str):
            raise EventValidationError("tool_use_id must be a string")
        if not self.tool_use_id:
            raise EventValidationError("tool_use_id cannot be empty")
        
        if not isinstance(self.result, str):
            raise EventValidationError("result must be a string")
        if not self.result:
            raise EventValidationError("result cannot be empty")
        if len(self.result) > 10000000:  # 10MB limit
            raise EventValidationError("result exceeds maximum length (10MB)")
        
        if not isinstance(self.duration_ms, int):
            raise EventValidationError("duration_ms must be an integer")
        if self.duration_ms < 0:
            raise EventValidationError("duration_ms cannot be negative")
        
        if not isinstance(self.timestamp, str):
            raise EventValidationError("timestamp must be a string")
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise EventValidationError("timestamp must be valid ISO8601 format")
        
        if not isinstance(self.session_id, str):
            raise EventValidationError("session_id must be a string")
        if not self.session_id:
            raise EventValidationError("session_id cannot be empty")
        
        if not isinstance(self.failed, bool):
            raise EventValidationError("failed must be a boolean")
        
        if self.failed and not self.error_message:
            raise EventValidationError("error_message required when failed=True")
        if self.error_message and not isinstance(self.error_message, str):
            raise EventValidationError("error_message must be a string")

    def to_dict(self) -> Dict[str, Any]:
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
            raise EventValidationError("explanation_text must be a string")
        if not self.explanation_text:
            raise EventValidationError("explanation_text cannot be empty")
        if len(self.explanation_text) > 1000000:  # 1MB limit
            raise EventValidationError("explanation_text exceeds maximum length (1MB)")
        
        if not isinstance(self.timestamp, str):
            raise EventValidationError("timestamp must be a string")
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise EventValidationError("timestamp must be valid ISO8601 format")
        
        if not isinstance(self.session_id, str):
            raise EventValidationError("session_id must be a string")
        if not self.session_id:
            raise EventValidationError("session_id cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SessionEndPayload:
    """Payload schema for SESSION_END events."""
    session_id: str
    message_count: int
    tool_call_count: int
    tool_result_count: int
    duration_seconds: float
    timestamp: str

    def validate(self) -> None:
        """Validate SESSION_END payload."""
        if not isinstance(self.session_id, str):
            raise EventValidationError("session_id must be a string")
        if not self.session_id:
            raise EventValidationError("session_id cannot be empty")
        
        if not isinstance(self.message_count, int):
            raise EventValidationError("message_count must be an integer")
        if self.message_count < 0:
            raise EventValidationError("message_count cannot be negative")
        
        if not isinstance(self.tool_call_count, int):
            raise EventValidationError("tool_call_count must be an integer")
        if self.tool_call_count < 0:
            raise EventValidationError("tool_call_count cannot be negative")
        
        if not isinstance(self.tool_result_count, int):
            raise EventValidationError("tool_result_count must be an integer")
        if self.tool_result_count < 0:
            raise EventValidationError("tool_result_count cannot be negative")
        
        if not isinstance(self.duration_seconds, (int, float)):
            raise EventValidationError("duration_seconds must be a number")
        if self.duration_seconds < 0:
            raise EventValidationError("duration_seconds cannot be negative")
        
        if not isinstance(self.timestamp, str):
            raise EventValidationError("timestamp must be a string")
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise EventValidationError("timestamp must be valid ISO8601 format")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SessionTracker:
    """Manages session ID generation and tracking."""

    def __init__(self):
        """Initialize session tracker."""
        self._current_session_id: Optional[str] = None
        self._session_start_time: Optional[float] = None

    def start_session(self) -> str:
        """
        Start a new session and return the session ID.
        
        Returns:
            session_id: Unique identifier for the session
        """
        self._current_session_id = str(uuid.uuid4())
        self._session_start_time = time.time()
        logger.debug(f"Started session: {self._current_session_id}")
        return self._current_session_id

    def get_current_session_id(self) -> str:
        """
        Get the current session ID.
        
        Returns:
            session_id: Current session ID (always set after __init__)
        """
        # Should never be None after __init__, but handle gracefully
        if self._current_session_id is None:
            logger.warning("Session ID is None, generating new one")
            return self.start_session()
        return self._current_session_id

    def end_session(self) -> Optional[str]:
        """
        End the current session.
        
        Returns:
            session_id: The session ID that was ended, or None if no session active
        """
        if self._current_session_id is None:
            return None
        
        session_id = self._current_session_id
        self._current_session_id = None
        self._session_start_time = None
        logger.debug(f"Ended session: {session_id}")
        return session_id

    def get_session_duration(self) -> Optional[float]:
        """
        Get the duration of the current session in seconds.
        
        Returns:
            duration: Duration in seconds, or None if no session active
        """
        if self._session_start_time is None:
            return None
        return time.time() - self._session_start_time


# Global session tracker instance
_session_tracker = SessionTracker()


def get_session_tracker() -> SessionTracker:
    """Get the global session tracker instance."""
    return _session_tracker


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO8601 format.
    
    Returns:
        timestamp: ISO8601 formatted timestamp with UTC timezone
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_event_payload(event_type: EventType, payload: Dict[str, Any]) -> None:
    """
    Validate an event payload against its schema.
    
    Args:
        event_type: Type of event
        payload: Event payload dictionary
        
    Raises:
        EventValidationError: If payload is invalid
    """
    try:
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
        elif event_type == EventType.SESSION_END:
            p = SessionEndPayload(**payload)
            p.validate()
        else:
            raise EventValidationError(f"Unknown event type: {event_type}")
    except TypeError as e:
        raise EventValidationError(f"Missing required fields: {e}")


def normalize_event_payload(event_type: EventType, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an event payload to ensure consistency.
    
    Args:
        event_type: Type of event
        payload: Event payload dictionary
        
    Returns:
        normalized_payload: Normalized payload dictionary
    """
    if event_type == EventType.USER_INPUT:
        p = UserInputPayload(**payload)
        return p.to_dict()
    elif event_type == EventType.TOOL_CALL:
        p = ToolCallPayload(**payload)
        return p.to_dict()
    elif event_type == EventType.TOOL_RESULT:
        p = ToolResultPayload(**payload)
        return p.to_dict()
    elif event_type == EventType.EXPLANATION:
        p = ExplanationPayload(**payload)
        return p.to_dict()
    elif event_type == EventType.SESSION_END:
        p = SessionEndPayload(**payload)
        return p.to_dict()
    else:
        raise EventValidationError(f"Unknown event type: {event_type}")
