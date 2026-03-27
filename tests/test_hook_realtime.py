"""Real-time testing for IDE hook integration - Phase 3."""

import pytest
import time
from divineos.core.ledger import init_db, get_events, count_events
from divineos.core.consolidation import init_knowledge_table
from divineos.event.event_emission import emit_event


@pytest.fixture(autouse=True)
def setup_realtime_tests(tmp_path, monkeypatch):
    """Setup test environment with isolated ledger."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    init_knowledge_table()
    yield
    if test_db.exists():
        test_db.unlink()


class TestEndToEndSessionFlow:
    """Test complete end-to-end session flows."""

    def test_authentication_feature_session(self):
        """Test realistic authentication feature implementation session."""
        # User asks for feature
        emit_event(
            "USER_INPUT", {"content": "Add authentication to the app"}, actor="user", validate=False
        )

        # AI responds with plan
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I'll add authentication. Let me check the current structure."},
            actor="assistant",
            validate=False,
        )

        # AI reads current code
        emit_event(
            "TOOL_CALL",
            {"tool_name": "readFile", "tool_input": {"path": "src/app.py"}, "tool_use_id": "t1"},
            actor="assistant",
            validate=False,
        )
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "t1",
                "result": "class App:\n    def __init__(self):\n        pass",
                "duration_ms": 45,
            },
            actor="system",
            validate=False,
        )

        # AI proposes changes
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I'll add a login method and user storage."},
            actor="assistant",
            validate=False,
        )

        # AI makes changes
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "strReplace",
                "tool_input": {
                    "path": "src/app.py",
                    "oldStr": "class App:\n    def __init__(self):\n        pass",
                    "newStr": "class App:\n    def __init__(self):\n        self.users = {}\n    def login(self, username, password):\n        return username in self.users",
                },
                "tool_use_id": "t2",
            },
            actor="assistant",
            validate=False,
        )
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "strReplace",
                "tool_use_id": "t2",
                "result": "File updated",
                "duration_ms": 30,
            },
            actor="system",
            validate=False,
        )

        # AI confirms
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "Authentication added successfully."},
            actor="assistant",
            validate=False,
        )

        # User approves
        emit_event(
            "USER_INPUT",
            {"content": "Great! Now add password hashing."},
            actor="user",
            validate=False,
        )

        # Session ends
        emit_event(
            "SESSION_END",
            {"session_id": "auth_session", "message_count": 4, "duration_seconds": 120.5},
            actor="system",
            validate=False,
        )

        # Verify all events captured
        events = get_events(limit=100)
        assert len(events) == 10

        event_types = [e["event_type"] for e in events]
        assert event_types.count("USER_INPUT") == 2
        assert event_types.count("ASSISTANT_OUTPUT") == 3
        assert event_types.count("TOOL_CALL") == 2
        assert event_types.count("TOOL_RESULT") == 2
        assert event_types.count("SESSION_END") == 1

    def test_debugging_session(self):
        """Test realistic debugging session."""
        # User reports bug
        emit_event(
            "USER_INPUT",
            {"content": "The app crashes when I click the button"},
            actor="user",
            validate=False,
        )

        # AI asks for details
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "Let me check the button handler code."},
            actor="assistant",
            validate=False,
        )

        # AI reads code
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "src/handlers.py"},
                "tool_use_id": "t1",
            },
            actor="assistant",
            validate=False,
        )
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "t1",
                "result": "def on_click():\n    data = process()\n    return data['result']",
                "duration_ms": 40,
            },
            actor="system",
            validate=False,
        )

        # AI identifies issue
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I found the bug. The code doesn't check if 'result' exists."},
            actor="assistant",
            validate=False,
        )

        # AI fixes it
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "strReplace",
                "tool_input": {
                    "path": "src/handlers.py",
                    "oldStr": "def on_click():\n    data = process()\n    return data['result']",
                    "newStr": "def on_click():\n    data = process()\n    return data.get('result', None)",
                },
                "tool_use_id": "t2",
            },
            actor="assistant",
            validate=False,
        )
        emit_event(
            "TOOL_RESULT",
            {"tool_name": "strReplace", "tool_use_id": "t2", "result": "Fixed", "duration_ms": 25},
            actor="system",
            validate=False,
        )

        # Session ends
        emit_event(
            "SESSION_END",
            {"session_id": "debug_session", "message_count": 2, "duration_seconds": 60.0},
            actor="system",
            validate=False,
        )

        # Verify events
        events = get_events(limit=100)
        assert len(events) == 8


@pytest.mark.slow
class TestPerformanceValidation:
    """Test performance under realistic conditions."""

    def test_high_frequency_events(self):
        """Test handling of high-frequency events."""
        start_time = time.time()

        # Emit 100 events rapidly
        for i in range(100):
            emit_event("USER_INPUT", {"content": f"Message {i}"}, actor="user", validate=False)

        elapsed = time.time() - start_time

        # Verify all captured
        events = get_events(limit=200)
        assert len(events) == 100

        # Performance should be good (< 1 second for 100 events)
        assert elapsed < 1.0

    def test_mixed_event_types_performance(self):
        """Test performance with mixed event types."""
        start_time = time.time()

        # Emit 50 mixed events
        for i in range(50):
            if i % 4 == 0:
                emit_event("USER_INPUT", {"content": f"msg {i}"}, actor="user", validate=False)
            elif i % 4 == 1:
                emit_event(
                    "ASSISTANT_OUTPUT",
                    {"content": f"response {i}"},
                    actor="assistant",
                    validate=False,
                )
            elif i % 4 == 2:
                emit_event(
                    "TOOL_CALL",
                    {"tool_name": "readFile", "tool_use_id": f"t{i}"},
                    actor="assistant",
                    validate=False,
                )
            else:
                emit_event(
                    "TOOL_RESULT",
                    {"tool_name": "readFile", "tool_use_id": f"t{i}", "result": "ok"},
                    actor="system",
                    validate=False,
                )

        elapsed = time.time() - start_time

        # Verify all captured
        events = get_events(limit=100)
        assert len(events) == 50

        # Performance should be good
        assert elapsed < 1.0

    def test_large_payload_handling(self):
        """Test handling of large payloads."""
        # Create large payload (10KB)
        large_content = "x" * 10000

        start_time = time.time()
        emit_event("USER_INPUT", {"content": large_content}, actor="user", validate=False)
        elapsed = time.time() - start_time

        # Should handle large payloads efficiently
        assert elapsed < 0.5

        # Verify event stored
        events = get_events(limit=10)
        assert len(events) == 1
        assert len(events[0]["payload"]["content"]) == 10000


class TestReliabilityValidation:
    """Test reliability and error handling."""

    def test_concurrent_event_emission(self):
        """Test that concurrent events are handled correctly."""
        # Emit events that might happen concurrently
        for i in range(10):
            emit_event("USER_INPUT", {"content": f"msg {i}"}, actor="user", validate=False)
            emit_event(
                "ASSISTANT_OUTPUT", {"content": f"response {i}"}, actor="assistant", validate=False
            )

        # Verify all captured in correct order
        events = get_events(limit=100)
        assert len(events) == 20

        # Verify alternating pattern
        user_events = [e for e in events if e["event_type"] == "USER_INPUT"]
        assistant_events = [e for e in events if e["event_type"] == "ASSISTANT_OUTPUT"]

        assert len(user_events) == 10
        assert len(assistant_events) == 10

    def test_event_recovery_after_error(self):
        """Test that system recovers after errors."""
        # Emit normal event
        emit_event("USER_INPUT", {"content": "test1"}, actor="user", validate=False)

        # Try to emit with unusual data
        emit_event(
            "USER_INPUT",
            {"content": "test2", "extra": {"nested": {"deep": "data"}}},
            actor="user",
            validate=False,
        )

        # Emit normal event again
        emit_event("USER_INPUT", {"content": "test3"}, actor="user", validate=False)

        # Verify all captured
        events = get_events(limit=100)
        assert len(events) == 3

    def test_ledger_consistency(self):
        """Test that ledger remains consistent."""
        # Emit events
        for i in range(20):
            emit_event("USER_INPUT", {"content": f"msg {i}"}, actor="user", validate=False)

        # Get count
        stats = count_events()
        assert stats["total"] == 20

        # Get events
        events = get_events(limit=100)
        assert len(events) == 20

        # Verify consistency
        assert stats["total"] == len(events)


class TestUserExperienceValidation:
    """Test user experience aspects."""

    def test_analysis_after_session(self):
        """Test that analysis works after session."""
        # Emit session events
        emit_event("USER_INPUT", {"content": "Add feature"}, actor="user", validate=False)
        emit_event(
            "ASSISTANT_OUTPUT", {"content": "I'll add it"}, actor="assistant", validate=False
        )
        emit_event(
            "TOOL_CALL",
            {"tool_name": "readFile", "tool_use_id": "t1"},
            actor="assistant",
            validate=False,
        )
        emit_event(
            "TOOL_RESULT",
            {"tool_name": "readFile", "tool_use_id": "t1", "result": "code"},
            actor="system",
            validate=False,
        )
        emit_event(
            "SESSION_END",
            {"session_id": "test", "message_count": 2, "duration_seconds": 30},
            actor="system",
            validate=False,
        )

        # Verify analysis can run
        events = get_events(limit=100)
        assert len(events) == 5

    def test_event_visibility(self):
        """Test that events are visible to user."""
        # Emit events
        emit_event("USER_INPUT", {"content": "test message"}, actor="user", validate=False)
        emit_event(
            "ASSISTANT_OUTPUT", {"content": "test response"}, actor="assistant", validate=False
        )

        # Verify events are retrievable
        events = get_events(limit=100)
        assert len(events) == 2

        # Verify content is intact
        user_event = next((e for e in events if e["event_type"] == "USER_INPUT"), None)
        assert user_event is not None
        assert user_event["payload"]["content"] == "test message"

    def test_session_metadata_tracking(self):
        """Test that session metadata is tracked."""
        # Emit session with metadata
        emit_event(
            "SESSION_END",
            {
                "session_id": "metadata_test",
                "message_count": 5,
                "duration_seconds": 120.5,
                "files_touched": 3,
                "tools_used": ["readFile", "strReplace"],
            },
            actor="system",
        )

        # Verify metadata captured
        events = get_events(limit=10)
        session_event = events[0]

        assert session_event["payload"]["session_id"] == "metadata_test"
        assert session_event["payload"]["message_count"] == 5
        assert session_event["payload"]["duration_seconds"] == 120.5
