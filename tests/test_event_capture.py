"""Tests for event capture infrastructure."""

import pytest
from datetime import datetime, timezone
from divineos.event.event_capture import (
    EventType,
    EventValidationError,
    UserInputPayload,
    ToolCallPayload,
    ToolResultPayload,
    SessionEndPayload,
    SessionTracker,
    get_session_tracker,
    get_current_timestamp,
    validate_event_payload,
    normalize_event_payload,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_types_defined(self):
        """Test that all required event types are defined."""
        assert EventType.USER_INPUT.value == "USER_INPUT"
        assert EventType.TOOL_CALL.value == "TOOL_CALL"
        assert EventType.TOOL_RESULT.value == "TOOL_RESULT"
        assert EventType.SESSION_END.value == "SESSION_END"

    def test_event_type_string_conversion(self):
        """Test that event types can be converted to strings."""
        assert str(EventType.USER_INPUT) == "EventType.USER_INPUT"


class TestUserInputPayload:
    """Tests for USER_INPUT payload schema."""

    def test_valid_payload(self):
        """Test valid USER_INPUT payload."""
        payload = UserInputPayload(
            content="Hello, world!", timestamp="2026-03-16T23:05:00Z", session_id="abc123"
        )
        payload.validate()  # Should not raise

    def test_empty_content_fails(self):
        """Test that empty content fails validation."""
        payload = UserInputPayload(
            content="", timestamp="2026-03-16T23:05:00Z", session_id="abc123"
        )
        with pytest.raises(EventValidationError, match="content cannot be empty"):
            payload.validate()

    def test_whitespace_only_content_passes(self):
        """Test that whitespace-only content passes validation."""
        payload = UserInputPayload(
            content="   ", timestamp="2026-03-16T23:05:00Z", session_id="abc123"
        )
        # Should not raise - whitespace-only content is valid
        payload.validate()

    def test_non_string_content_fails(self):
        """Test that non-string content fails validation."""
        payload = UserInputPayload(
            content=123, timestamp="2026-03-16T23:05:00Z", session_id="abc123"
        )
        with pytest.raises(EventValidationError, match="content must be a string"):
            payload.validate()

    def test_invalid_timestamp_fails(self):
        """Test that invalid timestamp fails validation."""
        payload = UserInputPayload(
            content="Hello", timestamp="not-a-timestamp", session_id="abc123"
        )
        with pytest.raises(EventValidationError, match="timestamp must be valid ISO8601"):
            payload.validate()

    def test_empty_session_id_fails(self):
        """Test that empty session_id fails validation."""
        payload = UserInputPayload(content="Hello", timestamp="2026-03-16T23:05:00Z", session_id="")
        with pytest.raises(EventValidationError, match="session_id cannot be empty"):
            payload.validate()

    def test_to_dict(self):
        """Test conversion to dictionary."""
        payload = UserInputPayload(
            content="Hello", timestamp="2026-03-16T23:05:00Z", session_id="abc123"
        )
        data = payload.to_dict()
        assert data["content"] == "Hello"
        assert data["timestamp"] == "2026-03-16T23:05:00Z"
        assert data["session_id"] == "abc123"

    def test_large_content(self):
        """Test that very large content fails validation."""
        payload = UserInputPayload(
            content="x" * (1000001),  # 1MB + 1 byte
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        with pytest.raises(EventValidationError, match="content exceeds maximum length"):
            payload.validate()


class TestToolCallPayload:
    """Tests for TOOL_CALL payload schema."""

    def test_valid_payload(self):
        """Test valid TOOL_CALL payload."""
        payload = ToolCallPayload(
            tool_name="readFile",
            tool_input={"path": "src/main.py"},
            tool_use_id="tool_123",
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        payload.validate()  # Should not raise

    def test_empty_tool_name_fails(self):
        """Test that empty tool_name fails validation."""
        payload = ToolCallPayload(
            tool_name="",
            tool_input={"path": "src/main.py"},
            tool_use_id="tool_123",
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        with pytest.raises(EventValidationError, match="tool_name cannot be empty"):
            payload.validate()

    def test_non_dict_tool_input_fails(self):
        """Test that non-dict tool_input fails validation."""
        payload = ToolCallPayload(
            tool_name="readFile",
            tool_input="not a dict",
            tool_use_id="tool_123",
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        with pytest.raises(EventValidationError, match="tool_input must be a dictionary"):
            payload.validate()

    def test_empty_tool_use_id_fails(self):
        """Test that empty tool_use_id fails validation."""
        payload = ToolCallPayload(
            tool_name="readFile",
            tool_input={"path": "src/main.py"},
            tool_use_id="",
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        with pytest.raises(EventValidationError, match="tool_use_id cannot be empty"):
            payload.validate()

    def test_to_dict(self):
        """Test conversion to dictionary."""
        payload = ToolCallPayload(
            tool_name="readFile",
            tool_input={"path": "src/main.py"},
            tool_use_id="tool_123",
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        data = payload.to_dict()
        assert data["tool_name"] == "readFile"
        assert data["tool_input"] == {"path": "src/main.py"}
        assert data["tool_use_id"] == "tool_123"


class TestToolResultPayload:
    """Tests for TOOL_RESULT payload schema."""

    def test_valid_payload(self):
        """Test valid TOOL_RESULT payload."""
        payload = ToolResultPayload(
            tool_name="readFile",
            tool_use_id="tool_123",
            result="file content",
            duration_ms=45,
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        payload.validate()  # Should not raise

    def test_failed_result_requires_error_message(self):
        """Test that failed result requires error_message."""
        payload = ToolResultPayload(
            tool_name="readFile",
            tool_use_id="tool_123",
            result="error",
            duration_ms=45,
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
            failed=True,
            error_message=None,
        )
        with pytest.raises(EventValidationError, match="error_message required when failed=True"):
            payload.validate()

    def test_failed_result_with_error_message(self):
        """Test that failed result with error_message is valid."""
        payload = ToolResultPayload(
            tool_name="readFile",
            tool_use_id="tool_123",
            result="error",
            duration_ms=45,
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
            failed=True,
            error_message="File not found",
        )
        payload.validate()  # Should not raise

    def test_empty_result_fails(self):
        """Test that empty result fails validation."""
        payload = ToolResultPayload(
            tool_name="readFile",
            tool_use_id="tool_123",
            result="",
            duration_ms=45,
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        with pytest.raises(EventValidationError, match="result cannot be empty"):
            payload.validate()

    def test_negative_duration_fails(self):
        """Test that negative duration fails validation."""
        payload = ToolResultPayload(
            tool_name="readFile",
            tool_use_id="tool_123",
            result="content",
            duration_ms=-1,
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        with pytest.raises(EventValidationError, match="duration_ms cannot be negative"):
            payload.validate()

    def test_to_dict_excludes_none_values(self):
        """Test that to_dict excludes None values."""
        payload = ToolResultPayload(
            tool_name="readFile",
            tool_use_id="tool_123",
            result="content",
            duration_ms=45,
            timestamp="2026-03-16T23:05:00Z",
            session_id="abc123",
        )
        data = payload.to_dict()
        assert "error_message" not in data
        assert "failed" in data  # False is not None


class TestSessionEndPayload:
    """Tests for SESSION_END payload schema."""

    def test_valid_payload(self):
        """Test valid SESSION_END payload."""
        payload = SessionEndPayload(
            session_id="abc123",
            message_count=15,
            tool_call_count=8,
            tool_result_count=8,
            duration_seconds=300.5,
            timestamp="2026-03-16T23:05:00Z",
        )
        payload.validate()  # Should not raise

    def test_negative_message_count_fails(self):
        """Test that negative message_count fails validation."""
        payload = SessionEndPayload(
            session_id="abc123",
            message_count=-1,
            tool_call_count=8,
            tool_result_count=8,
            duration_seconds=300,
            timestamp="2026-03-16T23:05:00Z",
        )
        with pytest.raises(EventValidationError, match="message_count cannot be negative"):
            payload.validate()

    def test_zero_counts_valid(self):
        """Test that zero counts are valid."""
        payload = SessionEndPayload(
            session_id="abc123",
            message_count=0,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=0,
            timestamp="2026-03-16T23:05:00Z",
        )
        payload.validate()  # Should not raise

    def test_to_dict(self):
        """Test conversion to dictionary."""
        payload = SessionEndPayload(
            session_id="abc123",
            message_count=15,
            tool_call_count=8,
            tool_result_count=8,
            duration_seconds=300.5,
            timestamp="2026-03-16T23:05:00Z",
        )
        data = payload.to_dict()
        assert data["session_id"] == "abc123"
        assert data["message_count"] == 15
        assert data["tool_call_count"] == 8
        assert data["tool_result_count"] == 8
        assert data["duration_seconds"] == 300.5


class TestSessionTracker:
    """Tests for SessionTracker."""

    def test_start_session_returns_id(self):
        """Test that start_session returns a session ID."""
        tracker = SessionTracker()
        session_id = tracker.start_session()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_start_session_generates_unique_ids(self):
        """Test that start_session generates unique IDs."""
        tracker = SessionTracker()
        id1 = tracker.start_session()
        id2 = tracker.start_session()
        assert id1 != id2

    def test_get_current_session_id(self):
        """Test getting current session ID."""
        tracker = SessionTracker()
        session_id = tracker.start_session()
        assert tracker.get_current_session_id() == session_id

    def test_get_current_session_id_creates_if_none(self):
        """Test that get_current_session_id creates session if none exists."""
        tracker = SessionTracker()
        session_id = tracker.get_current_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_end_session(self):
        """Test ending a session."""
        tracker = SessionTracker()
        session_id = tracker.start_session()
        ended_id = tracker.end_session()
        assert ended_id == session_id

    def test_end_session_when_none_active(self):
        """Test ending session when none is active."""
        # With the fix, SessionTracker always initializes with a session_id
        # (either from persistent file or newly generated)
        # So end_session() will always return a session_id, never None
        tracker = SessionTracker()
        result = tracker.end_session()
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_session_duration(self):
        """Test getting session duration."""
        import time

        tracker = SessionTracker()
        tracker.start_session()
        time.sleep(0.1)  # Sleep for 100ms
        duration = tracker.get_session_duration()
        assert duration is not None
        assert duration >= 0.1

    def test_get_session_duration_when_none_active(self):
        """Test getting duration when no session is active."""
        # With the fix, SessionTracker always initializes with a session_id and start time
        # So get_session_duration() will always return a duration (not None)
        tracker = SessionTracker()
        duration = tracker.get_session_duration()
        assert duration is not None
        assert isinstance(duration, float)
        assert duration >= 0

    def test_get_session_tracker_returns_singleton(self):
        """Test that get_session_tracker returns the same instance."""
        tracker1 = get_session_tracker()
        tracker2 = get_session_tracker()
        assert tracker1 is tracker2


class TestGetCurrentTimestamp:
    """Tests for get_current_timestamp function."""

    def test_returns_iso8601_string(self):
        """Test that timestamp is ISO8601 format."""
        ts = get_current_timestamp()
        assert isinstance(ts, str)
        assert ts.endswith("Z")

    def test_timestamp_is_parseable(self):
        """Test that timestamp can be parsed."""
        ts = get_current_timestamp()
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert isinstance(dt, datetime)

    def test_timestamp_is_recent(self):
        """Test that timestamp is recent (within 1 second)."""
        ts = get_current_timestamp()
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds()
        assert diff < 1


class TestValidateEventPayload:
    """Tests for validate_event_payload function."""

    def test_validate_user_input(self):
        """Test validating USER_INPUT payload."""
        payload = {"content": "Hello", "timestamp": "2026-03-16T23:05:00Z", "session_id": "abc123"}
        validate_event_payload(EventType.USER_INPUT, payload)  # Should not raise

    def test_validate_tool_call(self):
        """Test validating TOOL_CALL payload."""
        payload = {
            "tool_name": "readFile",
            "tool_input": {"path": "src/main.py"},
            "tool_use_id": "tool_123",
            "timestamp": "2026-03-16T23:05:00Z",
            "session_id": "abc123",
        }
        validate_event_payload(EventType.TOOL_CALL, payload)  # Should not raise

    def test_validate_tool_result(self):
        """Test validating TOOL_RESULT payload."""
        payload = {
            "tool_name": "readFile",
            "tool_use_id": "tool_123",
            "result": "content",
            "duration_ms": 45,
            "timestamp": "2026-03-16T23:05:00Z",
            "session_id": "abc123",
        }
        validate_event_payload(EventType.TOOL_RESULT, payload)  # Should not raise

    def test_validate_session_end(self):
        """Test validating SESSION_END payload."""
        payload = {
            "session_id": "abc123",
            "message_count": 15,
            "tool_call_count": 8,
            "tool_result_count": 8,
            "duration_seconds": 300,
            "timestamp": "2026-03-16T23:05:00Z",
        }
        validate_event_payload(EventType.SESSION_END, payload)  # Should not raise

    def test_validate_missing_fields(self):
        """Test that missing fields raise error."""
        payload = {
            "content": "Hello",
            "timestamp": "2026-03-16T23:05:00Z",
            # Missing session_id
        }
        with pytest.raises(EventValidationError, match="Missing required fields"):
            validate_event_payload(EventType.USER_INPUT, payload)

    def test_validate_invalid_event_type(self):
        """Test that invalid event type raises error."""
        payload = {}
        with pytest.raises(EventValidationError, match="Unknown event type"):
            validate_event_payload("INVALID_TYPE", payload)


class TestNormalizeEventPayload:
    """Tests for normalize_event_payload function."""

    def test_normalize_user_input(self):
        """Test normalizing USER_INPUT payload."""
        payload = {"content": "Hello", "timestamp": "2026-03-16T23:05:00Z", "session_id": "abc123"}
        normalized = normalize_event_payload(EventType.USER_INPUT, payload)
        assert normalized["content"] == "Hello"
        assert normalized["timestamp"] == "2026-03-16T23:05:00Z"
        assert normalized["session_id"] == "abc123"

    def test_normalize_tool_result_excludes_none(self):
        """Test that normalize excludes None values from TOOL_RESULT."""
        payload = {
            "tool_name": "readFile",
            "tool_use_id": "tool_123",
            "result": "content",
            "duration_ms": 45,
            "timestamp": "2026-03-16T23:05:00Z",
            "session_id": "abc123",
        }
        normalized = normalize_event_payload(EventType.TOOL_RESULT, payload)
        assert "error_message" not in normalized

    def test_normalize_invalid_event_type(self):
        """Test that invalid event type raises error."""
        with pytest.raises(EventValidationError, match="Unknown event type"):
            normalize_event_payload("INVALID_TYPE", {})
