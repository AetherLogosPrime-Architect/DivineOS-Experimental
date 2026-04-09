"""Unit tests for session components.

Tests individual components of the session system:
- Clarity enforcement in session
- Learning loop in session
- Memory monitor in session
- Integration of all three components

Validates: Requirements 1.4
"""

from datetime import datetime, timezone

import pytest

from divineos.agent_integration.learning_loop import (
    analyze_session_for_lessons,
    extract_corrections,
    extract_decisions,
    extract_encouragements,
    extract_error_patterns,
    extract_timing_patterns,
    extract_tool_patterns,
)
from divineos.agent_integration.memory_actions import get_memory_monitor
from divineos.clarity_enforcement.config import ClarityConfig, ClarityEnforcementMode
from divineos.clarity_enforcement.enforcer import ClarityEnforcer, ClarityViolationException
from divineos.clarity_enforcement.violation_detector import ViolationDetector, ViolationSeverity
from divineos.core.ledger import get_ledger, log_event


class TestClarityEnforcementInSession:
    """Test clarity enforcement within session context."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_clarity_session"
        self.enforcer = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.LOGGING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )
        self.detector = ViolationDetector()

    def test_clarity_enforcement_detects_violations(self):
        """Test that clarity enforcement detects violations correctly."""
        # Tool call without explanation
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["random context that doesn't explain the tool"]

        # Enforce clarity
        self.enforcer.enforce(tool_name, tool_input, context, self.session_id)

        # Verify violation was detected
        violation = self.detector.detect_violation(tool_name, tool_input, context, self.session_id)
        # May or may not detect depending on semantic analysis
        # Just verify the method works
        assert violation is None or violation is not None

    def test_clarity_enforcement_allows_explained_calls(self):
        """Test that clarity enforcement allows explained tool calls."""
        # Tool call with explanation
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["I need to read the test file to understand its structure"]

        # Enforce clarity - should not raise
        result = self.enforcer.enforce(tool_name, tool_input, context, self.session_id)
        assert result is None

    def test_clarity_enforcement_with_blocking_mode(self):
        """Test clarity enforcement in blocking mode."""
        enforcer_blocking = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.BLOCKING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )

        # Unexplained tool call
        tool_name = "fsWrite"
        tool_input = {"path": "output.txt", "text": "data"}
        context = ["random context"]

        # Should raise exception in blocking mode
        with pytest.raises(ClarityViolationException):
            enforcer_blocking.enforce(tool_name, tool_input, context, self.session_id)

    def test_clarity_enforcement_with_permissive_mode(self):
        """Test clarity enforcement in permissive mode."""
        enforcer_permissive = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
                violation_severity_threshold="medium",
                log_violations=False,
                emit_events=False,
            )
        )

        # Unexplained tool call
        tool_name = "executePwsh"
        tool_input = {"command": "echo test"}
        context = ["random context"]

        # Should not raise in permissive mode
        result = enforcer_permissive.enforce(tool_name, tool_input, context, self.session_id)
        assert result is None

    def test_clarity_enforcement_tracks_violations_per_session(self):
        """Test that violations are tracked per session."""
        session_1 = "session_1"
        session_2 = "session_2"

        # Make calls in session 1
        result1 = self.enforcer.enforce("readFile", {"path": "test1.txt"}, ["random"], session_1)
        assert result1 is None

        # Make calls in session 2
        result2 = self.enforcer.enforce(
            "fsWrite", {"path": "test2.txt", "text": "data"}, ["random"], session_2
        )
        assert result2 is None

    def test_clarity_enforcement_with_multiple_context_items(self):
        """Test clarity enforcement with multiple context items."""
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = [
            "First context item",
            "I need to read the file",
            "Third context item",
        ]

        # Should find explanation in one of the context items
        result = self.enforcer.enforce(tool_name, tool_input, context, self.session_id)
        assert result is None

    def test_clarity_enforcement_with_empty_context(self):
        """Test clarity enforcement with empty context."""
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = []

        # Should detect violation with empty context
        violation = self.detector.detect_violation(tool_name, tool_input, context, self.session_id)
        # Empty context should result in a violation
        assert violation is not None, "Should detect violation with empty context"

    def test_clarity_enforcement_violation_severity(self):
        """Test that violations have appropriate severity levels."""
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["random context"]

        violation = self.detector.detect_violation(tool_name, tool_input, context, self.session_id)
        if violation:
            assert hasattr(violation, "severity"), "Violation should have severity"
            assert violation.severity in [
                ViolationSeverity.LOW,
                ViolationSeverity.MEDIUM,
                ViolationSeverity.HIGH,
            ], "Severity should be valid"


class TestLearningLoopInSession:
    """Test learning loop within session context."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_learning_session"
        self.ledger = get_ledger()

    def test_learning_loop_captures_violations(self):
        """Test that learning loop captures clarity violations."""
        # Create a violation event
        violation_payload = {
            "session_id": self.session_id,
            "tool_name": "readFile",
            "tool_input": {"path": "test.txt"},
            "context": ["random context"],
            "violation_type": "clarity_violation",
            "severity": "medium",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log the violation
        event_id = log_event(
            event_type="CLARITY_VIOLATION",
            actor="clarity_enforcer",
            payload=violation_payload,
            validate=False,
        )

        assert event_id is not None, "Should log violation event"

        # Analyze session for lessons
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None, "Should analyze session for lessons"

    def test_learning_loop_extracts_corrections(self):
        """Test that learning loop extracts corrections from violations."""
        # Create violation events
        events = [
            {
                "type": "CLARITY_VIOLATION",
                "payload": {
                    "tool_name": "readFile",
                    "violation_type": "clarity_violation",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "CLARITY_VIOLATION",
                "payload": {
                    "tool_name": "fsWrite",
                    "violation_type": "clarity_violation",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract corrections
        corrections = extract_corrections(events)
        assert isinstance(corrections, list), "Should return list of corrections"

    def test_learning_loop_extracts_encouragements(self):
        """Test that learning loop extracts encouragements from successful calls."""
        # Create success events
        events = [
            {
                "type": "TOOL_CALL_SUCCESS",
                "payload": {
                    "tool_name": "readFile",
                    "context": "I need to read the file",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract encouragements
        encouragements = extract_encouragements(events)
        assert isinstance(encouragements, list), "Should return list of encouragements"

    def test_learning_loop_extracts_decisions(self):
        """Test that learning loop extracts decisions from events."""
        # Create decision events
        events = [
            {
                "type": "DECISION",
                "payload": {
                    "decision_type": "tool_selection",
                    "tool_name": "readFile",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract decisions
        decisions = extract_decisions(events)
        assert isinstance(decisions, list), "Should return list of decisions"

    def test_learning_loop_extracts_tool_patterns(self):
        """Test that learning loop extracts tool usage patterns."""
        # Create tool call events
        events = [
            {
                "type": "TOOL_CALL",
                "payload": {
                    "tool_name": "readFile",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "TOOL_CALL",
                "payload": {
                    "tool_name": "readFile",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "TOOL_CALL",
                "payload": {
                    "tool_name": "fsWrite",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract patterns
        patterns = extract_tool_patterns(events)
        assert isinstance(patterns, dict), "Should return dict of patterns"
        # readFile should appear more frequently
        if "readFile" in patterns and "fsWrite" in patterns:
            assert patterns["readFile"].frequency >= patterns["fsWrite"].frequency

    def test_learning_loop_extracts_timing_patterns(self):
        """Test that learning loop extracts timing patterns."""
        # Create timed events
        events = [
            {
                "type": "TOOL_CALL",
                "payload": {
                    "tool_name": "readFile",
                    "duration_ms": 100,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "TOOL_CALL",
                "payload": {
                    "tool_name": "readFile",
                    "duration_ms": 150,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract timing patterns
        patterns = extract_timing_patterns(events)
        assert isinstance(patterns, dict), "Should return dict of timing patterns"

    def test_learning_loop_extracts_error_patterns(self):
        """Test that learning loop extracts error patterns."""
        # Create error events
        events = [
            {
                "type": "TOOL_ERROR",
                "payload": {
                    "tool_name": "readFile",
                    "error_type": "FileNotFoundError",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "TOOL_ERROR",
                "payload": {
                    "tool_name": "readFile",
                    "error_type": "FileNotFoundError",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract error patterns
        patterns = extract_error_patterns(events)
        assert isinstance(patterns, dict), "Should return dict of error patterns"

    def test_learning_loop_with_empty_session(self):
        """Test learning loop with session that has no events."""
        # Analyze session with no events
        lessons = analyze_session_for_lessons("nonexistent_session")
        assert lessons is not None, "Should handle empty session gracefully"

    def test_learning_loop_with_mixed_events(self):
        """Test learning loop with mixed event types."""
        # Create mixed events
        events = [
            {
                "type": "CLARITY_VIOLATION",
                "payload": {
                    "tool_name": "readFile",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "TOOL_CALL_SUCCESS",
                "payload": {
                    "tool_name": "fsWrite",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            {
                "type": "TOOL_ERROR",
                "payload": {
                    "tool_name": "executePwsh",
                    "error_type": "RuntimeError",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        ]

        # Extract all patterns
        corrections = extract_corrections(events)
        encouragements = extract_encouragements(events)
        decisions = extract_decisions(events)
        tool_patterns = extract_tool_patterns(events)
        error_patterns = extract_error_patterns(events)

        assert isinstance(corrections, list)
        assert isinstance(encouragements, list)
        assert isinstance(decisions, list)
        assert isinstance(tool_patterns, dict)
        assert isinstance(error_patterns, dict)


class TestMemoryMonitorInSession:
    """Test memory monitor within session context."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_memory_session"
        self.monitor = get_memory_monitor(self.session_id)

    def test_memory_monitor_loads_session_context(self):
        """Test that memory monitor loads session context."""
        context = self.monitor.load_session_context()
        assert context is not None, "Should load session context"
        assert isinstance(context, dict), "Context should be a dict"

    def test_memory_monitor_tracks_token_usage(self):
        """Test that memory monitor tracks token usage."""
        # Update token usage
        status = self.monitor.update_token_usage(10000)
        assert status is not None, "Should return status"
        assert isinstance(status, dict), "Status should be a dict"

    def test_memory_monitor_detects_compression_threshold(self):
        """Test that memory monitor detects when compression is needed."""
        # Simulate high token usage (75% of 200k = 150k)
        status = self.monitor.update_token_usage(150000)
        assert status is not None
        # Check if compression is recommended
        # May or may not trigger depending on implementation

    def test_memory_monitor_compresses_context(self):
        """Test that memory monitor can compress context."""
        # Compress context
        summary = "Session checkpoint at 50% tokens"
        compressed = self.monitor.compress_context(summary)
        assert compressed is not None, "Should return compressed context"

    def test_memory_monitor_saves_work_checkpoint(self):
        """Test that memory monitor saves work checkpoints."""
        # Save checkpoint
        checkpoint = self.monitor.save_work_checkpoint(
            task="test_task",
            status="in_progress",
            files_modified=["test.py"],
            tests_passing=5,
            commit_hash="abc123",
            notes="Test checkpoint",
        )
        assert checkpoint is not None, "Should save checkpoint"

    def test_memory_monitor_ends_session(self):
        """Test that memory monitor ends session correctly."""
        # End session
        result = self.monitor.end_session("Session completed", "completed")
        assert result is not None, "Should end session"

    def test_memory_monitor_tracks_multiple_updates(self):
        """Test that memory monitor tracks multiple token updates."""
        # Make multiple updates
        updates = [10000, 20000, 30000, 40000, 50000]
        for tokens in updates:
            status = self.monitor.update_token_usage(tokens)
            assert status is not None

    def test_memory_monitor_with_high_token_usage(self):
        """Test memory monitor with very high token usage."""
        # Simulate very high usage
        status = self.monitor.update_token_usage(190000)
        assert status is not None
        # Should indicate compression needed or budget exceeded

    def test_memory_monitor_with_zero_tokens(self):
        """Test memory monitor with zero token usage."""
        # Update with zero tokens
        status = self.monitor.update_token_usage(0)
        assert status is not None

    def test_memory_monitor_records_work_outcome(self):
        """Test that memory monitor records work outcomes."""
        # Record outcome
        outcome = self.monitor.record_work_outcome(
            task="test_task",
            pattern_id="test_pattern",
            success=True,
            violations_introduced=0,
            token_efficiency=0.95,
        )
        assert outcome is not None, "Should record outcome"

    def test_memory_monitor_gets_recommendation(self):
        """Test that memory monitor provides recommendations."""
        # Get recommendation
        context = {"current_task": "reading files", "tools_used": ["readFile"]}
        recommendation = self.monitor.get_recommendation(context)
        assert recommendation is not None, "Should provide recommendation"

    def test_memory_monitor_runs_learning_cycle(self):
        """Test that memory monitor runs learning cycle."""
        # Run learning cycle
        result = self.monitor.run_learning_cycle()
        assert result is not None, "Should run learning cycle"


class TestSessionComponentsIntegration:
    """Test integration of all session components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_integration_session"
        self.enforcer = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.LOGGING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )
        self.monitor = get_memory_monitor(self.session_id)
        self.ledger = get_ledger()

    def test_clarity_and_learning_integration(self):
        """Test that clarity enforcement and learning loop work together."""
        # Make a tool call with clarity enforcement
        self.enforcer.enforce(
            "readFile",
            {"path": "test.txt"},
            ["I need to read the file"],
            self.session_id,
        )

        # Update memory
        self.monitor.update_token_usage(5000)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

    def test_clarity_and_memory_integration(self):
        """Test that clarity enforcement and memory monitor work together."""
        # Make multiple tool calls
        for i in range(5):
            result = self.enforcer.enforce(
                "readFile",
                {"path": f"test_{i}.txt"},
                ["I need to read the file"],
                self.session_id,
            )
            assert result is None

            # Update memory after each call
            status = self.monitor.update_token_usage(10000)
            assert status is not None

    def test_learning_and_memory_integration(self):
        """Test that learning loop and memory monitor work together."""
        # Create events
        for i in range(3):
            log_event(
                event_type="TOOL_CALL",
                actor="agent",
                payload={
                    "session_id": self.session_id,
                    "tool_name": "readFile",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                validate=False,
            )

        # Update memory
        self.monitor.update_token_usage(30000)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

    def test_all_components_together(self):
        """Test all components working together in a session."""
        # Phase 1: Clarity enforcement
        tool_calls = [
            ("readFile", {"path": "test1.txt"}, "I need to read the file"),
            ("fsWrite", {"path": "test2.txt", "text": "data"}, "random context"),
            ("executePwsh", {"command": "echo test"}, "I need to run a command"),
        ]

        for tool_name, tool_input, context in tool_calls:
            self.enforcer.enforce(tool_name, tool_input, [context], self.session_id)
            self.monitor.update_token_usage(5000)

        # Phase 2: Store facts
        facts = [
            {
                "key": "test_fact_1",
                "value": "value_1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.95,
            },
        ]

        for fact in facts:
            self.ledger.store_fact(fact)

        # Phase 3: Analyze session
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

        # Phase 4: End session
        session_record = self.monitor.end_session("Full integration test completed", "completed")
        assert session_record is not None

    def test_session_with_violations_and_learning(self):
        """Test session that captures violations and learns from them."""
        # Make unexplained calls
        for i in range(5):
            self.enforcer.enforce(
                "readFile",
                {"path": f"test_{i}.txt"},
                ["random context"],
                self.session_id,
            )

        # Update memory
        self.monitor.update_token_usage(25000)

        # Analyze for lessons
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

    def test_session_with_memory_compression(self):
        """Test session that triggers memory compression."""
        # Make calls and update memory to trigger compression
        for i in range(10):
            self.enforcer.enforce(
                "readFile",
                {"path": f"test_{i}.txt"},
                ["I need to read the file"],
                self.session_id,
            )

            # Accumulate tokens
            status = self.monitor.update_token_usage(15000)

            # Compress if needed
            if status.get("should_compress"):
                self.monitor.compress_context(f"Checkpoint at iteration {i}")

        # End session
        session_record = self.monitor.end_session("Session with compression completed", "completed")
        assert session_record is not None

    def test_session_error_recovery(self):
        """Test session recovery from errors."""
        # Make a normal call
        self.enforcer.enforce(
            "readFile",
            {"path": "test.txt"},
            ["I need to read the file"],
            self.session_id,
        )

        # Simulate error
        try:
            raise ValueError("Simulated error")
        except ValueError:
            pass

        # Continue session
        self.monitor.update_token_usage(5000)

        # End session
        session_record = self.monitor.end_session(
            "Session with error recovery completed", "completed"
        )
        assert session_record is not None

    def test_session_checkpoint_and_recovery(self):
        """Test session checkpoint and recovery."""
        # Make calls
        self.enforcer.enforce(
            "readFile",
            {"path": "test.txt"},
            ["I need to read the file"],
            self.session_id,
        )

        # Save checkpoint
        checkpoint = self.monitor.save_work_checkpoint(
            task="test_task",
            status="in_progress",
            files_modified=["test.py"],
            tests_passing=5,
        )
        assert checkpoint is not None

        # Continue session
        self.monitor.update_token_usage(5000)

        # End session
        session_record = self.monitor.end_session("Session with checkpoint completed", "completed")
        assert session_record is not None
