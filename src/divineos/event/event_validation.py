"""Event Validation Module.

Validates event payloads before they are stored in the ledger.
Prevents corrupted or malformed data from being persisted.
"""

import re
from typing import Any


class EventValidationError(Exception):
    """Raised when event validation fails."""


class EventValidator:
    """Validates event payloads for data integrity."""

    # Valid tool names (must start with letter, 2+ chars, alphanumeric/underscore/hyphen)
    # Examples: readFile, strReplace, executePwsh, list_events, delete-events
    # Rejects: 0, V, X, 4YhfT1, Valid, k2S (single char or starting with number)
    VALID_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,99}$")

    # Valid session ID format (UUID)
    VALID_SESSION_ID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    # Valid timestamp format (ISO8601)
    VALID_TIMESTAMP_PATTERN = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
    )

    @staticmethod
    def is_valid_tool_name(tool_name: str) -> bool:
        """Check if tool name is valid."""
        if not isinstance(tool_name, str):
            return False
        if len(tool_name) == 0 or len(tool_name) > 100:
            return False
        return EventValidator.VALID_TOOL_NAME_PATTERN.match(tool_name) is not None

    @staticmethod
    def is_valid_session_id(session_id: str) -> bool:
        """Check if session ID is valid UUID format."""
        if not isinstance(session_id, str):
            return False
        return EventValidator.VALID_SESSION_ID_PATTERN.match(session_id) is not None

    @staticmethod
    def is_valid_timestamp(timestamp: str) -> bool:
        """Check if timestamp is valid ISO8601 format."""
        if not isinstance(timestamp, str):
            return False
        return EventValidator.VALID_TIMESTAMP_PATTERN.match(timestamp) is not None

    @staticmethod
    def is_valid_tool_input_value(value: Any) -> bool:
        """Recursively validate tool_input values (supports nested structures)."""
        if isinstance(value, str):
            # Tool inputs are structured data (file paths, JSON, IDs) — not
            # human-readable prose. Accept any string; the content validator
            # rejects paths with backslashes and JSON with special chars.
            return True
        if isinstance(value, (int, float, bool, type(None))):
            return True
        if isinstance(value, dict):
            # Recursively validate nested dictionaries
            for k, v in value.items():
                if not isinstance(k, str):
                    return False
                if not EventValidator.is_valid_tool_input_value(v):
                    return False
            return True
        if isinstance(value, (list, tuple)):
            # Recursively validate list/tuple items
            return all(EventValidator.is_valid_tool_input_value(item) for item in value)
        # Unsupported type
        return False

    @staticmethod
    def is_valid_content(content: str, max_length: int = 1000000) -> bool:
        """Check if content is valid (readable text, not corrupted)."""
        if not isinstance(content, str):
            return False

        if len(content) == 0:
            return False

        if len(content) > max_length:
            return False

        # Check for excessive control characters (sign of corruption)
        control_char_count = sum(1 for c in content if ord(c) < 32 and c not in "\t\n\r")
        if control_char_count > len(content) * 0.1:  # More than 10% control chars
            return False

        # Check for invalid Unicode sequences
        try:
            content.encode("utf-8")
        except UnicodeEncodeError:
            return False

        # NEW: Check for garbage/corrupted content
        # Garbage detection: very short content with no spaces or punctuation
        # (except for legitimate short messages like "yes", "no", "ok")
        stripped = content.strip()

        # If content is very short (< 3 chars), it's likely garbage unless it's a known word
        if len(stripped) < 3:
            # Allow any single letter or common short words — users can type anything
            if len(stripped) == 1 and stripped.isalpha():
                return True
            common_short_words = {
                "ok",
                "no",
                "yes",
                "hi",
                "hey",
                "go",
                "do",
                "is",
                "it",
                "at",
                "to",
                "in",
                "on",
                "or",
                "if",
                "by",
                "up",
                "so",
                "we",
                "me",
                "he",
                "be",
                "as",
                "an",
                "a",
                "i",
            }
            if stripped.lower() not in common_short_words:
                return False

        # Check for random garbage: mostly non-alphanumeric characters
        # Real content should have mostly letters/numbers/spaces
        alphanumeric_count = sum(1 for c in stripped if c.isalnum() or c.isspace())
        alphanumeric_ratio = alphanumeric_count / len(stripped) if stripped else 0

        # If less than 50% alphanumeric, likely garbage
        if alphanumeric_ratio < 0.5:
            return False

        # Check for excessive special characters (more than 30% special chars)
        special_char_count = sum(1 for c in stripped if not c.isalnum() and not c.isspace())
        special_ratio = special_char_count / len(stripped) if stripped else 0
        return not special_ratio > 0.3

    @staticmethod
    def validate_user_input_payload(payload: dict[str, Any]) -> tuple[bool, str]:
        """Validate USER_INPUT event payload."""
        # Content is required
        if "content" not in payload:
            return False, "Missing required field: content"

        # Validate content
        content = payload.get("content", "")
        if not EventValidator.is_valid_content(content):
            return False, f"Invalid content: {content[:50]!r}"

        # Validate timestamp if provided
        if "timestamp" in payload:
            timestamp = payload.get("timestamp", "")
            if not EventValidator.is_valid_timestamp(timestamp):
                return False, f"Invalid timestamp: {timestamp}"

        # Validate session ID if provided - allow any non-empty string
        if "session_id" in payload:
            session_id = payload.get("session_id", "")
            if not isinstance(session_id, str) or len(session_id) == 0:
                return False, f"Invalid session ID: {session_id}"

        return True, "Valid"

    @staticmethod
    def validate_tool_call_payload(payload: dict[str, Any]) -> tuple[bool, str]:
        """Validate TOOL_CALL event payload."""
        # tool_name and tool_use_id are required
        if "tool_name" not in payload:
            return False, "Missing required field: tool_name"
        if "tool_use_id" not in payload:
            return False, "Missing required field: tool_use_id"

        # Validate tool name
        tool_name = payload.get("tool_name", "")
        if not EventValidator.is_valid_tool_name(tool_name):
            return False, f"Invalid tool name: {tool_name!r}"

        # Validate tool_input is a dict if provided
        if "tool_input" in payload:
            tool_input = payload.get("tool_input")
            if not isinstance(tool_input, dict):
                return False, f"tool_input must be a dict, got {type(tool_input)}"

            # Validate contents of tool_input dictionary using recursive validation
            for key, value in tool_input.items():
                # Keys must be strings
                if not isinstance(key, str):
                    return False, f"tool_input keys must be strings, got {type(key)}"

                # Validate value recursively (supports nested structures)
                if not EventValidator.is_valid_tool_input_value(value):
                    return False, f"Invalid tool_input value: {str(value)[:50]!r}"

        # Validate tool_use_id
        tool_use_id = payload.get("tool_use_id", "")
        if not isinstance(tool_use_id, str) or len(tool_use_id) == 0:
            return False, f"Invalid tool_use_id: {tool_use_id!r}"

        # Validate timestamp if provided
        if "timestamp" in payload:
            timestamp = payload.get("timestamp", "")
            if not EventValidator.is_valid_timestamp(timestamp):
                return False, f"Invalid timestamp: {timestamp}"

        # Validate session ID if provided - allow any non-empty string
        if "session_id" in payload:
            session_id = payload.get("session_id", "")
            if not isinstance(session_id, str) or len(session_id) == 0:
                return False, f"Invalid session ID: {session_id}"

        return True, "Valid"

    @staticmethod
    def validate_tool_result_payload(payload: dict[str, Any]) -> tuple[bool, str]:
        """Validate TOOL_RESULT event payload."""
        # tool_name and tool_use_id are required
        if "tool_name" not in payload:
            return False, "Missing required field: tool_name"
        if "tool_use_id" not in payload:
            return False, "Missing required field: tool_use_id"

        # Validate tool name
        tool_name = payload.get("tool_name", "")
        if not EventValidator.is_valid_tool_name(tool_name):
            return False, f"Invalid tool name: {tool_name!r}"

        # Validate result if provided — allow any non-empty string or valid JSON.
        # Tool results are often structured data (JSON dicts, lists), not
        # human-readable prose, so the standard content validator rejects them.
        if "result" in payload:
            result = payload.get("result", "")
            if not isinstance(result, str):
                return False, f"Invalid result type: {type(result).__name__}"

        # Validate duration_ms if provided
        if "duration_ms" in payload:
            duration_ms = payload.get("duration_ms")
            if not isinstance(duration_ms, (int, float)) or duration_ms < 0:
                return False, f"Invalid duration_ms: {duration_ms}"

        # Validate timestamp if provided
        if "timestamp" in payload:
            timestamp = payload.get("timestamp", "")
            if not EventValidator.is_valid_timestamp(timestamp):
                return False, f"Invalid timestamp: {timestamp}"

        # Validate session ID if provided - allow any non-empty string
        if "session_id" in payload:
            session_id = payload.get("session_id", "")
            if not isinstance(session_id, str) or len(session_id) == 0:
                return False, f"Invalid session ID: {session_id}"

        return True, "Valid"

    @staticmethod
    def validate_session_end_payload(payload: dict[str, Any]) -> tuple[bool, str]:
        """Validate SESSION_END event payload."""
        # session_id is required
        if "session_id" not in payload:
            return False, "Missing required field: session_id"

        # Validate session ID - allow any non-empty string (UUID or test session IDs)
        session_id = payload.get("session_id", "")
        if not isinstance(session_id, str) or len(session_id) == 0:
            return False, f"Invalid session ID: {session_id}"

        # Validate counts if provided
        for count_field in ["message_count", "tool_call_count", "tool_result_count"]:
            if count_field in payload:
                count = payload.get(count_field)
                if not isinstance(count, int) or count < 0:
                    return False, f"Invalid {count_field}: {count}"

        # Validate duration if provided
        if "duration_seconds" in payload:
            duration = payload.get("duration_seconds")
            if not isinstance(duration, (int, float)) or duration < 0:
                return False, f"Invalid duration_seconds: {duration}"

        # Validate timestamp if provided
        if "timestamp" in payload:
            timestamp = payload.get("timestamp", "")
            if not EventValidator.is_valid_timestamp(timestamp):
                return False, f"Invalid timestamp: {timestamp}"

        return True, "Valid"

    @staticmethod
    def validate_payload(event_type: str, payload: dict[str, Any]) -> tuple[bool, str]:
        """Validate a payload based on event type."""
        if event_type == "USER_INPUT":
            return EventValidator.validate_user_input_payload(payload)
        if event_type == "TOOL_CALL":
            return EventValidator.validate_tool_call_payload(payload)
        if event_type == "TOOL_RESULT":
            return EventValidator.validate_tool_result_payload(payload)
        if event_type == "SESSION_END":
            return EventValidator.validate_session_end_payload(payload)
        return False, f"Unknown event type: {event_type}"
