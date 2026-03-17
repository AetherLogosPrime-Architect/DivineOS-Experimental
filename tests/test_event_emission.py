"""Tests for event emission module."""

import pytest
import os
import tempfile
from datetime import datetime

from divineos.event_emission import (
    emit_user_input,
    emit_tool_call,
    emit_tool_result,
    emit_session_end,
)
from divineos.event_capture import (
    EventValidationError,
    get_session_tracker,
)
from divineos.ledger import get_events, init_db


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_ledger.db")
        os.environ["DIVINEOS_DB"] = db_path
        init_db()
        yield db_path
        if "DIVINEOS_DB" in os.environ:
            del os.environ["DIVINEOS_DB"]


@pytest.fixture
def fresh_session():
    """Create a fresh session for each test."""
    # Clear persistent session file to ensure fresh session
    from pathlib import Path
    session_file = Path.home() / ".divineos" / "current_session.txt"
    if session_file.exists():
        session_file.unlink()
    
    tracker = get_session_tracker()
    tracker.start_session()
    yield tracker
    tracker.end_session()


class TestEmitUserInput:
    """Tests for emit_user_input function."""

    def test_emit_user_input_basic(self, temp_db, fresh_session):
        """Test basic USER_INPUT event emission."""
        event_id = emit_user_input("Hello, world!")
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        # Verify event was stored in ledger
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["event_type"] == "USER_INPUT"
        assert events[0]["actor"] == "user"
        assert events[0]["payload"]["content"] == "Hello, world!"

    def test_emit_user_input_with_session_id(self, temp_db):
        """Test USER_INPUT event with explicit session ID."""
        session_id = "test-session-123"
        event_id = emit_user_input("Test message", session_id=session_id)
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] == session_id

    def test_emit_user_input_includes_timestamp(self, temp_db, fresh_session):
        """Test that USER_INPUT event includes ISO8601 timestamp."""
        event_id = emit_user_input("Test message")
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        
        timestamp = events[0]["payload"]["timestamp"]
        assert timestamp is not None
        # Verify it's valid ISO8601
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_emit_user_input_includes_session_id(self, temp_db, fresh_session):
        """Test that USER_INPUT event includes session ID."""
        event_id = emit_user_input("Test message")
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] is not None

    def test_emit_user_input_includes_hash(self, temp_db, fresh_session):
        """Test that USER_INPUT event includes SHA256 hash."""
        event_id = emit_user_input("Test message")
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["content_hash"] is not None
        assert len(events[0]["content_hash"]) == 32  # SHA256 truncated to 32 chars

    def test_emit_user_input_empty_content_fails(self, temp_db, fresh_session):
        """Test that empty content fails validation."""
        with pytest.raises(EventValidationError, match="content cannot be empty"):
            emit_user_input("")

    def test_emit_user_input_whitespace_only_passes(self, temp_db, fresh_session):
        """Test that whitespace-only content passes validation and is emitted."""
        # Should not raise - whitespace-only content is valid
        event_id = emit_user_input("   ")
        assert event_id is not None
        assert isinstance(event_id, str)

    def test_emit_user_input_long_content(self, temp_db, fresh_session):
        """Test USER_INPUT with long content."""
        long_content = "x" * 100000  # 100KB
        event_id = emit_user_input(long_content)
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["payload"]["content"] == long_content

    def test_emit_user_input_special_characters(self, temp_db, fresh_session):
        """Test USER_INPUT with special characters."""
        content = "Hello 🌍! Special chars: @#$%^&*()"
        event_id = emit_user_input(content)
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["payload"]["content"] == content

    def test_emit_user_input_multiple_events(self, temp_db, fresh_session):
        """Test emitting multiple USER_INPUT events."""
        event_id_1 = emit_user_input("Message 1")
        event_id_2 = emit_user_input("Message 2")
        event_id_3 = emit_user_input("Message 3")
        
        assert event_id_1 != event_id_2
        assert event_id_2 != event_id_3
        
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 3


