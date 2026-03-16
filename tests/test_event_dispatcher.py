"""Tests for the event dispatcher and event capture system."""

import pytest
from divineos.event_dispatcher import emit_event, register_listener, get_dispatcher
from divineos.ledger import get_events, verify_all_events


@pytest.fixture(autouse=True)
def setup_dispatcher(tmp_path, monkeypatch):
    """Initialize dispatcher for each test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    
    from divineos.ledger import init_db
    init_db()
    
    yield


class TestEventDispatcher:
    """Test the event dispatcher."""

    def test_emit_user_input(self):
        """Test emitting a USER_INPUT event."""
        event_id = emit_event(
            "USER_INPUT",
            {"content": "How should I structure this?"},
            actor="user"
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        assert len(events) > 0
        
        user_event = next((e for e in events if e["event_type"] == "USER_INPUT"), None)
        assert user_event is not None
        assert user_event["payload"]["content"] == "How should I structure this?"

    def test_emit_assistant_output(self):
        """Test emitting an ASSISTANT_OUTPUT event."""
        event_id = emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I'd recommend organizing by responsibility."},
            actor="assistant"
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        assistant_event = next((e for e in events if e["event_type"] == "ASSISTANT_OUTPUT"), None)
        assert assistant_event is not None
        assert "responsibility" in assistant_event["payload"]["content"]

    def test_emit_tool_call(self):
        """Test emitting a TOOL_CALL event."""
        event_id = emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "src/main.py"},
                "tool_use_id": "tool_123"
            }
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        tool_event = next((e for e in events if e["event_type"] == "TOOL_CALL"), None)
        assert tool_event is not None
        assert tool_event["payload"]["tool_name"] == "readFile"

    def test_emit_tool_result(self):
        """Test emitting a TOOL_RESULT event."""
        event_id = emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "tool_123",
                "result": "def main(): pass"
            }
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        result_event = next((e for e in events if e["event_type"] == "TOOL_RESULT"), None)
        assert result_event is not None
        assert "def main" in result_event["payload"]["result"]

    def test_emit_session_end(self):
        """Test emitting a SESSION_END event."""
        event_id = emit_event(
            "SESSION_END",
            {
                "session_id": "test_session",
                "message_count": 10,
                "duration_seconds": 300
            }
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        end_event = next((e for e in events if e["event_type"] == "SESSION_END"), None)
        assert end_event is not None
        assert end_event["payload"]["session_id"] == "test_session"

    def test_listener_callback(self):
        """Test that listeners are called when events are emitted."""
        called = []
        
        def listener(event_type, payload):
            called.append((event_type, payload))
        
        register_listener("TEST_EVENT", listener)
        
        emit_event("TEST_EVENT", {"content": "test"})
        
        assert len(called) == 1
        assert called[0][0] == "TEST_EVENT"
        assert called[0][1]["content"] == "test"

    def test_fidelity_verification(self):
        """Test that emitted events pass fidelity verification."""
        emit_event("USER_INPUT", {"content": "Test message"}, actor="user")
        emit_event("ASSISTANT_OUTPUT", {"content": "Test response"}, actor="assistant")
        emit_event("TOOL_CALL", {"tool_name": "test", "tool_input": {}})
        
        result = verify_all_events()
        
        assert result["integrity"] == "PASS"
        assert result["failed"] == 0
        assert result["total"] >= 3

    def test_multiple_events_sequence(self):
        """Test emitting a sequence of events."""
        emit_event("USER_INPUT", {"content": "Help me debug"}, actor="user")
        emit_event("ASSISTANT_OUTPUT", {"content": "I'll help"}, actor="assistant")
        emit_event("TOOL_CALL", {"tool_name": "readFile", "tool_input": {"path": "test.py"}, "tool_use_id": "t1"})
        emit_event("TOOL_RESULT", {"tool_name": "readFile", "tool_use_id": "t1", "result": "code here"})
        emit_event("ASSISTANT_OUTPUT", {"content": "I found the issue"}, actor="assistant")
        
        events = get_events(limit=100)
        
        # Should have at least 5 events
        assert len(events) >= 5
        
        # Verify sequence
        event_types = [e["event_type"] for e in events[-5:]]
        assert "USER_INPUT" in event_types
        assert "ASSISTANT_OUTPUT" in event_types
        assert "TOOL_CALL" in event_types
        assert "TOOL_RESULT" in event_types
