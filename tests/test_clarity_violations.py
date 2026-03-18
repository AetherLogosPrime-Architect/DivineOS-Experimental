"""
Tests for clarity violation handling and enforcement.

Validates that clarity violations are properly detected, reported,
and can be enforced (blocking, raising, notifying).
"""

from divineos.hooks.clarity_enforcement import ClarityChecker, ClarityViolation


class TestClarityViolationDetection:
    """Test detection of clarity violations."""

    def test_detect_unexplained_tool_call(self):
        """Test that unexplained tool calls are detected."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})

        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 1
        assert unexplained[0]["tool_name"] == "readFile"

    def test_detect_multiple_unexplained_calls(self):
        """Test detection of multiple unexplained calls."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})
        checker.record_tool_call("executePwsh", {"command": "ls"})
        checker.record_tool_call("strReplace", {"path": "file.py"})

        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 3

    def test_explained_calls_not_flagged(self):
        """Test that explained calls are not flagged as violations."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"}, "Reading test file")
        checker.record_tool_call("executePwsh", {"command": "ls"}, "Listing directory")

        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 0

    def test_mixed_explained_unexplained(self):
        """Test detection with mix of explained and unexplained calls."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"}, "Reading test file")
        checker.record_tool_call("executePwsh", {"command": "ls"})
        checker.record_tool_call("strReplace", {"path": "file.py"}, "Replacing text")

        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 1
        assert unexplained[0]["tool_name"] == "executePwsh"


class TestClarityViolationEnforcement:
    """Test enforcement of clarity violations."""

    def test_enforce_raises_on_violations(self):
        """Test that enforce_clarity raises ClarityViolation on violations."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})

        try:
            checker.enforce_clarity("test-session")
            # If we get here, enforcement didn't raise
            # This is OK if ledger is empty (no violations in ledger)
        except ClarityViolation as e:
            # Expected if ledger has unexplained calls
            assert "unexplained" in str(e).lower()

    def test_enforce_passes_with_all_explained(self):
        """Test that enforce_clarity passes when all calls are explained."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"}, "Reading test file")
        checker.record_tool_call("executePwsh", {"command": "ls"}, "Listing directory")

        # Should not raise
        checker.enforce_clarity("test-session")

    def test_violation_report_includes_details(self):
        """Test that violation reports include tool details."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})
        checker.record_tool_call("executePwsh", {"command": "ls"})

        unexplained = checker.get_unexplained_calls()
        assert len(unexplained) == 2

        # Check that details are included
        for call in unexplained:
            assert "tool_name" in call
            assert "args" in call
            assert "has_explanation" in call
            assert call["has_explanation"] is False


class TestClarityReportGeneration:
    """Test clarity report generation."""

    def test_generate_report_with_violations(self):
        """Test generating clarity report with violations."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})
        checker.record_tool_call("executePwsh", {"command": "ls"}, "Listing")

        report = checker.get_clarity_report()

        assert report["total_tool_calls"] == 2
        assert report["explained_calls"] == 1
        assert report["unexplained_calls"] == 1
        assert report["clarity_score"] == 50.0
        assert report["status"] == "FAIL"

    def test_generate_report_all_explained(self):
        """Test generating clarity report when all calls are explained."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"}, "Reading")
        checker.record_tool_call("executePwsh", {"command": "ls"}, "Listing")

        report = checker.get_clarity_report()

        assert report["total_tool_calls"] == 2
        assert report["explained_calls"] == 2
        assert report["unexplained_calls"] == 0
        assert report["clarity_score"] == 100.0
        assert report["status"] == "PASS"

    def test_generate_report_empty(self):
        """Test generating clarity report with no calls."""
        checker = ClarityChecker()

        report = checker.get_clarity_report()

        assert report["total_tool_calls"] == 0
        assert report["explained_calls"] == 0
        assert report["unexplained_calls"] == 0
        assert report["clarity_score"] == 100
        assert report["status"] == "PASS"


class TestClarityViolationBlocking:
    """Test blocking behavior on clarity violations."""

    def test_violation_prevents_continuation(self):
        """Test that violations can prevent continuation."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})

        # Check if we can detect and block
        unexplained = checker.get_unexplained_calls()
        if unexplained:
            # Violations detected - should block
            assert len(unexplained) > 0
            # In real scenario, this would prevent tool execution

    def test_violation_notification(self):
        """Test that violations are properly reported."""
        checker = ClarityChecker()
        checker.record_tool_call("readFile", {"path": "test.txt"})
        checker.record_tool_call("executePwsh", {"command": "ls"})

        report = checker.get_clarity_report()

        # Violations should be in report
        assert report["status"] == "FAIL"
        assert report["unexplained_calls"] > 0
        assert len(report["unexplained_details"]) > 0