class TestEmitToolCall:
    """Tests for emit_tool_call function."""

    def test_emit_tool_call_basic(self, temp_db, fresh_session):
        """Test basic TOOL_CALL event emission."""
        tool_input = {"path": "src/main.py"}
        event_id = emit_tool_call("readFile", tool_input)
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["event_type"] == "TOOL_CALL"
        assert events[0]["actor"] == "assistant"
        assert events[0]["payload"]["tool_name"] == "readFile"
        assert events[0]["payload"]["tool_input"] == tool_input

    def test_emit_tool_call_with_tool_use_id(self, temp_db, fresh_session):
        """Test TOOL_CALL event with explicit tool_use_id."""
        tool_use_id = "tool-use-123"
        event_id = emit_tool_call("readFile", {"path": "file.py"}, tool_use_id=tool_use_id)
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["payload"]["tool_use_id"] == tool_use_id

    def test_emit_tool_call_generates_tool_use_id(self, temp_db, fresh_session):
        """Test that TOOL_CALL generates tool_use_id if not provided."""
        event_id = emit_tool_call("readFile", {"path": "file.py"})
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["payload"]["tool_use_id"] is not None

    def test_emit_tool_call_includes_timestamp(self, temp_db, fresh_session):
        """Test that TOOL_CALL event includes ISO8601 timestamp."""
        event_id = emit_tool_call("readFile", {"path": "file.py"})
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        
        timestamp = events[0]["payload"]["timestamp"]
        assert timestamp is not None
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_emit_tool_call_includes_session_id(self, temp_db, fresh_session):
        """Test that TOOL_CALL event includes session ID."""
        event_id = emit_tool_call("readFile", {"path": "file.py"})
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] is not None

    def test_emit_tool_call_includes_hash(self, temp_db, fresh_session):
        """Test that TOOL_CALL event includes SHA256 hash."""
        event_id = emit_tool_call("readFile", {"path": "file.py"})
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["content_hash"] is not None
        assert len(events[0]["content_hash"]) == 32

    def test_emit_tool_call_empty_tool_name_fails(self, temp_db, fresh_session):
        """Test that empty tool_name fails validation."""
        with pytest.raises(EventValidationError, match="tool_name cannot be empty"):
            emit_tool_call("", {"path": "file.py"})

    def test_emit_tool_call_complex_input(self, temp_db, fresh_session):
        """Test TOOL_CALL with complex nested input."""
        tool_input = {
            "path": "file.py",
            "oldStr": "def foo():\n    pass",
            "newStr": "def foo():\n    return 42",
            "nested": {
                "key1": "value1",
                "key2": [1, 2, 3],
            }
        }
        event_id = emit_tool_call("strReplace", tool_input)
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["payload"]["tool_input"] == tool_input

    def test_emit_tool_call_multiple_events(self, temp_db, fresh_session):
        """Test emitting multiple TOOL_CALL events."""
        event_id_1 = emit_tool_call("readFile", {"path": "file1.py"})
        event_id_2 = emit_tool_call("strReplace", {"path": "file2.py"})
        event_id_3 = emit_tool_call("fsWrite", {"path": "file3.py"})
        
        assert event_id_1 != event_id_2
        assert event_id_2 != event_id_3
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 3


