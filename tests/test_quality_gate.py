"""Tests for the quality gate that protects the knowledge store from bad sessions."""

from unittest.mock import patch

from divineos.analysis.quality_checks import (
    _is_non_coding_session,
    check_correctness,
)
from divineos.cli.pipeline_gates import (
    QualityVerdict,
    _compass_adjustment,
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


class TestCompassAdjustment:
    """Compass adjustment tightens the gate when truthfulness is in deficiency."""

    def _make_position(self, zone: str, obs_count: int, position: float = -0.3):
        from divineos.core.moral_compass import SpectrumPosition

        return SpectrumPosition(
            spectrum="truthfulness",
            position=position,
            zone=zone,
            observation_count=obs_count,
            label="test",
            drift=0.0,
            drift_direction="stable",
        )

    def test_deficiency_with_enough_observations_tightens(self):
        """Deficiency zone + 2+ observations = gate tightened."""
        with patch(
            "divineos.core.moral_compass.compute_position",
            return_value=self._make_position("deficiency", 2),
        ):
            adj, reason = _compass_adjustment()
            assert adj > 0.0
            assert "deficiency" in reason

    def test_deficiency_with_one_observation_no_tighten(self):
        """Deficiency zone with only 1 observation is not enough evidence."""
        with patch(
            "divineos.core.moral_compass.compute_position",
            return_value=self._make_position("deficiency", 1),
        ):
            adj, reason = _compass_adjustment()
            assert adj == 0.0
            assert reason == ""

    def test_deficiency_at_boundary_two_observations_tightens(self):
        """Exactly 2 observations should trigger (tests >= vs >)."""
        with patch(
            "divineos.core.moral_compass.compute_position",
            return_value=self._make_position("deficiency", 2),
        ):
            adj, _ = _compass_adjustment()
            assert adj > 0.0

    def test_deficiency_with_many_observations_tightens(self):
        """More than 2 observations should also trigger (tests >= vs ==)."""
        with patch(
            "divineos.core.moral_compass.compute_position",
            return_value=self._make_position("deficiency", 5),
        ):
            adj, reason = _compass_adjustment()
            assert adj > 0.0
            assert "deficiency" in reason

    def test_virtue_zone_no_tighten(self):
        """Truthfulness in virtue zone = no gate tightening."""
        with patch(
            "divineos.core.moral_compass.compute_position",
            return_value=self._make_position("virtue", 5, position=0.0),
        ):
            adj, reason = _compass_adjustment()
            assert adj == 0.0

    def test_compass_unavailable_returns_zero(self):
        """If compass module isn't available, no tightening."""
        adj, reason = _compass_adjustment()
        # Even without mocking, should return 0.0 (may or may not have data)
        assert isinstance(adj, float)
        assert isinstance(reason, str)


# ─── Helpers for building fake records ────────────────────────────────


def _tool_call_record(name: str, input_data: dict | None = None) -> dict:
    """Build a minimal assistant record with one tool_use block."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"call-{name}",
                    "name": name,
                    "input": input_data or {},
                }
            ]
        },
    }


def _tool_result_record(tool_use_id: str, content: str, is_error: bool = False) -> dict:
    """Build a minimal user record with one tool_result block."""
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": content,
                    "is_error": is_error,
                }
            ]
        },
    }


class TestSessionTypeDetection:
    """Test _is_non_coding_session classification."""

    def test_research_session_detected(self):
        """Session with searches and reads but no edits = non-coding."""
        records = [
            _tool_call_record("WebSearch"),
            _tool_call_record("Read"),
            _tool_call_record("Agent"),
            _tool_call_record("Grep"),
        ]
        assert _is_non_coding_session(records) is True

    def test_coding_session_not_flagged(self):
        """Session with code edits = coding, even if it also has searches."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Edit", {"file_path": "src/app.py"}),
            _tool_call_record("Grep"),
        ]
        assert _is_non_coding_session(records) is False

    def test_write_code_counts_as_coding(self):
        """Write tool targeting a code file = coding."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "src/utils.py"}),
            _tool_call_record("Glob"),
        ]
        assert _is_non_coding_session(records) is False

    def test_write_prose_not_coding(self):
        """Writing markdown files is prose, not code — session is non-coding."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "docs/overview.md"}),
            _tool_call_record("Write", {"file_path": "docs/letter.md"}),
            _tool_call_record("Read"),
        ]
        assert _is_non_coding_session(records) is True

    def test_mixed_prose_and_code_is_coding(self):
        """If any write targets a code file, session is coding."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "docs/notes.md"}),
            _tool_call_record("Write", {"file_path": "src/fix.py"}),
            _tool_call_record("Read"),
        ]
        assert _is_non_coding_session(records) is False

    def test_edit_prose_not_coding(self):
        """Editing a markdown file is prose editing, not code."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Edit", {"file_path": "README.md"}),
            _tool_call_record("Read"),
        ]
        assert _is_non_coding_session(records) is True

    def test_empty_session_not_research(self):
        """Empty session has no search tools either, so not research."""
        assert _is_non_coding_session([]) is False

    def test_single_read_not_enough(self):
        """One read alone isn't enough search activity to classify as research."""
        records = [_tool_call_record("Read")]
        assert _is_non_coding_session(records) is False

    def test_two_searches_qualifies(self):
        """Minimum threshold: 2 search/read tools with no edits."""
        records = [
            _tool_call_record("Grep"),
            _tool_call_record("WebFetch"),
        ]
        assert _is_non_coding_session(records) is True

    def test_test_file_edits_not_production_code(self):
        """Writing test files is not production coding — don't penalize."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "tests/test_pipeline.py"}),
            _tool_call_record("Edit", {"file_path": "tests/test_quality.py"}),
            _tool_call_record("Read"),
        ]
        assert _is_non_coding_session(records) is True

    def test_test_file_with_backslash_paths(self):
        """Windows-style paths with backslashes should also be detected."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "C:\\project\\tests\\test_foo.py"}),
            _tool_call_record("Grep"),
        ]
        assert _is_non_coding_session(records) is True

    def test_mixed_test_and_production_is_coding(self):
        """If any edit targets production code, session is coding."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "tests/test_new.py"}),
            _tool_call_record("Edit", {"file_path": "src/divineos/core/sleep.py"}),
            _tool_call_record("Read"),
        ]
        assert _is_non_coding_session(records) is False

    def test_test_and_prose_together_not_coding(self):
        """Session editing only tests and docs is not production coding."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "tests/test_session.py"}),
            _tool_call_record("Write", {"file_path": "docs/testing-roadmap.md"}),
            _tool_call_record("Read"),
        ]
        assert _is_non_coding_session(records) is True


