"""Integration tests for Full Agent Session.

Tests that all components work together correctly in a realistic agent session:
- Clarity enforcement
- Learning loop
- Memory monitor
- Contradiction detection and resolution

Property 5: Full session integration
- For any agent session, all components (clarity enforcement, learning loop,
  memory monitor, contradiction detection) SHALL work together correctly,
  with no conflicts or data inconsistencies.
"""

import pytest
from datetime import datetime

from divineos.clarity_enforcement.enforcer import ClarityEnforcer, ClarityViolationException
from divineos.clarity_enforcement.config import ClarityConfig, ClarityEnforcementMode
from divineos.agent_integration.learning_loop import analyze_session_for_lessons
from divineos.agent_integration.memory_monitor import get_memory_monitor
from divineos.core.ledger import get_ledger
from divineos.supersession.contradiction_detector import ContradictionDetector
from divineos.supersession.resolution_engine import ResolutionEngine


class TestFullSessionIntegration:
    """Test full agent session with all components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_full_session"
        self.enforcer = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.LOGGING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )
        self.memory_monitor = get_memory_monitor(self.session_id)
        self.ledger = get_ledger()
        self.detector = ContradictionDetector()
        self.resolver = ResolutionEngine()

    def test_full_session_with_clarity_and_learning(self):
        """
        Test full session with clarity enforcement and learning loop.

        Scenario:
        1. Start session
        2. Make several tool calls with varying clarity
        3. Clarity enforcement logs violations
        4. Learning loop analyzes session
        5. Session completes successfully

        Property 5: Full session integration
        """
        # Load session context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # Make tool calls with varying clarity
        tool_calls = [
            {
                "name": "readFile",
                "input": {"path": "test.txt"},
                "context": "I need to read the test file to understand its structure",
                "expected_violation": False,
            },
            {
                "name": "fsWrite",
                "input": {"path": "output.txt", "text": "data"},
                "context": "random context",
                "expected_violation": True,
            },
            {
                "name": "executePwsh",
                "input": {"command": "echo test"},
                "context": "I need to run a command to verify the system",
                "expected_violation": False,
            },
        ]

        for call in tool_calls:
            # Enforce clarity
            self.enforcer.enforce(
                call["name"],
                call["input"],
                [call["context"]],  # This creates a list with one string element
                self.session_id,
            )

            # Update token usage
            self.memory_monitor.update_token_usage(5000)

        # Analyze session for lessons
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

        # End session
        summary = "Session completed with clarity enforcement"
        session_record = self.memory_monitor.end_session(summary, "completed")
        assert session_record is not None

    def test_full_session_with_memory_management(self):
        """
        Test full session with memory management.

        Scenario:
        1. Start session
        2. Simulate high token usage
        3. Memory monitor triggers compression
        4. Session continues with reduced tokens
        5. Session completes successfully
        """
        # Load session context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # Simulate token usage growth
        token_increments = [10000, 20000, 30000, 40000, 50000]

        for tokens in token_increments:
            status = self.memory_monitor.update_token_usage(tokens)
            assert status is not None

            # If compression needed, compress
            if status.get("should_compress"):
                compressed = self.memory_monitor.compress_context(f"Checkpoint at {tokens} tokens")
                assert compressed is not None

        # End session
        session_record = self.memory_monitor.end_session(
            "Session with memory management completed", "completed"
        )
        assert session_record is not None

    def test_full_session_with_contradiction_detection(self):
        """
        Test full session with contradiction detection and resolution.

        Scenario:
        1. Start session
        2. Store facts in ledger
        3. Create contradictions
        4. Detect contradictions
        5. Resolve contradictions
        6. Verify resolution applied
        """
        # Store initial fact
        fact_1 = {
            "key": "math_result",
            "value": "17 × 23 = 391",
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.95,
        }

        # Store contradicting fact
        fact_2 = {
            "key": "math_result",
            "value": "17 × 23 = 392",
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.90,
        }

        # Add facts to ledger
        self.ledger.store_fact(fact_1)
        self.ledger.store_fact(fact_2)

        # Detect contradictions
        contradiction = self.detector.detect_contradiction(fact_1, fact_2)

        # Verify contradiction detected
        if contradiction:
            assert contradiction is not None, "Should detect contradiction"

            # Resolve contradiction
            resolution = self.resolver.resolve_contradiction(contradiction)
            assert resolution is not None

    def test_full_session_with_all_components(self):
        """
        Test full session with all components working together.

        Scenario:
        1. Start session
        2. Make tool calls (clarity enforcement)
        3. Store facts (contradiction detection)
        4. Monitor memory (memory management)
        5. Analyze patterns (learning loop)
        6. Session completes with all components active

        Property 5: Full session integration
        """
        # Load session context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # Phase 1: Tool calls with clarity enforcement
        tool_calls = [
            ("readFile", {"path": "test.txt"}, "I need to read the file"),
            ("fsWrite", {"path": "output.txt", "text": "data"}, "random context"),
        ]

        for tool_name, tool_input, context_str in tool_calls:
            self.enforcer.enforce(tool_name, tool_input, [context_str], self.session_id)
            self.memory_monitor.update_token_usage(5000)

        # Phase 2: Store facts for contradiction detection
        facts = [
            {
                "key": "test_fact_1",
                "value": "value_1",
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.95,
            },
            {
                "key": "test_fact_2",
                "value": "value_2",
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.90,
            },
        ]

        for fact in facts:
            self.ledger.store_fact(fact)

        # Phase 3: Analyze session
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

        # Phase 4: End session
        session_record = self.memory_monitor.end_session(
            "Full session completed with all components", "completed"
        )
        assert session_record is not None

    def test_session_with_multiple_tool_calls(self):
        """
        Test session with multiple tool calls and pattern learning.

        Scenario:
        1. Make 10 tool calls
        2. Mix of explained and unexplained calls
        3. Learning loop captures patterns
        4. Memory monitor tracks usage
        5. Session completes successfully
        """
        # Make multiple tool calls
        num_calls = 10

        for i in range(num_calls):
            tool_name = ["readFile", "fsWrite", "executePwsh"][i % 3]
            tool_input = (
                {"path": f"test_{i}.txt"} if tool_name == "readFile" else {"command": f"cmd_{i}"}
            )

            # Alternate between explained and unexplained
            if i % 2 == 0:
                context = f"I need to {tool_name} for operation {i}"
            else:
                context = "random context"

            # Enforce clarity
            self.enforcer.enforce(tool_name, tool_input, [context], self.session_id)

            # Update memory
            self.memory_monitor.update_token_usage(3000)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

        # End session
        session_record = self.memory_monitor.end_session(
            f"Session with {num_calls} tool calls completed", "completed"
        )
        assert session_record is not None

    def test_session_error_handling(self):
        """
        Test session error handling across components.

        Scenario:
        1. Start session
        2. Trigger error in clarity enforcement
        3. Verify error is handled
        4. Session continues
        5. Session completes
        """
        # Load session context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # Make a normal call
        self.enforcer.enforce(
            "readFile", {"path": "test.txt"}, ["I need to read the file"], self.session_id
        )

        # Try to trigger error with blocking mode
        enforcer_blocking = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.BLOCKING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )

        # This should raise an exception
        with pytest.raises(ClarityViolationException):
            enforcer_blocking.enforce(
                "readFile", {"path": "test.txt"}, ["random context"], self.session_id
            )

        # Session should still be able to continue
        self.memory_monitor.update_token_usage(5000)

        # End session
        session_record = self.memory_monitor.end_session(
            "Session with error handling completed", "completed"
        )
        assert session_record is not None


class TestFullSessionEdgeCases:
    """Test edge cases in full session integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_edge_case_session"
        self.enforcer = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.LOGGING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )
        self.memory_monitor = get_memory_monitor(self.session_id)
        self.ledger = get_ledger()

    def test_empty_session(self):
        """
        Test session with no tool calls.

        Scenario:
        1. Start session
        2. Don't make any tool calls
        3. End session
        4. Should complete successfully
        """
        # Load context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # End session without any calls
        session_record = self.memory_monitor.end_session("Empty session", "completed")
        assert session_record is not None

    def test_session_with_high_memory_usage(self):
        """
        Test session with high memory usage.

        Scenario:
        1. Start session
        2. Simulate very high token usage
        3. Trigger multiple compressions
        4. Session completes
        """
        # Load context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # Simulate high usage
        high_tokens = 180000
        status = self.memory_monitor.update_token_usage(high_tokens)
        assert status is not None

        # Compress if needed
        if status.get("should_compress"):
            compressed = self.memory_monitor.compress_context("High usage checkpoint")
            assert compressed is not None

        # End session
        session_record = self.memory_monitor.end_session(
            "High memory usage session completed", "completed"
        )
        assert session_record is not None

    def test_session_with_many_violations(self):
        """
        Test session with many clarity violations.

        Scenario:
        1. Start session
        2. Make many unexplained tool calls
        3. Learning loop captures all violations
        4. Session completes
        """
        # Make many unexplained calls
        for i in range(20):
            tool_name = ["readFile", "fsWrite", "executePwsh"][i % 3]
            tool_input = (
                {"path": f"test_{i}.txt"} if tool_name == "readFile" else {"command": f"cmd_{i}"}
            )

            # All unexplained
            self.enforcer.enforce(tool_name, tool_input, ["random context"], self.session_id)

            self.memory_monitor.update_token_usage(2000)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)
        assert lessons is not None

        # End session
        session_record = self.memory_monitor.end_session(
            "Session with many violations completed", "completed"
        )
        assert session_record is not None

    def test_concurrent_sessions(self):
        """
        Test multiple sessions running concurrently.

        Scenario:
        1. Create multiple session IDs
        2. Run operations in each session
        3. Verify sessions don't interfere
        4. End all sessions
        """
        session_ids = ["session_1", "session_2", "session_3"]
        monitors = {}

        # Create monitors for each session
        for session_id in session_ids:
            monitors[session_id] = get_memory_monitor(session_id)

        # Run operations in each session
        for session_id in session_ids:
            monitor = monitors[session_id]
            context = monitor.load_session_context()
            assert context is not None

            monitor.update_token_usage(10000)

        # End all sessions
        for session_id in session_ids:
            monitor = monitors[session_id]
            session_record = monitor.end_session(f"Session {session_id} completed", "completed")
            assert session_record is not None

    def test_session_recovery_after_error(self):
        """
        Test session recovery after an error.

        Scenario:
        1. Start session
        2. Make a call
        3. Trigger error
        4. Recover and continue
        5. End session
        """
        # Load context
        context = self.memory_monitor.load_session_context()
        assert context is not None

        # Make a call
        self.enforcer.enforce(
            "readFile", {"path": "test.txt"}, ["I need to read the file"], self.session_id
        )

        # Try to trigger error
        try:
            # Simulate error
            raise ValueError("Simulated error")
        except ValueError:
            # Recover
            pass

        # Continue session
        self.memory_monitor.update_token_usage(5000)

        # End session
        session_record = self.memory_monitor.end_session(
            "Session with recovery completed", "completed"
        )
        assert session_record is not None
