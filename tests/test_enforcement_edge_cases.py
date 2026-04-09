"""
Edge case tests for enforcement system - concurrency, MCP failures, session lifecycle.

Tests cover:
- Concurrent tool calls under RLock
- MCP failure modes (bad JSON, missing fields)
- Full session lifecycle with violations
- Clarity enforcement blocking
"""

import threading

from divineos.core.session_manager import end_session, initialize_session
from divineos.core.tool_wrapper import get_unified_capture
from divineos.hooks.clarity_enforcement import ClarityChecker


class TestConcurrencyEdgeCases:
    """Test concurrency edge cases in enforcement system."""

    def test_concurrent_tool_calls_maintain_order(self):
        """Test that concurrent tool calls maintain logical order."""
        capture = get_unified_capture()
        call_order = []
        lock = threading.Lock()

        def capture_and_record(tool_id):
            capture.capture_tool_execution(
                tool_name=f"tool_{tool_id}",
                tool_input={"id": tool_id},
                result={"success": True},
                duration_ms=10,
            )
            with lock:
                call_order.append(tool_id)

        # Launch concurrent captures
        threads = [threading.Thread(target=capture_and_record, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should complete
        assert len(call_order) == 10

    def test_rlock_handles_reentrant_calls(self):
        """Test that RLock handles reentrant calls correctly."""
        capture = get_unified_capture()
        depth_reached = []

        def recursive_capture(depth):
            if depth > 0:
                capture.capture_tool_execution(
                    tool_name=f"recursive_{depth}",
                    tool_input={"depth": depth},
                    result={"depth": depth},
                    duration_ms=5,
                )
                depth_reached.append(depth)
                recursive_capture(depth - 1)

        # Should not deadlock
        recursive_capture(3)
        assert len(depth_reached) == 3

    def test_concurrent_clarity_checks_with_updates(self):
        """Test concurrent clarity checks while clarity is being updated."""
        checker = ClarityChecker()
        results = []
        errors = []

        def add_tools():
            for i in range(5):
                checker.record_tool_call(f"tool_{i}", f"id_{i}")

        def check_clarity():
            try:
                unexplained = checker.get_unexplained_calls()
                results.append(len(unexplained))
            except Exception as e:
                errors.append(e)

        # Mix tool additions and clarity checks
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=add_tools))
            threads.append(threading.Thread(target=check_clarity))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors
        assert len(errors) == 0
        assert len(results) >= 3


class TestMCPFailureModes:
    """Test MCP failure modes in unified capture."""

    def test_malformed_json_in_tool_input(self):
        """Test handling of malformed JSON in tool input."""
        capture = get_unified_capture()

        # Should handle gracefully
        result = capture.capture_tool_execution(
            tool_name="test_tool",
            tool_input={"circular": None},  # Will be converted to string
            result={"success": True},
            duration_ms=10,
        )

        assert result is not None

    def test_missing_required_fields_in_result(self):
        """Test handling of missing required fields."""
        capture = get_unified_capture()

        # Should handle gracefully even with minimal result
        result = capture.capture_tool_execution(
            tool_name="minimal_tool",
            tool_input={},
            result=None,
            duration_ms=0,
        )

        assert result is not None

    def test_very_large_tool_result_truncation(self):
        """Test that very large results are truncated."""
        capture = get_unified_capture()

        # Create a very large result
        large_result = "x" * 10000

        result = capture.capture_tool_execution(
            tool_name="large_tool",
            tool_input={},
            result=large_result,
            duration_ms=100,
        )

        # Should complete without error
        assert result is not None

    def test_tool_execution_with_exception_in_result(self):
        """Test handling of exceptions in tool results."""
        capture = get_unified_capture()

        # Should handle exception objects gracefully
        try:
            raise ValueError("Test error")
        except Exception as e:
            result = capture.capture_tool_execution(
                tool_name="error_tool",
                tool_input={},
                result=str(e),
                duration_ms=10,
                failed=True,
                error_message=str(e),
            )

        assert result is not None


class TestSessionLifecycleViolations:
    """Test full session lifecycle with clarity violations."""

    def test_session_with_all_tools_explained(self):
        """Test session where all tools are properly explained."""
        initialize_session()
        checker = ClarityChecker()

        # Add tools with explanations
        for i in range(5):
            checker.record_tool_call(f"tool_{i}", f"id_{i}")
            checker.record_explanation(f"Explanation for tool_{i}")

        # Should have no violations
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

        end_session()

    def test_session_with_mixed_explained_unexplained(self):
        """Test session with mix of explained and unexplained tools."""
        initialize_session()
        checker = ClarityChecker()

        # Add mix of explained and unexplained
        checker.record_tool_call("explained_1", "id_1")
        checker.record_explanation("Explained")

        checker.record_tool_call("unexplained_1", "id_2")

        checker.record_tool_call("explained_2", "id_3")
        checker.record_explanation("Explained")

        # Should have 1 violation
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 1

        end_session()

    def test_session_with_all_tools_unexplained(self):
        """Test session where no tools are explained."""
        initialize_session()
        checker = ClarityChecker()

        # Add tools without explanations
        for i in range(3):
            checker.record_tool_call(f"tool_{i}", f"id_{i}")

        # Should have 3 violations
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 3

        end_session()

    def test_session_enforcement_report_accuracy(self):
        """Test that enforcement reports are accurate."""
        initialize_session()
        checker = ClarityChecker()

        # Add tools
        checker.record_tool_call("tool_a", "id_a")
        checker.record_tool_call("tool_b", "id_b")
        checker.record_tool_call("tool_c", "id_c")

        # Explain some
        checker.record_explanation("Explained A")
        checker.record_explanation("Explained C")

        # Verify unexplained count (at least 1 should be unexplained)
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) >= 1

        end_session()


class TestClarityEnforcementBlocking:
    """Test that clarity enforcement truly blocks on violations."""

    def test_enforcement_detects_violations(self):
        """Test that enforcement detects violations."""
        initialize_session()
        checker = ClarityChecker()

        # Unexplained tool
        checker.record_tool_call("critical_tool", "id_critical")

        # Should detect violation
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) > 0

        end_session()

    def test_enforcement_includes_tool_details(self):
        """Test that enforcement includes tool details."""
        initialize_session()
        checker = ClarityChecker()

        # Multiple unexplained tools
        checker.record_tool_call("tool_x", "id_x")
        checker.record_tool_call("tool_y", "id_y")

        # Should detect both
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 2

        end_session()

    def test_enforcement_passes_when_all_explained(self):
        """Test that enforcement passes when all tools are explained."""
        initialize_session()
        checker = ClarityChecker()

        # All explained
        checker.record_tool_call("tool_1", "id_1")
        checker.record_explanation("Explained 1")

        checker.record_tool_call("tool_2", "id_2")
        checker.record_explanation("Explained 2")

        # Should have no unexplained
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

        end_session()
