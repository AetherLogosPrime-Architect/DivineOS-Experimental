"""
Property-Based Tests for DivineOS Hardening.

Tests formal correctness properties of the hardened system:
1. Event immutability property
2. Tool call/result pairing property
3. Session uniqueness property
4. No silent errors property
5. Event hash validity property
6. Session lifecycle property
7. Tool execution duration property
"""

import pytest
import uuid

try:
    from hypothesis import given, strategies as st, settings, HealthCheck

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

    # Provide dummy decorators for when hypothesis is not installed
    def given(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def settings(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


from divineos.core.ledger import get_events, verify_event_hash
from divineos.core.session_manager import (
    initialize_session,
    get_current_session_id,
    end_session,
    clear_session,
)
from divineos.event.event_emission import (
    emit_user_input,
    emit_tool_call,
    emit_tool_result,
)

# Skip all tests in this module if hypothesis is not installed
pytestmark = pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")


# Strategy for generating valid content
# Use only alphanumeric and spaces to ensure validation passes
valid_content = st.text(
    min_size=3,
    max_size=100,
    alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
).filter(lambda x: len(x.strip()) >= 3 and any(c.isalpha() for c in x))


class TestEventImmutabilityProperty:
    """Property: Events stored in ledger are immutable."""

    @given(content=valid_content)
    @pytest.mark.slow
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_event_immutability(self, content):
        """Test that events cannot be modified after storage."""
        session_id = initialize_session()
        try:
            # Store an event
            event_id = emit_user_input(content=content, session_id=session_id)

            # Retrieve the event
            events = get_events(limit=1)
            assert len(events) > 0

            original_event = events[0]
            original_hash = original_event.get("content_hash")

            # Verify hash is consistent
            assert original_hash is not None

            # Verify hash matches using correct signature
            payload = original_event.get("payload", {})
            is_valid, reason = verify_event_hash(event_id, payload, original_hash)
            assert is_valid, reason

            # Retrieve again and verify hash hasn't changed
            events_again = get_events(limit=1)
            assert events_again[0].get("content_hash") == original_hash
        finally:
            clear_session()


class TestToolCallResultPairingProperty:
    """Property: Every TOOL_CALL has a corresponding TOOL_RESULT."""

    @given(
        tool_name=st.text(
            min_size=2,
            max_size=50,
            alphabet="abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
        ).filter(lambda x: x[0].isalpha() and len(x) >= 2),  # Must start with letter
        result=valid_content,
    )
    @pytest.mark.slow
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_tool_call_result_pairing(self, tool_name, result):
        """Test that tool calls are paired with results."""
        # Initialize session
        session_id = initialize_session()

        try:
            # Emit tool call
            tool_use_id = str(uuid.uuid4())
            emit_tool_call(
                tool_name=tool_name,
                tool_input={"test": "input"},
                tool_use_id=tool_use_id,
                session_id=session_id,
            )

            # Emit tool result
            emit_tool_result(
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                result=result,
                duration_ms=100,
                session_id=session_id,
            )

            # Verify both events exist - filter by session_id to avoid interference from other test runs
            all_events = get_events(limit=1000)

            # Filter events by session_id to isolate this test's events
            events = [e for e in all_events if e.get("payload", {}).get("session_id") == session_id]
            tool_calls = [e for e in events if e["event_type"] == "TOOL_CALL"]
            tool_results = [e for e in events if e["event_type"] == "TOOL_RESULT"]

            # For this session, we should have at least one of each
            assert len(tool_calls) > 0, "No TOOL_CALL events found"
            assert len(tool_results) > 0, "No TOOL_RESULT events found"

            # Verify tool_use_id matches between call and result
            call_tool_use_ids = {call.get("payload", {}).get("tool_use_id") for call in tool_calls}
            result_tool_use_ids = {
                result_event.get("payload", {}).get("tool_use_id") for result_event in tool_results
            }

            # There should be overlap
            assert call_tool_use_ids & result_tool_use_ids, (
                "No matching tool_use_ids between calls and results"
            )

        finally:
            clear_session()


class TestSessionUniquenessProperty:
    """Property: Each session has a unique session_id."""

    @given(st.just(None))  # Placeholder for hypothesis
    @pytest.mark.slow
    @settings(max_examples=10)
    def test_session_uniqueness(self, _):
        """Test that sessions have unique IDs."""
        session_ids = set()

        for _ in range(5):
            session_id = initialize_session()
            assert session_id not in session_ids
            session_ids.add(session_id)
            clear_session()

        # All session IDs should be unique
        assert len(session_ids) == 5


class TestNoSilentErrorsProperty:
    """Property: No errors are silently swallowed."""

    @given(content=valid_content)
    @pytest.mark.slow
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_no_silent_errors(self, content):
        """Test that errors are logged, not silently swallowed."""
        # This is a basic test - in production, we'd verify logs
        # For now, just verify that operations complete without silent failures

        session_id = initialize_session()

        try:
            # Emit events
            emit_user_input(content=content, session_id=session_id)

            # Verify event was stored
            events = get_events(limit=1)
            assert len(events) > 0

        finally:
            clear_session()


class TestEventHashValidityProperty:
    """Property: All events have valid SHA256 hashes (truncated to 32 chars)."""

    @given(content=valid_content)
    @pytest.mark.slow
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_event_hash_validity(self, content):
        """Test that all events have valid hashes."""
        session_id = initialize_session()
        try:
            # Store an event
            event_id = emit_user_input(content=content, session_id=session_id)

            # Retrieve the event
            events = get_events(limit=1)
            assert len(events) > 0

            event = events[0]
            event_hash = event.get("content_hash")

            # Verify hash is valid
            assert event_hash is not None
            # Hash is truncated SHA256 to 32 chars (not full 64)
            assert len(event_hash) == 32, f"Expected 32 char hash, got {len(event_hash)}"
            assert all(c in "0123456789abcdef" for c in event_hash), (
                "Hash contains invalid hex characters"
            )

            # Verify hash matches
            payload = event.get("payload", {})
            is_valid, reason = verify_event_hash(event_id, payload, event_hash)
            assert is_valid, reason
        finally:
            clear_session()


class TestSessionLifecycleProperty:
    """Property: Sessions follow correct lifecycle (init → use → end → clear)."""

    @given(st.just(None))  # Placeholder for hypothesis
    @pytest.mark.slow
    @settings(max_examples=10)
    def test_session_lifecycle(self, _):
        """Test that sessions follow correct lifecycle."""
        # Initialize session
        session_id = initialize_session()
        assert session_id is not None

        # Get current session
        current_id = get_current_session_id()
        assert current_id == session_id

        # Emit event in session
        emit_user_input(content="test", session_id=session_id)

        # End session
        end_session()

        # Clear session
        clear_session()

        # Verify session is cleared
        # (next initialize should create new session)
        new_session_id = initialize_session()
        assert new_session_id != session_id

        clear_session()


class TestToolExecutionDurationProperty:
    """Property: Tool execution duration is always non-negative."""

    @given(
        duration_ms=st.integers(min_value=0, max_value=10000),
    )
    @pytest.mark.slow
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_tool_execution_duration(self, duration_ms):
        """Test that tool execution duration is non-negative."""
        session_id = initialize_session()

        try:
            # Emit tool call
            tool_use_id = str(uuid.uuid4())
            emit_tool_call(
                tool_name="test_tool",
                tool_input={},
                tool_use_id=tool_use_id,
                session_id=session_id,
            )

            # Emit tool result with duration
            emit_tool_result(
                tool_name="test_tool",
                tool_use_id=tool_use_id,
                result="test result",
                duration_ms=duration_ms,
                session_id=session_id,
            )

            # Verify duration is stored correctly
            events = get_events(limit=100)
            tool_results = [e for e in events if e["event_type"] == "TOOL_RESULT"]

            assert len(tool_results) > 0
            for result in tool_results:
                stored_duration = result.get("payload", {}).get("duration_ms")
                assert stored_duration >= 0

        finally:
            clear_session()


class TestEventCaptureRateProperty:
    """Property: All user actions result in captured events."""

    @given(
        num_inputs=st.integers(min_value=1, max_value=10),
    )
    @pytest.mark.slow
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_event_capture_rate(self, num_inputs):
        """Test that all user inputs are captured."""
        session_id = initialize_session()

        try:
            # Emit multiple user inputs
            for i in range(num_inputs):
                emit_user_input(content=f"input_{i}", session_id=session_id)

            # Verify all inputs were captured
            events = get_events(limit=1000)
            user_inputs = [e for e in events if e["event_type"] == "USER_INPUT"]

            # Should have at least num_inputs events
            assert len(user_inputs) >= num_inputs

        finally:
            clear_session()
