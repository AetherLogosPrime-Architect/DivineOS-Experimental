"""Real-time testing for IDE hook integration - Phase 3."""

import os
import sqlite3
import time

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import count_events, get_events, init_db
from divineos.event.event_emission import emit_event

# WHY THESE BUDGETS ARE MEASURED RATHER THAN WRITTEN DOWN.
#
# These assertions used a fixed wall-clock budget scaled by a hand-set
# multiplier. That multiplier was raised from 2 to 4 on 2026-07-16 after a
# flake, and on 2026-09-21 the mixed-event test flaked again at 6.039s against
# the 4.0s budget -- during a full-suite run, on a busy machine, with nothing
# about the code changed. It blocked a push that had nothing to do with it.
#
# A wall-clock budget cannot tell "this code got slower" from "this machine was
# busy". Those are two states sharing one output, which is the fault class this
# repository keeps finding in its own instruments. Raising the multiplier again
# treats the symptom and guarantees a third flake.
#
# So the budget is CALIBRATED in the same process, against the same disk, at the
# moment the test runs: time a plain sqlite insert loop, then require our
# emission layer to stay within a multiple of that. A uniformly slower machine
# moves both numbers and the ratio holds. A genuine regression in our own code
# moves only ours, and still fails.
#
# DIVINEOS_PERF_MULTIPLIER still applies on top, so the old tightening knob
# keeps working for anyone who wants it.
_PERF_MULT = float(os.environ.get("DIVINEOS_PERF_MULTIPLIER", "4"))

# How much more expensive one emit_event may be than one bare sqlite insert.
# Emission validates, serialises a payload and hash-chains the row, so it is
# legitimately heavier; this bounds how much heavier.
_EMIT_OVERHEAD_RATIO = 60.0


def _seconds_per_bare_insert(db_path: str, samples: int = 50, payload_bytes: int = 64) -> float:
    """Time one plain sqlite insert on this machine, right now.

    Returned as seconds per insert. Never returns zero: a clock too coarse to
    see the loop reports the clock's own resolution instead, so a caller can
    always divide by it.

    PAYLOAD SIZE IS A PARAMETER, and leaving it out was a real failure.
    Calibrating on a 64-byte row and then applying that budget to a test that
    writes ten-kilobyte rows measures one population and judges another: the
    large-payload test overran its budget by under one percent and reported a
    regression, when what it had found was that a big row costs more to write
    than a small one. Calibrate against rows the size of the rows under test,
    and the ratio is then about our own overhead rather than about bytes.
    """
    conn = sqlite3.connect(db_path)
    filler = "x" * payload_bytes
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS _perf_calibration (n INTEGER, s TEXT)")
        conn.commit()
        start = time.perf_counter()
        for i in range(samples):
            conn.execute("INSERT INTO _perf_calibration (n, s) VALUES (?, ?)", (i, filler))
            conn.commit()
        elapsed = time.perf_counter() - start
        conn.execute("DROP TABLE _perf_calibration")
        conn.commit()
    finally:
        conn.close()
    per = elapsed / samples
    return max(per, time.get_clock_info("perf_counter").resolution)


def _emit_budget(db_path: str, event_count: int, payload_bytes: int = 64) -> float:
    """Wall-clock seconds this machine may take to emit `event_count` events.

    ``payload_bytes`` must match the size of the payloads the caller emits, or
    the budget is calibrated against a different population than it judges.
    """
    per_insert = _seconds_per_bare_insert(db_path, payload_bytes=payload_bytes)
    return per_insert * event_count * _EMIT_OVERHEAD_RATIO * _PERF_MULT


@pytest.fixture(autouse=True)
def setup_realtime_tests(tmp_path, monkeypatch):
    """Setup test environment with isolated ledger.

    Yields the ledger path so timing tests can calibrate their budget against
    the same file on the same disk.
    """
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    init_knowledge_table()
    yield str(test_db)
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

    def test_high_frequency_events(self, setup_realtime_tests):
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
        budget = _emit_budget(setup_realtime_tests, 100)
        assert elapsed < budget, (
            f"Bulk emit took {elapsed:.3f}s, budget {budget:.3f}s "
            f"(calibrated against bare sqlite inserts on this machine)"
        )

    def test_mixed_event_types_performance(self, setup_realtime_tests):
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
        budget = _emit_budget(setup_realtime_tests, 50)
        assert elapsed < budget, (
            f"Mixed events took {elapsed:.3f}s, budget {budget:.3f}s "
            f"(calibrated against bare sqlite inserts on this machine)"
        )

    def test_large_payload_handling(self, setup_realtime_tests):
        """Test handling of large payloads.

        MEASURED OVER SEVERAL EMISSIONS, not one. This test timed a single
        call and flaked on 2026-09-21 even after the budget was calibrated,
        because one sample of anything is not a measurement -- the first call
        also pays whatever warm-up the run happens to owe, and a busy disk
        moves a single reading far more than it moves an average. The rule
        that says prove the instrument applies to the sample size too.
        """
        # Create large payload (10KB)
        large_content = "x" * 10000
        samples = 10

        start_time = time.time()
        for i in range(samples):
            emit_event(
                "USER_INPUT", {"content": f"{i}{large_content}"}, actor="user", validate=False
            )
        elapsed = time.time() - start_time

        # Should handle large payloads efficiently
        budget = _emit_budget(setup_realtime_tests, samples, payload_bytes=len(large_content))
        assert elapsed < budget, (
            f"Large payload took {elapsed:.3f}s, budget {budget:.3f}s "
            f"(calibrated against bare sqlite inserts of the same size)"
        )

        # Verify events stored, and that each one kept its whole payload --
        # a fast write that truncated the content would otherwise pass.
        events = get_events(limit=samples + 5)
        assert len(events) == samples
        for event in events:
            assert len(event["payload"]["content"]) == 10001


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