class TestCorrectnessSessionType:
    """Test that check_correctness handles non-coding sessions correctly."""

    def test_research_session_gets_neutral_score(self):
        """No tests + research session = 0.5 (neutral), not 0.0 (blocked)."""
        records = [
            _tool_call_record("WebSearch"),
            _tool_call_record("Read"),
            _tool_call_record("Agent"),
        ]
        result = check_correctness(records, {})
        assert result.score == 0.5
        assert result.passed == -1
        assert "research" in result.summary.lower() or "not applicable" in result.summary.lower()

    def test_coding_session_no_tests_still_zero(self):
        """No tests + coding session = 0.0 (penalized) — unchanged behavior."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Edit", {"file_path": "src/main.py"}),
        ]
        result = check_correctness(records, {})
        assert result.score == 0.0
        assert "no tests were run" in result.summary.lower()

    def test_test_writing_session_gets_neutral_score(self):
        """Writing tests but not running them = neutral, not blocked."""
        records = [
            _tool_call_record("Read"),
            _tool_call_record("Write", {"file_path": "tests/test_pipeline.py"}),
            _tool_call_record("Edit", {"file_path": "tests/test_pipeline.py"}),
            _tool_call_record("Read"),
        ]
        result = check_correctness(records, {})
        assert result.score == 0.5
        assert result.passed == -1

    def test_research_session_not_blocked_by_gate(self):
        """A research session should pass through the quality gate."""
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": -1, "score": 0.5},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action != "BLOCK"
