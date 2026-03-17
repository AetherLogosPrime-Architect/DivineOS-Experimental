"""Tests for asynchronous event capture module."""

import pytest
import asyncio
import os
import tempfile
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from hypothesis import given, strategies as st, settings

from divineos.async_capture import (
    emit_user_input_async,
    emit_tool_call_async,
    emit_tool_result_async,
    emit_session_end_async,
    EventQueue,
    get_event_queue,
    flush_event_queue,
    _retry_with_backoff,
)
from divineos.event_capture import get_session_tracker
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
    tracker = get_session_tracker()
    tracker.start_session()
    yield tracker
    tracker.end_session()


@pytest.fixture
def event_queue():
    """Get a fresh event queue."""
    queue = get_event_queue()
    queue.clear()
    yield queue
    queue.clear()


class TestEventQueue:
    """Tests for EventQueue class."""

    def test_queue_initialization(self):
        """Test EventQueue initialization."""
        queue = EventQueue(max_retries=3, initial_backoff_ms=100)
        assert queue.size() == 0
        assert queue.max_retries == 3
        assert queue.initial_backoff_ms == 100

    def test_enqueue_and_dequeue(self, event_queue):
        """Test enqueuing and dequeuing events."""
        event_data = {"type": "USER_INPUT", "content": "test"}
        event_queue.enqueue(event_data)
        
        assert event_queue.size() == 1
        
        dequeued = event_queue.dequeue()
        assert dequeued == event_data
        assert event_queue.size() == 0

    def test_dequeue_empty_queue(self, event_queue):
        """Test dequeuing from empty queue."""
        result = event_queue.dequeue()
        assert result is None

    def test_queue_fifo_order(self, event_queue):
        """Test that queue maintains FIFO order."""
        events = [
            {"type": "USER_INPUT", "id": 1},
            {"type": "TOOL_CALL", "id": 2},
            {"type": "TOOL_RESULT", "id": 3},
        ]
        
        for event in events:
            event_queue.enqueue(event)
        
        for expected_event in events:
            dequeued = event_queue.dequeue()
            assert dequeued == expected_event

    def test_queue_clear(self, event_queue):
        """Test clearing the queue."""
        event_queue.enqueue({"type": "USER_INPUT"})
        event_queue.enqueue({"type": "TOOL_CALL"})
        
        assert event_queue.size() == 2
        event_queue.clear()
        assert event_queue.size() == 0

    def test_queue_thread_safety(self, event_queue):
        """Test that queue is thread-safe."""
        import threading
        
        def enqueue_events():
            for i in range(10):
                event_queue.enqueue({"id": i})
        
        threads = [threading.Thread(target=enqueue_events) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert event_queue.size() == 30


class TestAsyncEmitUserInput:
    """Tests for emit_user_input_async function."""

    @pytest.mark.asyncio
    async def test_emit_user_input_async_basic(self, temp_db, fresh_session):
        """Test basic async USER_INPUT event emission."""
        event_id = await emit_user_input_async("Hello, world!")
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        # Verify event was stored in ledger
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["payload"]["content"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_emit_user_input_async_with_session_id(self, temp_db):
        """Test async USER_INPUT event with explicit session ID."""
        session_id = "test-session-123"
        event_id = await emit_user_input_async("Test message", session_id=session_id)
        
        assert event_id is not None
        events = get_events(limit=10, event_type="USER_INPUT")
        assert len(events) == 1
        assert events[0]["payload"]["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_emit_user_input_async_returns_quickly(self, temp_db, fresh_session):
        """Test that emit_user_input_async returns within 100ms."""
        start_time = time.time()
        event_id = await emit_user_input_async("Test message")
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert event_id is not None
        assert elapsed_ms < 100, f"Emission took {elapsed_ms}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_emit_user_input_async_error_handling(self, temp_db, fresh_session):
        """Test that errors are handled gracefully."""
        with patch('divineos.async_capture.sync_emit_user_input', side_effect=Exception("Test error")):
            # Should not raise, should return None
            event_id = await emit_user_input_async("Test message")
            assert event_id is None

    @pytest.mark.asyncio
    async def test_emit_user_input_async_queues_on_failure(self, temp_db, fresh_session, event_queue):
        """Test that events are queued when emission fails."""
        with patch('divineos.async_capture.sync_emit_user_input', side_effect=Exception("Test error")):
            event_id = await emit_user_input_async("Test message")
            
            assert event_id is None
            assert event_queue.size() == 1
            
            queued_event = event_queue.dequeue()
            assert queued_event["type"] == "USER_INPUT"
            assert queued_event["args"][0] == "Test message"


class TestAsyncEmitToolCall:
    """Tests for emit_tool_call_async function."""

    @pytest.mark.asyncio
    async def test_emit_tool_call_async_basic(self, temp_db, fresh_session):
        """Test basic async TOOL_CALL event emission."""
        tool_input = {"path": "test.py"}
        event_id = await emit_tool_call_async("readFile", tool_input)
        
        assert event_id is not None
        
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["payload"]["tool_name"] == "readFile"
        assert events[0]["payload"]["tool_input"] == tool_input

    @pytest.mark.asyncio
    async def test_emit_tool_call_async_with_tool_use_id(self, temp_db, fresh_session):
        """Test async TOOL_CALL event with explicit tool_use_id."""
        tool_use_id = "tool-123"
        event_id = await emit_tool_call_async(
            "readFile",
            {"path": "test.py"},
            tool_use_id=tool_use_id
        )
        
        assert event_id is not None
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) == 1
        assert events[0]["payload"]["tool_use_id"] == tool_use_id

    @pytest.mark.asyncio
    async def test_emit_tool_call_async_returns_quickly(self, temp_db, fresh_session):
        """Test that emit_tool_call_async returns within 100ms."""
        start_time = time.time()
        event_id = await emit_tool_call_async("readFile", {"path": "test.py"})
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert event_id is not None
        assert elapsed_ms < 100, f"Emission took {elapsed_ms}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_emit_tool_call_async_error_handling(self, temp_db, fresh_session):
        """Test that errors are handled gracefully."""
        with patch('divineos.async_capture.sync_emit_tool_call', side_effect=Exception("Test error")):
            event_id = await emit_tool_call_async("readFile", {"path": "test.py"})
            assert event_id is None

    @pytest.mark.asyncio
    async def test_emit_tool_call_async_queues_on_failure(self, temp_db, fresh_session, event_queue):
        """Test that events are queued when emission fails."""
        with patch('divineos.async_capture.sync_emit_tool_call', side_effect=Exception("Test error")):
            event_id = await emit_tool_call_async("readFile", {"path": "test.py"})
            
            assert event_id is None
            assert event_queue.size() == 1


class TestAsyncEmitToolResult:
    """Tests for emit_tool_result_async function."""

    @pytest.mark.asyncio
    async def test_emit_tool_result_async_basic(self, temp_db, fresh_session):
        """Test basic async TOOL_RESULT event emission."""
        event_id = await emit_tool_result_async(
            "readFile",
            "tool-123",
            "file content",
            45
        )
        
        assert event_id is not None
        
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["tool_name"] == "readFile"
        assert events[0]["payload"]["result"] == "file content"
        assert events[0]["payload"]["duration_ms"] == 45

    @pytest.mark.asyncio
    async def test_emit_tool_result_async_with_failure(self, temp_db, fresh_session):
        """Test async TOOL_RESULT event with failure flag."""
        event_id = await emit_tool_result_async(
            "readFile",
            "tool-123",
            "Error: File not found",
            100,
            failed=True,
            error_message="File not found"
        )
        
        assert event_id is not None
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) == 1
        assert events[0]["payload"]["failed"] is True
        assert events[0]["payload"]["error_message"] == "File not found"

    @pytest.mark.asyncio
    async def test_emit_tool_result_async_returns_quickly(self, temp_db, fresh_session):
        """Test that emit_tool_result_async returns within 100ms."""
        start_time = time.time()
        event_id = await emit_tool_result_async(
            "readFile",
            "tool-123",
            "result",
            45
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert event_id is not None
        assert elapsed_ms < 100, f"Emission took {elapsed_ms}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_emit_tool_result_async_error_handling(self, temp_db, fresh_session):
        """Test that errors are handled gracefully."""
        with patch('divineos.async_capture.sync_emit_tool_result', side_effect=Exception("Test error")):
            event_id = await emit_tool_result_async(
                "readFile",
                "tool-123",
                "result",
                45
            )
            assert event_id is None


class TestAsyncEmitSessionEnd:
    """Tests for emit_session_end_async function."""

    @pytest.mark.asyncio
    async def test_emit_session_end_async_basic(self, temp_db, fresh_session):
        """Test basic async SESSION_END event emission."""
        event_id = await emit_session_end_async()
        
        assert event_id is not None
        
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_emit_session_end_async_with_metadata(self, temp_db, fresh_session):
        """Test async SESSION_END event with metadata."""
        event_id = await emit_session_end_async(
            message_count=5,
            tool_call_count=3,
            tool_result_count=3,
            duration_seconds=120.5
        )
        
        assert event_id is not None
        events = get_events(limit=10, event_type="SESSION_END")
        assert len(events) == 1
        assert events[0]["payload"]["message_count"] == 5
        assert events[0]["payload"]["tool_call_count"] == 3
        assert events[0]["payload"]["tool_result_count"] == 3
        assert events[0]["payload"]["duration_seconds"] == 120.5

    @pytest.mark.asyncio
    async def test_emit_session_end_async_returns_quickly(self, temp_db, fresh_session):
        """Test that emit_session_end_async returns within 100ms."""
        start_time = time.time()
        event_id = await emit_session_end_async()
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert event_id is not None
        assert elapsed_ms < 100, f"Emission took {elapsed_ms}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_emit_session_end_async_error_handling(self, temp_db, fresh_session):
        """Test that errors are handled gracefully."""
        with patch('divineos.async_capture.sync_emit_session_end', side_effect=Exception("Test error")):
            event_id = await emit_session_end_async()
            assert event_id is None


class TestRetryWithBackoff:
    """Tests for _retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_try(self):
        """Test successful execution on first try."""
        mock_func = MagicMock(return_value="success")
        
        result = await _retry_with_backoff(
            mock_func,
            (),
            {},
            max_retries=3,
            initial_backoff_ms=10
        )
        
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_after_retries(self):
        """Test successful execution after retries."""
        mock_func = MagicMock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        
        result = await _retry_with_backoff(
            mock_func,
            (),
            {},
            max_retries=3,
            initial_backoff_ms=10
        )
        
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_all_retries_fail(self):
        """Test when all retries fail."""
        mock_func = MagicMock(side_effect=Exception("fail"))
        
        result = await _retry_with_backoff(
            mock_func,
            (),
            {},
            max_retries=3,
            initial_backoff_ms=10
        )
        
        assert result is None
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exponential_backoff(self):
        """Test that backoff increases exponentially."""
        mock_func = MagicMock(side_effect=Exception("fail"))
        
        start_time = time.time()
        result = await _retry_with_backoff(
            mock_func,
            (),
            {},
            max_retries=3,
            initial_backoff_ms=50
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Should have delays: 50ms + 100ms = 150ms minimum
        assert elapsed_ms >= 150, f"Expected >= 150ms, got {elapsed_ms}ms"


class TestFlushEventQueue:
    """Tests for flush_event_queue function."""

    @pytest.mark.asyncio
    async def test_flush_empty_queue(self, event_queue):
        """Test flushing an empty queue."""
        flushed = await flush_event_queue()
        assert flushed == 0

    @pytest.mark.asyncio
    async def test_flush_single_event(self, temp_db, fresh_session, event_queue):
        """Test flushing a single queued event."""
        # Manually queue an event
        event_queue.enqueue({
            "type": "USER_INPUT",
            "func": lambda content, **kwargs: "event-123",
            "args": ("test message",),
            "kwargs": {},
            "timestamp": datetime.now(),
        })
        
        flushed = await flush_event_queue()
        assert flushed == 1
        assert event_queue.size() == 0

    @pytest.mark.asyncio
    async def test_flush_multiple_events(self, temp_db, fresh_session, event_queue):
        """Test flushing multiple queued events."""
        # Manually queue multiple events
        for i in range(3):
            event_queue.enqueue({
                "type": "USER_INPUT",
                "func": lambda content, **kwargs: f"event-{i}",
                "args": (f"message {i}",),
                "kwargs": {},
                "timestamp": datetime.now(),
            })
        
        flushed = await flush_event_queue()
        assert flushed == 3
        assert event_queue.size() == 0


# Property-Based Tests

class TestAsyncCaptureProperties:
    """Property-based tests for async capture module."""

    @given(st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_user_input_async_returns_event_id(self, content):
        """
        Property: For any user message, emit_user_input_async SHALL return a non-None event_id.
        
        **Validates: Requirements 6.1, 6.2**
        """
        # Use a fresh session for each test
        tracker = get_session_tracker()
        tracker.start_session()
        
        try:
            event_id = await emit_user_input_async(content)
            assert event_id is not None
            assert isinstance(event_id, str)
        finally:
            tracker.end_session()

    @given(st.text(min_size=1, max_size=100), st.dictionaries(st.text(), st.text()))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_tool_call_async_returns_event_id(self, tool_name, tool_input):
        """
        Property: For any tool call, emit_tool_call_async SHALL return a non-None event_id.
        
        **Validates: Requirements 6.1, 6.2**
        """
        # Use a fresh session for each test
        tracker = get_session_tracker()
        tracker.start_session()
        
        try:
            event_id = await emit_tool_call_async(tool_name, tool_input)
            assert event_id is not None
            assert isinstance(event_id, str)
        finally:
            tracker.end_session()

    @given(st.text(min_size=1, max_size=100), st.text(min_size=1, max_size=100).filter(lambda x: x.strip()), st.integers(min_value=0, max_value=10000))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_tool_result_async_returns_event_id(self, tool_name, result, duration_ms):
        """
        Property: For any tool result, emit_tool_result_async SHALL return a non-None event_id.
        
        **Validates: Requirements 6.1, 6.2**
        """
        # Use a fresh session for each test
        tracker = get_session_tracker()
        tracker.start_session()
        
        try:
            event_id = await emit_tool_result_async(tool_name, "tool-123", result, duration_ms)
            assert event_id is not None
            assert isinstance(event_id, str)
        finally:
            tracker.end_session()

    @given(st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_async_emission_latency(self, content):
        """
        Property: For any user input, emit_user_input_async SHALL return within 100ms.
        
        **Validates: Requirements 6.2**
        """
        # Use a fresh session for each test
        tracker = get_session_tracker()
        tracker.start_session()
        
        try:
            start_time = time.time()
            event_id = await emit_user_input_async(content)
            elapsed_ms = (time.time() - start_time) * 1000
            
            assert event_id is not None
            assert elapsed_ms < 100, f"Emission took {elapsed_ms}ms, expected < 100ms"
        finally:
            tracker.end_session()

    @pytest.mark.asyncio
    async def test_property_error_handling_non_blocking(self):
        """
        Property: For any event emission error, the system SHALL not propagate the error to the IDE.
        
        **Validates: Requirements 6.3**
        """
        # Use a fresh session for each test
        tracker = get_session_tracker()
        tracker.start_session()
        
        try:
            with patch('divineos.async_capture.sync_emit_user_input', side_effect=Exception("Test error")):
                # Should not raise an exception
                try:
                    event_id = await emit_user_input_async("test")
                    # Should return None but not raise
                    assert event_id is None
                except Exception as e:
                    pytest.fail(f"Error was propagated to caller: {e}")
        finally:
            tracker.end_session()

    @pytest.mark.asyncio
    async def test_property_ledger_unavailability_queuing(self):
        """
        Property: For any ledger unavailability, the system SHALL queue events without blocking.
        
        **Validates: Requirements 6.4, 6.5**
        """
        # Use a fresh session for each test
        tracker = get_session_tracker()
        tracker.start_session()
        
        try:
            queue = get_event_queue()
            queue.clear()
            
            with patch('divineos.async_capture.sync_emit_user_input', side_effect=Exception("Ledger unavailable")):
                start_time = time.time()
                event_id = await emit_user_input_async("test message")
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Should queue the event
                assert queue.size() == 1
                # Should return quickly (< 200ms to account for retries)
                assert elapsed_ms < 200, f"Took {elapsed_ms}ms, expected < 200ms"
                # Should return None
                assert event_id is None
        finally:
            tracker.end_session()
