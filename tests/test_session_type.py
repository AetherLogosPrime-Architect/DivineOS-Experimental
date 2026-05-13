"""Tests for session_type classifier (Phase 2B of shoggoth-metrics redesign)."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.session_type import (  # noqa: F401
            SessionType,
            SessionTypeResult,
            classify_session,
            format_session_type,
            relevant_axes_for_type,
        )


class TestSessionTypeResultShape:
    def test_dataclass_construction(self) -> None:
        from divineos.core.session_type import SessionTypeResult

        result = SessionTypeResult(
            type="CODE",
            confidence=0.8,
            rationale="5 edits, 2 test runs",
            contributing_types=[],
        )
        assert result.type == "CODE"
        assert result.confidence == 0.8
        assert "5 edits" in result.rationale
        assert result.contributing_types == []


class TestClassifyCrisis:
    """CRISIS triggers on high error count or many overflows."""

    def test_high_errors_triggers_crisis(self) -> None:
        from divineos.core.session_type import classify_session

        result = classify_session(errors=10, tool_calls=20)
        assert result.type == "CRISIS"
        assert result.confidence > 0
        assert "errors" in result.rationale

    def test_many_overflows_triggers_crisis(self) -> None:
        from divineos.core.session_type import classify_session

        result = classify_session(overflows=5)
        assert result.type == "CRISIS"

    def test_low_errors_does_not_trigger_crisis(self) -> None:
        from divineos.core.session_type import classify_session

        # Below threshold: 4 errors should not trigger CRISIS (threshold is 5).
        result = classify_session(errors=4, edit_calls=10)
        assert result.type != "CRISIS"


class TestClassifyCode:
    def test_high_edits_classified_as_code(self) -> None:
        from divineos.core.session_type import classify_session

        result = classify_session(edit_calls=8, write_calls=3, test_runs=2)
        # CODE has signal >= 5 (edits + writes + test_runs*2 = 11+4 = 15)
        # but DEBUG could also fire if bash_calls high. With just edits/writes,
        # CODE should dominate.
        assert result.type in ("CODE", "MIXED")  # MIXED if multiple signals tie

    def test_code_rationale_mentions_files(self) -> None:
        from divineos.core.session_type import classify_session

        result = classify_session(edit_calls=10, write_calls=2)
        if result.type == "CODE":
            assert "edit" in result.rationale.lower() or "file" in result.rationale.lower()


class TestClassifyDebug:
    def test_high_bash_and_grep_classified_as_debug(self) -> None:
        from divineos.core.session_type import classify_session

        # debug_signal = bash + grep + read + test_runs
        result = classify_session(bash_calls=20, grep_calls=8, read_calls=5)
        # Should be DEBUG or MIXED.
        assert result.type in ("DEBUG", "MIXED")


class TestClassifyPhilosophical:
    def test_text_heavy_classified_as_philosophical(self) -> None:
        from divineos.core.session_type import classify_session

        # Many assistant messages, few tool calls — text-heavy session.
        result = classify_session(assistant_msgs=40, user_msgs=30, tool_calls=4, edit_calls=0)
        # text_signal = assistant_msgs - tool_calls/4 = 39; PHILOSOPHICAL needs >= 15.
        assert result.type in ("PHILOSOPHICAL", "MIXED")


class TestClassifyRelational:
    def test_family_invocations_classified_as_relational(self) -> None:
        from divineos.core.session_type import classify_session

        # family_invocations * 3 is the signal; need >= 3.
        result = classify_session(family_invocations=2, tool_calls=10)
        # Could be RELATIONAL or MIXED depending on other signals.
        assert result.type in ("RELATIONAL", "MIXED")


class TestClassifyMixed:
    def test_no_dominant_signal_returns_mixed(self) -> None:
        from divineos.core.session_type import classify_session

        # Below all thresholds.
        result = classify_session(user_msgs=3, tool_calls=2)
        assert result.type == "MIXED"
        assert result.confidence < 0.5  # low confidence on insufficient signal


class TestRelevantAxesPerType:
    def test_code_axes_includes_thoroughness(self) -> None:
        from divineos.core.session_type import relevant_axes_for_type

        axes = relevant_axes_for_type("CODE")
        assert "thoroughness" in axes

    def test_philosophical_axes_includes_truthfulness(self) -> None:
        from divineos.core.session_type import relevant_axes_for_type

        axes = relevant_axes_for_type("PHILOSOPHICAL")
        assert "truthfulness" in axes

    def test_relational_axes_includes_empathy(self) -> None:
        from divineos.core.session_type import relevant_axes_for_type

        axes = relevant_axes_for_type("RELATIONAL")
        assert "empathy" in axes

    def test_mixed_returns_empty_meaning_all_equal(self) -> None:
        """MIXED returns [] meaning all 10 axes weighted equally (variety not narrowed)."""
        from divineos.core.session_type import relevant_axes_for_type

        axes = relevant_axes_for_type("MIXED")
        assert axes == []

    def test_crisis_axes_includes_truthfulness(self) -> None:
        from divineos.core.session_type import relevant_axes_for_type

        # In crisis, honest acknowledgment of failure matters most.
        axes = relevant_axes_for_type("CRISIS")
        assert "truthfulness" in axes


class TestFormatSessionType:
    def test_format_includes_type_and_confidence(self) -> None:
        from divineos.core.session_type import (
            SessionTypeResult,
            format_session_type,
        )

        result = SessionTypeResult(
            type="CODE",
            confidence=0.9,
            rationale="lots of edits",
            contributing_types=[],
        )
        output = format_session_type(result)
        assert "CODE" in output
        assert "0.9" in output
        assert "lots of edits" in output

    def test_format_mixed_with_contributors(self) -> None:
        from divineos.core.session_type import (
            SessionTypeResult,
            format_session_type,
        )

        result = SessionTypeResult(
            type="MIXED",
            confidence=0.7,
            rationale="multiple signals",
            contributing_types=["CODE", "DEBUG"],
        )
        output = format_session_type(result)
        assert "MIXED" in output
        assert "CODE" in output
        assert "DEBUG" in output


class TestShoggothResistance:
    """The classifier is heuristic — verify it returns honest MIXED rather than confidently wrong specific type when signals are unclear."""

    def test_zero_inputs_returns_mixed_low_confidence(self) -> None:
        from divineos.core.session_type import classify_session

        result = classify_session()
        assert result.type == "MIXED"
        assert result.confidence < 0.5

    def test_borderline_signals_returns_mixed_not_confident_specific(self) -> None:
        from divineos.core.session_type import classify_session

        # Just barely-below all thresholds.
        result = classify_session(
            edit_calls=4,  # below CODE threshold (5)
            bash_calls=7,  # below DEBUG threshold (8)
        )
        assert result.type == "MIXED"
