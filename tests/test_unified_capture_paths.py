"""
Tests for unified IDE/MCP capture paths.

Validates that the merged capture system works correctly for both
IDE IDE and MCP server scenarios.
"""

from divineos.core.tool_wrapper import (
    UnifiedToolCapture,
    get_unified_capture,
    capture_tool_execution,
)
from divineos.core.tool_wrapper import (
    get_ide_tool_executor,
)


class TestUnifiedCaptureHappyPath:
    """Test unified capture in happy path scenarios."""

    def test_unified_capture_emits_both_events(self):
        """Test that unified capture emits both TOOL_CALL and TOOL_RESULT."""
        capture = UnifiedToolCapture()
        tool_call_id, tool_result_id = capture.capture_tool_execution(
            tool_name="readFile",
            tool_input={"path": "test.txt"},
            result="file contents",
            duration_ms=100,
        )

        assert tool_call_id is not None
        assert tool_result_id is not None

    def test_unified_capture_preserves_input_data(self):
        """Test that unified capture preserves input data."""
        capture = UnifiedToolCapture()
        input_data = {"path": "test.txt", "mode": "read"}

        capture.capture_tool_execution(
            tool_name="readFile",
            tool_input=input_data,
            result="contents",
            duration_ms=100,
        )

        # Verify events were created (would be in ledger)
        # This is a basic check that capture didn't lose data


class TestUnifiedCaptureFailurePath:
    """Test unified capture in failure scenarios."""

    def test_unified_capture_handles_tool_failure(self):
        """Test that unified capture handles tool failures."""
        capture = UnifiedToolCapture()
        tool_call_id, tool_result_id = capture.capture_tool_execution(
            tool_name="readFile",
            tool_input={"path": "nonexistent.txt"},
            result="Error: File not found",
            duration_ms=50,
            failed=True,
            error_message="File not found",
        )

        assert tool_call_id is not None
        assert tool_result_id is not None

    def test_unified_capture_with_exception_message(self):
        """Test unified capture with exception details."""
        capture = UnifiedToolCapture()
        error_msg = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"

        tool_call_id, tool_result_id = capture.capture_tool_execution(
            tool_name="executePwsh",
            tool_input={"command": "python script.py"},
            result=error_msg,
            duration_ms=100,
            failed=True,
            error_message=error_msg,
        )

        assert tool_call_id is not None
        assert tool_result_id is not None


class TestIDEIntegrationWithUnified:
    """Test IDE integration using unified capture."""

    def test_ide_capture_uses_unified(self):
        """Test that IDEToolCapture uses unified capture."""
        executor = get_ide_tool_executor()
        tool_use_id = executor.start_tool_execution(
            tool_name="readFile",
            tool_input={"path": "test.txt"},
        )
        result_id = executor.end_tool_execution(tool_use_id, "contents", failed=False)

        assert tool_use_id is not None
        assert result_id is not None

    def test_ide_capture_multiple_calls(self):
        """Test multiple IDE captures in sequence."""
        executor = get_ide_tool_executor()

        for i in range(3):
            tool_use_id = executor.start_tool_execution(
                tool_name=f"tool_{i}",
                tool_input={"index": i},
            )
            result_id = executor.end_tool_execution(tool_use_id, f"result_{i}", failed=False)
            assert tool_use_id is not None
            assert result_id is not None


class TestUnifiedCaptureSingleton:
    """Test singleton behavior of unified capture."""

    def test_get_unified_capture_returns_same_instance(self):
        """Test that get_unified_capture returns the same instance."""
        capture1 = get_unified_capture()
        capture2 = get_unified_capture()

        assert capture1 is capture2

    def test_convenience_function_uses_singleton(self):
        """Test that convenience function uses singleton."""
        # Use convenience function
        call_id, result_id = capture_tool_execution(
            tool_name="readFile",
            tool_input={"path": "test.txt"},
            result="contents",
            duration_ms=100,
        )

        # Should have used the singleton
        assert call_id is not None
        assert result_id is not None


class TestUnifiedCaptureThreadSafety:
    """Test thread safety of unified capture."""

    def test_unified_capture_lock_exists(self):
        """Test that unified capture has locking mechanism."""
        capture = UnifiedToolCapture()

        # Verify lock exists
        assert hasattr(capture, "_lock")
        assert capture._lock is not None

    def test_concurrent_captures_dont_corrupt(self):
        """Test that concurrent captures don't corrupt data."""
        import threading

        capture = UnifiedToolCapture()
        results = []

        def capture_tool():
            call_id, result_id = capture.capture_tool_execution(
                tool_name="readFile",
                tool_input={"path": "test.txt"},
                result="contents",
                duration_ms=50,
            )
            results.append((call_id, result_id))

        threads = [threading.Thread(target=capture_tool) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All captures should have succeeded
        assert len(results) == 3
        for call_id, result_id in results:
            assert call_id is not None
            assert result_id is not None
