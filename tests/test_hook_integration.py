"""Integration tests for IDE hook event capture."""

import pytest
from divineos.ledger import init_db, get_events, count_events
from divineos.consolidation import init_knowledge_table
from divineos.event_dispatcher import emit_event


@pytest.fixture(autouse=True)
def setup_integration_tests(tmp_path, monkeypatch):
    """Setup test environment with isolated ledger."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    init_knowledge_table()
    yield
    if test_db.exists():
        test_db.unlink()


class TestUserInputCapture:
    """Test user input capture via promptSubmit hook."""

    def test_user_input_event_emitted(self):
        """Test that USER_INPUT event is emitted and stored."""
        # Simulate user submitting a message
        user_message = "How should I structure this module?"
        
        event_id = emit_event(
            "USER_INPUT",
            {"content": user_message},
            actor="user"
        )
        
        assert event_id is not None
        
        # Verify event appears in ledger
        events = get_events(limit=10)
        assert len(events) > 0
        
        user_event = next((e for e in events if e["event_type"] == "USER_INPUT"), None)
        assert user_event is not None
        assert user_event["payload"]["content"] == user_message

    def test_multiple_user_inputs_captured(self):
        """Test that multiple user inputs are captured."""
        messages = [
            "First question",
            "Second question",
            "Third question"
        ]
        
        for msg in messages:
            emit_event("USER_INPUT", {"content": msg}, actor="user", validate=False)
        
        events = get_events(limit=100)
        user_events = [e for e in events if e["event_type"] == "USER_INPUT"]
        
        assert len(user_events) == 3
        for i, event in enumerate(user_events):
            assert event["payload"]["content"] == messages[i]

    def test_user_input_has_timestamp(self):
        """Test that USER_INPUT events have timestamps."""
        emit_event("USER_INPUT", {"content": "test"}, actor="user", validate=False)
        
        events = get_events(limit=10)
        user_event = next((e for e in events if e["event_type"] == "USER_INPUT"), None)
        
        assert user_event is not None
        assert "timestamp" in user_event
        assert user_event["timestamp"] is not None

    def test_user_input_has_content_hash(self):
        """Test that USER_INPUT events have content hashes."""
        emit_event("USER_INPUT", {"content": "test message"}, actor="user", validate=False)
        
        events = get_events(limit=10)
        user_event = next((e for e in events if e["event_type"] == "USER_INPUT"), None)
        
        assert user_event is not None
        assert "content_hash" in user_event
        assert user_event["content_hash"] is not None
        assert len(user_event["content_hash"]) > 0


class TestToolCallCapture:
    """Test tool call capture via postToolUse hook."""

    def test_tool_call_event_emitted(self):
        """Test that TOOL_CALL event is emitted and stored."""
        tool_name = "readFile"
        tool_input = {"path": "src/main.py"}
        
        event_id = emit_event(
            "TOOL_CALL",
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_use_id": "tool_001"
            },
            actor="assistant"
        )
        
        assert event_id is not None
        
        # Verify event appears in ledger
        events = get_events(limit=10)
        assert len(events) > 0
        
        tool_event = next((e for e in events if e["event_type"] == "TOOL_CALL"), None)
        assert tool_event is not None
        assert tool_event["payload"]["tool_name"] == tool_name
        assert tool_event["payload"]["tool_input"] == tool_input

    def test_tool_result_event_emitted(self):
        """Test that TOOL_RESULT event is emitted and stored."""
        tool_name = "readFile"
        result = "def main():\n    pass"
        
        event_id = emit_event(
            "TOOL_RESULT",
            {
                "tool_name": tool_name,
                "tool_use_id": "tool_001",
                "result": result,
                "duration_ms": 45
            },
            actor="system"
        )
        
        assert event_id is not None
        
        # Verify event appears in ledger
        events = get_events(limit=10)
        assert len(events) > 0
        
        result_event = next((e for e in events if e["event_type"] == "TOOL_RESULT"), None)
        assert result_event is not None
        assert result_event["payload"]["tool_name"] == tool_name
        assert result_event["payload"]["result"] == result
        assert result_event["payload"]["duration_ms"] == 45

    def test_tool_call_and_result_sequence(self):
        """Test that tool call and result are captured in sequence."""
        # Emit tool call
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "file.py"},
                "tool_use_id": "t1"
            },
            actor="assistant"
        )
        
        # Emit tool result
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "t1",
                "result": "content",
                "duration_ms": 50
            },
            actor="system"
        )
        
        events = get_events(limit=100)
        tool_events = [e for e in events if e["event_type"] in ("TOOL_CALL", "TOOL_RESULT")]
        
        assert len(tool_events) == 2
        assert tool_events[0]["event_type"] == "TOOL_CALL"
        assert tool_events[1]["event_type"] == "TOOL_RESULT"

    def test_multiple_tool_calls_captured(self):
        """Test that multiple tool calls are captured."""
        tools = ["readFile", "strReplace", "readFile"]
        
        for i, tool in enumerate(tools):
            emit_event(
                "TOOL_CALL",
                {
                    "tool_name": tool,
                    "tool_input": {"path": f"file{i}.py"},
                    "tool_use_id": f"t{i}"
                },
                actor="assistant"
            )
        
        events = get_events(limit=100)
        tool_events = [e for e in events if e["event_type"] == "TOOL_CALL"]
        
        assert len(tool_events) == 3
        for i, event in enumerate(tool_events):
            assert event["payload"]["tool_name"] == tools[i]


class TestSessionEndCapture:
    """Test session end capture via agentStop hook."""

    def test_session_end_event_emitted(self):
        """Test that SESSION_END event is emitted and stored."""
        session_id = "test_session_001"
        message_count = 5
        duration_seconds = 120.5
        
        event_id = emit_event(
            "SESSION_END",
            {
                "session_id": session_id,
                "message_count": message_count,
                "duration_seconds": duration_seconds
            },
            actor="system"
        )
        
        assert event_id is not None
        
        # Verify event appears in ledger
        events = get_events(limit=10)
        assert len(events) > 0
        
        session_event = next((e for e in events if e["event_type"] == "SESSION_END"), None)
        assert session_event is not None
        assert session_event["payload"]["session_id"] == session_id
        assert session_event["payload"]["message_count"] == message_count
        assert session_event["payload"]["duration_seconds"] == duration_seconds

    def test_session_end_has_timestamp(self):
        """Test that SESSION_END events have timestamps."""
        emit_event(
            "SESSION_END",
            {
                "session_id": "test",
                "message_count": 0,
                "duration_seconds": 0
            },
            actor="system"
        )
        
        events = get_events(limit=10)
        session_event = next((e for e in events if e["event_type"] == "SESSION_END"), None)
        
        assert session_event is not None
        assert "timestamp" in session_event
        assert session_event["timestamp"] is not None


class TestAutoAnalysisCapture:
    """Test auto-analysis event capture."""

    def test_quality_report_event_emitted(self):
        """Test that QUALITY_REPORT event is emitted."""
        event_id = emit_event(
            "QUALITY_REPORT",
            {
                "session_id": "test_session",
                "check_count": 7,
                "evidence_hash": "abc123"
            },
            actor="system"
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        report_event = next((e for e in events if e["event_type"] == "QUALITY_REPORT"), None)
        
        assert report_event is not None
        assert report_event["payload"]["session_id"] == "test_session"
        assert report_event["payload"]["check_count"] == 7

    def test_session_features_event_emitted(self):
        """Test that SESSION_FEATURES event is emitted."""
        event_id = emit_event(
            "SESSION_FEATURES",
            {
                "session_id": "test_session",
                "evidence_hash": "def456"
            },
            actor="system"
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        features_event = next((e for e in events if e["event_type"] == "SESSION_FEATURES"), None)
        
        assert features_event is not None
        assert features_event["payload"]["session_id"] == "test_session"

    def test_session_analysis_event_emitted(self):
        """Test that SESSION_ANALYSIS event is emitted."""
        report_text = "Session analysis report..."
        
        event_id = emit_event(
            "SESSION_ANALYSIS",
            {
                "session_id": "test_session",
                "report_text": report_text
            },
            actor="system"
        )
        
        assert event_id is not None
        
        events = get_events(limit=10)
        analysis_event = next((e for e in events if e["event_type"] == "SESSION_ANALYSIS"), None)
        
        assert analysis_event is not None
        assert analysis_event["payload"]["session_id"] == "test_session"
        assert analysis_event["payload"]["report_text"] == report_text


class TestCompleteEventSequence:
    """Test complete event capture sequence for a realistic session."""

    def test_complete_session_flow(self):
        """Test complete flow: user input → tool call → tool result → AI response → session end."""
        # 1. User submits message
        emit_event(
            "USER_INPUT",
            {"content": "Add authentication to the app"},
            actor="user"
        )
        
        # 2. AI responds
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I'll add authentication. Let me first check the current structure."},
            actor="assistant"
        )
        
        # 3. AI calls tool
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "src/app.py"},
                "tool_use_id": "t1"
            },
            actor="assistant"
        )
        
        # 4. Tool returns result
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "t1",
                "result": "class App:\n    def __init__(self):\n        pass",
                "duration_ms": 45
            },
            actor="system"
        )
        
        # 5. AI responds with plan
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "Now I'll add the authentication module."},
            actor="assistant"
        )
        
        # 6. AI calls tool to make changes
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "strReplace",
                "tool_input": {
                    "path": "src/app.py",
                    "oldStr": "class App:\n    def __init__(self):\n        pass",
                    "newStr": "class App:\n    def __init__(self):\n        self.users = {}\n    def login(self, username, password):\n        return username in self.users"
                },
                "tool_use_id": "t2"
            },
            actor="assistant"
        )
        
        # 7. Tool returns result
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "strReplace",
                "tool_use_id": "t2",
                "result": "File updated successfully",
                "duration_ms": 30
            },
            actor="system"
        )
        
        # 8. AI confirms completion
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "Authentication module added successfully."},
            actor="assistant"
        )
        
        # 9. Session ends
        emit_event(
            "SESSION_END",
            {
                "session_id": "auth_session",
                "message_count": 3,
                "duration_seconds": 45.5
            },
            actor="system"
        )
        
        # 10. Analysis runs
        emit_event(
            "QUALITY_REPORT",
            {
                "session_id": "auth_session",
                "check_count": 7,
                "evidence_hash": "xyz789"
            },
            actor="system"
        )
        
        # Verify all events captured
        events = get_events(limit=100)
        
        assert len(events) == 10
        
        event_types = [e["event_type"] for e in events]
        assert event_types.count("USER_INPUT") == 1
        assert event_types.count("ASSISTANT_OUTPUT") == 3
        assert event_types.count("TOOL_CALL") == 2
        assert event_types.count("TOOL_RESULT") == 2
        assert event_types.count("SESSION_END") == 1
        assert event_types.count("QUALITY_REPORT") == 1

    def test_event_count_accuracy(self):
        """Test that event count is accurate."""
        # Emit 5 events
        for i in range(5):
            emit_event(
                "USER_INPUT",
                {"content": f"Message {i}"},
                actor="user"
            )
        
        # Verify count
        stats = count_events()
        assert stats["total"] == 5
        assert stats["by_type"]["USER_INPUT"] == 5

    def test_events_retrievable_in_order(self):
        """Test that events are retrievable in order."""
        messages = ["First", "Second", "Third"]
        
        for msg in messages:
            emit_event("USER_INPUT", {"content": msg}, actor="user", validate=False)
        
        events = get_events(limit=100)
        user_events = [e for e in events if e["event_type"] == "USER_INPUT"]
        
        # Events should be in order (oldest first in the list)
        assert len(user_events) == 3
        assert user_events[0]["payload"]["content"] == "First"
        assert user_events[1]["payload"]["content"] == "Second"
        assert user_events[2]["payload"]["content"] == "Third"


class TestEventNonBlocking:
    """Test that event capture is non-blocking."""

    def test_rapid_event_emission(self):
        """Test that rapid event emission works without blocking."""
        # Emit 50 events rapidly
        for i in range(50):
            emit_event(
                "USER_INPUT",
                {"content": f"Message {i}"},
                actor="user",
                validate=False
            )
        
        # Verify all events captured
        events = get_events(limit=100)
        assert len(events) == 50

    def test_mixed_event_types_rapid(self):
        """Test rapid emission of mixed event types."""
        event_types = ["USER_INPUT", "ASSISTANT_OUTPUT", "TOOL_CALL", "TOOL_RESULT"]
        
        for i in range(25):
            event_type = event_types[i % len(event_types)]
            if event_type == "USER_INPUT":
                emit_event(event_type, {"content": f"msg {i}"}, actor="user", validate=False)
            elif event_type == "ASSISTANT_OUTPUT":
                emit_event(event_type, {"content": f"response {i}"}, actor="assistant", validate=False)
            elif event_type == "TOOL_CALL":
                emit_event(event_type, {"tool_name": "readFile", "tool_use_id": f"t{i}"}, actor="assistant", validate=False)
            else:
                emit_event(event_type, {"tool_name": "readFile", "tool_use_id": f"t{i}", "result": "ok"}, actor="system", validate=False)
        
        events = get_events(limit=100)
        assert len(events) == 25


class TestEventDataIntegrity:
    """Test that event data is stored with integrity."""

    def test_event_payload_preserved(self):
        """Test that event payload is preserved exactly."""
        payload = {
            "content": "Test message with special chars: !@#$%^&*()",
            "metadata": {"key": "value"},
            "nested": {"deep": {"data": 123}}
        }
        
        emit_event("USER_INPUT", payload, actor="user", validate=False)
        
        events = get_events(limit=10)
        event = next((e for e in events if e["event_type"] == "USER_INPUT"), None)
        
        assert event is not None
        assert event["payload"] == payload

    def test_event_actor_recorded(self):
        """Test that event actor is recorded correctly."""
        actors = ["user", "assistant", "system"]
        
        for actor in actors:
            emit_event("USER_INPUT", {"content": "test"}, actor=actor, validate=False)
        
        events = get_events(limit=100)
        
        for actor in actors:
            actor_events = [e for e in events if e["actor"] == actor]
            assert len(actor_events) > 0

    def test_event_timestamp_format(self):
        """Test that event timestamps are in ISO format or numeric."""
        emit_event("USER_INPUT", {"content": "test"}, actor="user", validate=False)
        
        events = get_events(limit=10)
        event = events[0]
        
        timestamp = event["timestamp"]
        # Timestamp should be a number (Unix timestamp)
        assert isinstance(timestamp, (int, float))
        assert timestamp > 0