class TestEmitToolResult:
    """Tests for emit_tool_result function."""

    def test_emit_tool_result_basic(self, temp_db, fresh_session):
        """Test basic TOOL_RESULT event emission."""
        tool_use_id = "tool-use-123"
        result = "File content here"
        event_id = emit_tool_result("readFile", tool_use_id, result, 45)
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["event_type"] == "TOOL_RESULT"
        assert events[0]["actor"] == "system"
        assert events[0]["payload"]["tool_name"] == "readFile"
        assert events[0]["payload"]["tool_use_id"] == tool_use_id
        assert events[0]["payload"]["result"] == result
        assert events[0]["payload"]["duration_ms"] == 45

    def test_emit_tool_result_with_session_id(self, temp_db):
        """Test TOOL_RESULT event with explicit session ID."""
        session_id = "test-session-123"
        event_id = emit_tool_result(
            "readFile",
            "tool-use-123",
            "Result content",
            50,
            session_id=session_id
        )
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] == session_id

    def test_emit_tool_result_includes_timestamp(self, temp_db, fresh_session):
        """Test that TOOL_RESULT event includes ISO8601 timestamp."""
        event_id = emit_tool_result("readFile", "tool-use-123", "Result", 50)
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        
        timestamp = events[0]["payload"]["timestamp"]
        assert timestamp is not None
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_emit_tool_result_includes_session_id(self, temp_db, fresh_session):
        """Test that TOOL_RESULT event includes session ID."""
        event_id = emit_tool_result("readFile", "tool-use-123", "Result", 50)
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] is not None

    def test_emit_tool_result_includes_hash(self, temp_db, fresh_session):
        """Test that TOOL_RESULT event includes SHA256 hash."""
        event_id = emit_tool_result("readFile", "tool-use-123", "Result", 50)
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["content_hash"] is not None
        assert len(events[0]["content_hash"]) == 32

    def test_emit_tool_result_success(self, temp_db, fresh_session):
        """Test TOOL_RESULT event for successful execution."""
        event_id = emit_tool_result("readFile", "tool-use-123", "Result", 50, failed=False)
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["failed"] is False
        assert "error_message" not in events[0]["payload"]

    def test_emit_tool_result_failure(self, temp_db, fresh_session):
        """Test TOOL_RESULT event for failed execution."""
        error_msg = "File not found"
        event_id = emit_tool_result(
            "readFile",
            "tool-use-123",
            "Error occurred",
            50,
            failed=True,
            error_message=error_msg
        )
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["failed"] is True
        assert events[0]["payload"]["error_message"] == error_msg

    def test_emit_tool_result_long_output(self, temp_db, fresh_session):
        """Test TOOL_RESULT with long output."""
        long_result = "x" * 1000000  # 1MB
        event_id = emit_tool_result("readFile", "tool-use-123", long_result, 100)
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["result"] == long_result

    def test_emit_tool_result_empty_result_fails(self, temp_db, fresh_session):
        """Test that empty result fails validation."""
        with pytest.raises(EventValidationError, match="result cannot be empty"):
            emit_tool_result("readFile", "tool-use-123", "", 50)

    def test_emit_tool_result_negative_duration_fails(self, temp_db, fresh_session):
        """Test that negative duration fails validation."""
        with pytest.raises(EventValidationError, match="duration_ms cannot be negative"):
            emit_tool_result("readFile", "tool-use-123", "Result", -1)

    def test_emit_tool_result_multiple_events(self, temp_db, fresh_session):
        """Test emitting multiple TOOL_RESULT events."""
        event_id_1 = emit_tool_result("readFile", "tool-1", "Result 1", 45)
        event_id_2 = emit_tool_result("strReplace", "tool-2", "Result 2", 50)
        event_id_3 = emit_tool_result("fsWrite", "tool-3", "Result 3", 55)
        
        assert event_id_1 != event_id_2
        assert event_id_2 != event_id_3
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 3


