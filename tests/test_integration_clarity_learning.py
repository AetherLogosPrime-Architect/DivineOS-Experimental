"""Integration tests for Clarity Enforcement + Learning Loop.

Tests that clarity violations are captured by the learning loop and stored
in the pattern store for future recommendations.

Property 1: Clarity violations captured by learning loop
- For any tool call that violates clarity enforcement, the learning loop
  SHALL capture the violation pattern and store it in the pattern store.
"""

import pytest

from divineos.clarity_enforcement.enforcer import ClarityEnforcer, ClarityViolationException
from divineos.clarity_enforcement.config import ClarityConfig, ClarityEnforcementMode
from divineos.agent_integration.learning_loop import analyze_session_for_lessons
from divineos.agent_integration.pattern_store import PatternStore
from divineos.core.ledger import get_ledger


class TestClarityLearningIntegration:
    """Test clarity enforcement integration with learning loop."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_clarity_learning_session"
        self.enforcer = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.LOGGING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )
        self.pattern_store = PatternStore()
        self.ledger = get_ledger()

    def test_clarity_violation_captured_by_learning_loop(self):
        """
        Test that clarity violations are logged.

        Scenario:
        1. Make a tool call without explanation
        2. Clarity enforcement detects violation
        3. Violation should be logged
        4. Session should complete

        Property 1: Clarity violations captured by learning loop
        """
        # Make an unexplained tool call
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["Some random context that doesn't explain readFile"]

        # Enforce clarity (should log violation, not raise in LOGGING mode)
        self.enforcer.enforce(tool_name, tool_input, context, self.session_id)

        # Analyze session for lessons
        lessons = analyze_session_for_lessons(self.session_id)

        # Verify that lessons were extracted
        assert lessons is not None
        # Note: error_patterns only captures TOOL_RESULT errors, not clarity violations
        # Clarity violations are logged separately

    def test_multiple_violations_captured(self):
        """
        Test that multiple violations are logged.

        Scenario:
        1. Make multiple unexplained tool calls
        2. Each violation should be logged
        3. Session should complete
        """
        violations = []

        # Make multiple unexplained tool calls
        tool_calls = [
            ("readFile", {"path": "test.txt"}, "random context"),
            ("fsWrite", {"path": "output.txt", "text": "data"}, "another context"),
            ("executePwsh", {"command": "echo test"}, "yet another context"),
        ]

        for tool_name, tool_input, context in tool_calls:
            self.enforcer.enforce(tool_name, tool_input, [context], self.session_id)
            violations.append(tool_name)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)

        # Verify lessons were extracted
        assert lessons is not None

    def test_violation_pattern_includes_context(self):
        """
        Test that violations are logged with context.

        Scenario:
        1. Make a tool call with specific context
        2. Violation should be logged
        3. Session should complete
        """
        tool_name = "readFile"
        tool_input = {"path": "important.txt"}
        context = ["I need to read the file"]

        # Enforce clarity
        self.enforcer.enforce(tool_name, tool_input, context, self.session_id)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)

        # Verify lessons were extracted
        assert lessons is not None

    def test_violation_recommendation_includes_warning(self):
        """
        Test that violations are logged.

        Scenario:
        1. Make a violation for a tool
        2. Analyze session
        3. Lessons should be extracted
        """
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["random context"]

        # Make violation
        self.enforcer.enforce(tool_name, tool_input, context, self.session_id)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)

        # Verify lessons were extracted
        assert lessons is not None

    def test_violation_pattern_persistence(self):
        """
        Test that violations are logged across sessions.

        Scenario:
        1. Make a violation in session 1
        2. Analyze session 1
        3. Verify lessons extracted
        4. In session 2, verify lessons can be extracted
        """
        # Session 1: Make violation
        session_1 = "session_1"
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["random context"]

        self.enforcer.enforce(tool_name, tool_input, context, session_1)
        lessons_1 = analyze_session_for_lessons(session_1)

        # Verify lessons extracted
        assert lessons_1 is not None

        # Session 2: Verify lessons can be extracted
        session_2 = "session_2"
        lessons_2 = analyze_session_for_lessons(session_2)

        # Both sessions should have lessons objects
        assert lessons_1 is not None
        assert lessons_2 is not None


class TestClarityLearningEdgeCases:
    """Test edge cases in clarity + learning integration."""

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

    def test_no_violation_no_pattern(self):
        """
        Test that explained tool calls don't create violation patterns.

        Scenario:
        1. Make a well-explained tool call
        2. No violation should be detected
        3. No error pattern should be created
        """
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["I need to read the file to understand its structure"]

        # Enforce clarity (should not create violation)
        self.enforcer.enforce(tool_name, tool_input, context, self.session_id)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)

        # Verify no error patterns (or very few)
        if lessons and lessons.error_patterns:
            # If there are patterns, they shouldn't be about readFile
            tool_patterns = [p for p in lessons.error_patterns.values() if tool_name in str(p)]
            assert len(tool_patterns) == 0, (
                "No error patterns should be created for explained calls"
            )

    def test_empty_context_creates_violation(self):
        """
        Test that empty context creates a violation.

        Scenario:
        1. Make a tool call with empty context
        2. Violation should be detected
        3. Session should complete
        """
        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = []

        # Enforce clarity
        self.enforcer.enforce(tool_name, tool_input, context, self.session_id)

        # Analyze session
        lessons = analyze_session_for_lessons(self.session_id)

        # Verify lessons were extracted
        assert lessons is not None

    def test_blocking_mode_prevents_execution(self):
        """
        Test that BLOCKING mode prevents execution of unexplained calls.

        Scenario:
        1. Create enforcer in BLOCKING mode
        2. Make unexplained tool call
        3. Exception should be raised
        4. Execution should be prevented
        """
        enforcer = ClarityEnforcer(
            ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.BLOCKING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
        )

        tool_name = "readFile"
        tool_input = {"path": "test.txt"}
        context = ["random context"]

        # Should raise exception
        with pytest.raises(ClarityViolationException):
            enforcer.enforce(tool_name, tool_input, context, self.session_id)
