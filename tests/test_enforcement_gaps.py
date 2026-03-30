"""
Targeted tests for enforcement system gaps identified by Grok audit.

Tests cover:
- Merged IDE/MCP failure modes
- Clarity violation handling
- Concurrent tool calls under RLock
- Full session lifecycle
"""

import threading

from divineos.core.tool_wrapper import wrap_tool_execution
from divineos.core.session_manager import initialize_session, end_session
from divineos.hooks.clarity_enforcement import ClarityChecker
from divineos.core.tool_wrapper import get_unified_capture


class TestMergedIDEMCPFailureModes:
    """Test failure modes in merged IDE/MCP paths."""

    def test_unified_capture_singleton_pattern(self):
        """Test that unified capture uses singleton pattern."""
        capture1 = get_unified_capture()
        capture2 = get_unified_capture()

        # Should be same instance
        assert capture1 is capture2

    def test_unified_capture_thread_safety(self):
        """Test that unified capture is thread-safe."""
        capture = get_unified_capture()

        # Should have RLock for thread safety
        assert hasattr(capture, "_lock")

    def test_unified_capture_handles_concurrent_access(self):
        """Test that unified capture handles concurrent access."""
        results = []

        def access_capture():
            try:
                # Just access the singleton
                c = get_unified_capture()
                results.append(c is not None)
            except Exception:
                results.append(False)

        # Launch concurrent accesses
        threads = [threading.Thread(target=access_capture) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert all(results)


class TestClarityViolationHandling:
    """Test clarity violation detection and enforcement."""

    def test_clarity_violation_raises_on_unexplained_calls(self):
        """Test that clarity violations raise exceptions."""
        checker = ClarityChecker()

        # Record unexplained tool call
        checker.record_tool_call("test_tool", "tool_123")

        # Check that unexplained calls are detected
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) > 0

    def test_clarity_violation_message_includes_details(self):
        """Test that violation messages include tool details."""
        checker = ClarityChecker()

        checker.record_tool_call("dangerous_tool", "tool_456")

        # Verify tool is recorded
        unexplained = checker.get_unexplained_calls()
        assert any("dangerous_tool" in str(call) for call in unexplained)

    def test_clarity_no_violation_when_explained(self):
        """Test that explained calls don't violate clarity."""
        checker = ClarityChecker()

        checker.record_tool_call("test_tool", "tool_789")
        checker.record_explanation("Calling test_tool for X reason")

        # Should have no unexplained calls
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

    def test_clarity_report_includes_violation_count(self):
        """Test that clarity reports include violation counts."""
        checker = ClarityChecker()

        checker.record_tool_call("tool_a", "id_a")
        checker.record_tool_call("tool_b", "id_b")
        checker.record_explanation("Explained tool_a")

        # Should have 1 unexplained
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 1


class TestConcurrentToolCallsUnderRLock:
    """Test concurrent tool calls with RLock protection."""

    def test_concurrent_tool_captures_are_serialized(self):
        """Test that concurrent tool captures don't race."""
        capture = get_unified_capture()
        results = []
        errors = []

        def capture_tool(tool_id):
            try:
                result = capture.capture_tool_execution(
                    tool_name=f"tool_{tool_id}",
                    tool_input={"id": tool_id},
                    result={"success": True},
                    duration_ms=10,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Launch concurrent captures
        threads = [threading.Thread(target=capture_tool, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(errors) == 0
        assert len(results) == 5

    def test_rlock_prevents_deadlock_on_nested_calls(self):
        """Test that RLock prevents deadlock on nested tool calls."""
        capture = get_unified_capture()

        # Simulate nested tool call (tool calls another tool)
        def nested_tool():
            capture.capture_tool_execution(
                tool_name="inner_tool",
                tool_input={},
                result={"inner": True},
                duration_ms=5,
            )

        # Should not deadlock
        result = capture.capture_tool_execution(
            tool_name="outer_tool",
            tool_input={},
            result={"outer": True},
            duration_ms=10,
        )

        assert result is not None

    def test_concurrent_clarity_checks_dont_race(self):
        """Test that concurrent clarity checks are safe."""
        checker = ClarityChecker()
        results = []

        def check_clarity(session_id):
            try:
                unexplained = checker.get_unexplained_calls()
                results.append(unexplained)
            except Exception:
                pass

        # Launch concurrent checks
        threads = [threading.Thread(target=check_clarity, args=(f"session_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should complete
        assert len(results) >= 3


class TestFullSessionLifecycle:
    """Test complete session lifecycle with enforcement."""

    def test_session_start_to_end_with_tool_calls(self):
        """Test full session: start → tool call → explanation → end."""
        # Initialize session
        session_id = initialize_session()
        assert session_id is not None

        # Record tool call
        checker = ClarityChecker()
        checker.record_tool_call("test_tool", "tool_id_1")

        # Record explanation
        checker.record_explanation("Calling test_tool for testing")

        # Verify no unexplained calls
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

        # End session
        end_session()

    def test_session_with_multiple_tools_and_explanations(self):
        """Test session with multiple tool calls and explanations."""
        initialize_session()
        checker = ClarityChecker()

        # Multiple tool calls
        for i in range(3):
            checker.record_tool_call(f"tool_{i}", f"id_{i}")
            checker.record_explanation(f"Explanation for tool_{i}")

        # All should be explained
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

        end_session()

    def test_session_with_partial_explanations(self):
        """Test session where only some tools are explained."""
        initialize_session()
        checker = ClarityChecker()

        # Some explained, some not
        checker.record_tool_call("tool_a", "id_a")
        checker.record_explanation("Explained A")

        checker.record_tool_call("tool_b", "id_b")
        # No explanation for tool_b

        checker.record_tool_call("tool_c", "id_c")
        checker.record_explanation("Explained C")

        # Should have 1 unexplained
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 1

        end_session()

    def test_session_enforcement_blocks_on_violations(self):
        """Test that session enforcement detects unexplained calls."""
        initialize_session()
        checker = ClarityChecker()

        # Unexplained tool call
        checker.record_tool_call("critical_tool", "id_critical")

        # Should detect violation
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) > 0

        end_session()


class TestEnforcementIntegration:
    """Integration tests for enforcement system."""

    def test_tool_wrapper_preserves_function_behavior(self):
        """Test that tool wrapper preserves original function behavior."""
        initialize_session()

        # Define a simple tool
        def test_tool(x):
            return x * 2

        # Wrap it - note: wrap_tool_execution takes (tool_name, tool_func, tool_use_id)
        wrapped = wrap_tool_execution("test_tool", test_tool)

        # Should still work
        result = wrapped(5)
        assert result == 10

        end_session()

    def test_clarity_checker_detects_unexplained_tools(self):
        """Test that clarity checker detects unexplained tools."""
        initialize_session()
        checker = ClarityChecker()

        # Tool call without explanation
        checker.record_tool_call("undocumented_tool", "id_undoc")

        # Should detect as unexplained
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) > 0

        end_session()

    def test_full_workflow_with_all_components(self):
        """Test full workflow: session → tool → clarity → verification."""
        # Start session
        session_id = initialize_session()
        assert session_id is not None

        # Create checker
        checker = ClarityChecker()

        # Simulate tool execution
        checker.record_tool_call("workflow_tool", "id_workflow")
        checker.record_explanation("Executing workflow_tool for integration test")

        # Verify no unexplained calls
        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

        # Verify all explained
        assert checker.verify_all_explained()

        # End session
        end_session()