class TestEmitSessionEnd:
    """Tests for emit_session_end function."""

    def test_emit_session_end_basic(self, temp_db, fresh_session):
        """Test basic SESSION_END event emission."""
        # Emit some events first
        emit_user_input("Message 1")
        emit_user_input("Message 2")
        emit_tool_call("readFile", {"path": "file.py"})
        emit_tool_result("readFile", "tool-1", "Result", 50)
        
        event_id = emit_session_end()
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["event_type"] == "SESSION_END"
        assert events[0]["actor"] == "system"

    def test_emit_session_end_with_explicit_session_id(self, temp_db):
        """Test SESSION_END event with explicit session ID."""
        session_id = "test-session-123"
        event_id = emit_session_end(
            session_id=session_id,
            message_count=5,
            tool_call_count=3,
            tool_result_count=3,
            duration_seconds=60.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] == session_id

    def test_emit_session_end_includes_message_count(self, temp_db, fresh_session):
        """Test that SESSION_END includes message count."""
        emit_user_input("Message 1")
        emit_user_input("Message 2")
        
        event_id = emit_session_end(
            message_count=2,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=30.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["message_count"] == 2

    def test_emit_session_end_includes_tool_call_count(self, temp_db, fresh_session):
        """Test that SESSION_END includes tool call count."""
        emit_tool_call("readFile", {"path": "file.py"})
        emit_tool_call("strReplace", {"path": "file.py"})
        
        event_id = emit_session_end(
            message_count=0,
            tool_call_count=2,
            tool_result_count=0,
            duration_seconds=30.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["tool_call_count"] == 2

    def test_emit_session_end_includes_tool_result_count(self, temp_db, fresh_session):
        """Test that SESSION_END includes tool result count."""
        emit_tool_result("readFile", "tool-1", "Result 1", 50)
        emit_tool_result("strReplace", "tool-2", "Result 2", 50)
        
        event_id = emit_session_end(
            message_count=0,
            tool_call_count=0,
            tool_result_count=2,
            duration_seconds=30.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["tool_result_count"] == 2

    def test_emit_session_end_includes_duration(self, temp_db, fresh_session):
        """Test that SESSION_END includes duration."""
        event_id = emit_session_end(
            message_count=0,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=120.5
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["duration_seconds"] == 120.5

    def test_emit_session_end_includes_timestamp(self, temp_db, fresh_session):
        """Test that SESSION_END event includes ISO8601 timestamp."""
        event_id = emit_session_end(
            message_count=0,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=30.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        
        timestamp = events[0]["payload"]["timestamp"]
        assert timestamp is not None
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_emit_session_end_includes_hash(self, temp_db, fresh_session):
        """Test that SESSION_END event includes SHA256 hash."""
        event_id = emit_session_end(
            message_count=0,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=30.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["content_hash"] is not None
        assert len(events[0]["content_hash"]) == 32

    def test_emit_session_end_zero_counts(self, temp_db, fresh_session):
        """Test SESSION_END with zero event counts."""
        event_id = emit_session_end(
            message_count=0,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=0.0
        )
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["message_count"] == 0
        assert events[0]["payload"]["tool_call_count"] == 0
        assert events[0]["payload"]["tool_result_count"] == 0
        assert events[0]["payload"]["duration_seconds"] == 0.0

    def test_emit_session_end_negative_message_count_fails(self, temp_db, fresh_session):
        """Test that negative message_count fails validation."""
        with pytest.raises(EventValidationError, match="message_count cannot be negative"):
            emit_session_end(
                message_count=-1,
                tool_call_count=0,
                tool_result_count=0,
                duration_seconds=30.0
            )

    def test_emit_session_end_negative_duration_fails(self, temp_db, fresh_session):
        """Test that negative duration fails validation."""
        with pytest.raises(EventValidationError, match="duration_seconds cannot be negative"):
            emit_session_end(
                message_count=0,
                tool_call_count=0,
                tool_result_count=0,
                duration_seconds=-1.0
            )


class TestEventEmissionIntegration:
    """Integration tests for event emission."""

    def test_emit_all_event_types(self, temp_db, fresh_session):
        """Test emitting all four event types in sequence."""
        # Emit USER_INPUT
        user_event_id = emit_user_input("Hello, world!")
        
        # Emit TOOL_CALL
        tool_call_id = emit_tool_call("readFile", {"path": "file.py"})
        
        # Emit TOOL_RESULT
        tool_result_id = emit_tool_result("readFile", tool_call_id, "File content", 50)
        
        # Emit SESSION_END
        session_end_id = emit_session_end(
            message_count=1,
            tool_call_count=1,
            tool_result_count=1,
            duration_seconds=60.0
        )
        
        # Verify all events are in ledger
        all_events = get_events(limit=100)
        assert len(all_events) == 4
        
        event_types = [e["event_type"] for e in all_events]
        assert "USER_INPUT" in event_types
        assert "TOOL_CALL" in event_types
        assert "TOOL_RESULT" in event_types
        assert "SESSION_END" in event_types

    def test_events_have_consistent_session_id(self, temp_db, fresh_session):
        """Test that all events in a session have the same session ID."""
        emit_user_input("Message 1")
        emit_tool_call("readFile", {"path": "file.py"})
        emit_tool_result("readFile", "tool-1", "Result", 50)
        emit_session_end(
            message_count=1,
            tool_call_count=1,
            tool_result_count=1,
            duration_seconds=30.0
        )
        
        all_events = get_events(limit=100)
        session_ids = [e["payload"].get("session_id") for e in all_events]
        
        # All should have the same session ID
        assert len(set(session_ids)) == 1

    def test_events_are_chronologically_ordered(self, temp_db, fresh_session):
        """Test that events are stored in chronological order."""
        emit_user_input("Message 1")
        emit_user_input("Message 2")
        emit_user_input("Message 3")
        
        events = get_events(limit=100, event_type="USER_INPUT")
        assert len(events) == 3
        
        # Verify timestamps are in order
        timestamps = [e["payload"]["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)

    def test_event_hashes_are_valid(self, temp_db, fresh_session):
        """Test that all event hashes are valid SHA256 hashes."""
        emit_user_input("Message 1")
        emit_tool_call("readFile", {"path": "file.py"})
        emit_tool_result("readFile", "tool-1", "Result", 50)
        
        events = get_events(limit=100)
        
        for event in events:
            content_hash = event["content_hash"]
            assert content_hash is not None
            assert len(content_hash) == 32  # SHA256 truncated to 32 chars
            # Verify it's a valid hex string
            assert all(c in "0123456789abcdef" for c in content_hash)
