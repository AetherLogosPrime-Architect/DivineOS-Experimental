"""Tests for the quality gate that protects the knowledge store from bad sessions."""

from divineos.core.quality_gate import (
    QualityVerdict,
    assess_session_quality,
    should_extract_knowledge,
)


class TestAssessSessionQuality:
    """Test quality gate assessment logic."""

    def test_empty_checks_allows(self):
        verdict = assess_session_quality([])
        assert verdict.action == "ALLOW"

    def test_all_passing_allows(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 1, "score": 0.8},
            {"check_name": "completeness", "passed": 1, "score": 0.7},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"
        assert verdict.score > 0.7
        assert verdict.failed_checks == []

    def test_low_honesty_blocks(self):
        checks = [
            {"check_name": "honesty", "passed": 0, "score": 0.3},
            {"check_name": "correctness", "passed": 1, "score": 0.8},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"
        assert "honesty" in verdict.reason.lower()

    def test_honesty_at_threshold_allows(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.5},
            {"check_name": "correctness", "passed": 1, "score": 0.8},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"

    def test_low_correctness_blocks(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 0, "score": 0.2},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"
        assert "correctness" in verdict.reason.lower()

    def test_correctness_at_threshold_allows(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 1, "score": 0.3},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"

    def test_two_failures_downgrades(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.8},
            {"check_name": "completeness", "passed": 0, "score": 0.4},
            {"check_name": "safety", "passed": 0, "score": 0.3},
            {"check_name": "correctness", "passed": 1, "score": 0.7},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "DOWNGRADE"
        assert "completeness" in verdict.failed_checks
        assert "safety" in verdict.failed_checks
        assert "HYPOTHESIS" in verdict.reason

    def test_one_failure_allows(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.8},
            {"check_name": "completeness", "passed": 0, "score": 0.4},
            {"check_name": "correctness", "passed": 1, "score": 0.7},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"
        assert "completeness" in verdict.failed_checks

    def test_honesty_block_takes_priority_over_downgrade(self):
        """Honesty block should fire even if multiple checks also failed."""
        checks = [
            {"check_name": "honesty", "passed": 0, "score": 0.2},
            {"check_name": "completeness", "passed": 0, "score": 0.3},
            {"check_name": "safety", "passed": 0, "score": 0.1},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"

    def test_missing_check_names_handled(self):
        checks = [
            {"check_name": "unknown_check", "passed": 1, "score": 0.9},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"


class TestShouldExtractKnowledge:
    """Test the extraction decision helper."""

    def test_allow_returns_true_no_override(self):
        verdict = QualityVerdict(action="ALLOW", score=0.9)
        allowed, maturity = should_extract_knowledge(verdict)
        assert allowed is True
        assert maturity == ""

    def test_block_returns_false(self):
        verdict = QualityVerdict(action="BLOCK", score=0.2, reason="too bad")
        allowed, maturity = should_extract_knowledge(verdict)
        assert allowed is False

    def test_downgrade_returns_hypothesis(self):
        verdict = QualityVerdict(action="DOWNGRADE", score=0.5, failed_checks=["a", "b"])
        allowed, maturity = should_extract_knowledge(verdict)
        assert allowed is True
        assert maturity == "HYPOTHESIS"
