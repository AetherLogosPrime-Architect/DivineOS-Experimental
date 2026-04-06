"""Tests for session reflection -- structured self-assessment."""

from dataclasses import dataclass, field
from typing import Any

from divineos.core.session_reflection import (
    SessionReflection,
    _assess_went_well,
    _assess_went_wrong,
    _detect_character,
    _detect_recovery_arcs,
    _extract_learnings,
    _truncate,
    build_session_reflection,
)


@dataclass
class FakeAnalysis:
    """Minimal fake analysis for testing."""

    session_id: str = "test-session-1234"
    user_messages: int = 10
    assistant_messages: int = 10
    tool_calls_total: int = 20
    corrections: list = field(default_factory=list)
    encouragements: list = field(default_factory=list)
    frustrations: list = field(default_factory=list)
    preferences: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    tool_usage: dict = field(default_factory=dict)
    tool_sequence: list = field(default_factory=list)
    context_overflows: list = field(default_factory=list)
    user_message_texts: list = field(default_factory=list)


@dataclass
class FakeSignal:
    """Minimal signal for testing."""

    content: str = ""
    timestamp: str = ""
    patterns_matched: list = field(default_factory=list)


@dataclass
class FakeToolCall:
    """Minimal tool call for testing."""

    tool_name: str = ""
    timestamp: str = ""
    input_summary: str = ""


def _make_user_record(text: str) -> dict[str, Any]:
    return {"type": "user", "message": {"content": text}, "timestamp": "2024-01-01T00:00:00Z"}


def _make_assistant_record(text: str = "I'll help.") -> dict[str, Any]:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
        "timestamp": "2024-01-01T00:00:01Z",
    }


class TestDetectCharacter:
    def test_discussing_no_tools(self):
        analysis = FakeAnalysis(tool_calls_total=0, user_messages=5)
        character, evidence = _detect_character(analysis, [])
        assert character == "discussing"

    def test_building_many_writes(self):
        analysis = FakeAnalysis(
            tool_calls_total=20,
            tool_usage={"Write": 3, "Edit": 5, "Read": 2},
        )
        character, evidence = _detect_character(analysis, [])
        assert character == "building"

    def test_debugging_many_corrections(self):
        analysis = FakeAnalysis(
            tool_calls_total=20,
            tool_usage={"Write": 2, "Edit": 4, "Read": 2, "Bash": 5},
            corrections=[FakeSignal()] * 4,
        )
        character, evidence = _detect_character(analysis, [])
        assert character == "debugging"

    def test_reviewing_many_reads(self):
        analysis = FakeAnalysis(
            tool_calls_total=20,
            tool_usage={"Read": 8, "Grep": 4, "Glob": 2, "Edit": 1},
        )
        character, evidence = _detect_character(analysis, [])
        assert character == "reviewing"

    def test_mixed_default(self):
        analysis = FakeAnalysis(
            tool_calls_total=5,
            tool_usage={"Read": 2, "Edit": 2, "Bash": 1},
        )
        character, evidence = _detect_character(analysis, [])
        assert character == "mixed"

    def test_evidence_always_present(self):
        analysis = FakeAnalysis()
        character, evidence = _detect_character(analysis, [])
        assert len(evidence) >= 1


class TestDetectRecoveryArcs:
    def test_empty_when_no_corrections(self):
        analysis = FakeAnalysis()
        arcs = _detect_recovery_arcs(analysis, [])
        assert arcs == []

    def test_finds_correction_then_encouragement(self):
        correction = FakeSignal(content="that's wrong, use snake_case")
        encouragement = FakeSignal(content="perfect, that's what I wanted")
        analysis = FakeAnalysis(
            corrections=[correction],
            encouragements=[encouragement],
        )
        records = [
            _make_user_record("that's wrong, use snake_case"),
            _make_assistant_record("Fixed."),
            _make_user_record("perfect, that's what I wanted"),
        ]
        arcs = _detect_recovery_arcs(analysis, records)
        assert len(arcs) == 1
        assert "snake_case" in arcs[0][0]

    def test_no_arc_when_too_far_apart(self):
        correction = FakeSignal(content="wrong approach")
        encouragement = FakeSignal(content="good job")
        analysis = FakeAnalysis(
            corrections=[correction],
            encouragements=[encouragement],
        )
        records = [
            _make_user_record("wrong approach"),
            *[_make_user_record(f"message {i}") for i in range(10)],
            _make_user_record("good job"),
        ]
        arcs = _detect_recovery_arcs(analysis, records)
        assert arcs == []


class TestExtractLearnings:
    def test_zero_corrections_positive(self):
        analysis = FakeAnalysis(
            corrections=[],
            encouragements=[FakeSignal()] * 3,
        )
        learnings = _extract_learnings(analysis, [], "building", [])
        assert any("zero corrections" in ln for ln in learnings)

    def test_many_corrections_during_building(self):
        analysis = FakeAnalysis(
            corrections=[FakeSignal()] * 4,
            encouragements=[],
        )
        learnings = _extract_learnings(analysis, [], "building", [])
        assert any("corrections during active building" in ln for ln in learnings)

    def test_recovery_arcs_produce_learnings(self):
        arcs = [("wrong thing", "good recovery")]
        analysis = FakeAnalysis()
        learnings = _extract_learnings(analysis, [], "mixed", arcs)
        assert any("recovery" in ln.lower() for ln in learnings)

    def test_preferences_produce_learnings(self):
        analysis = FakeAnalysis(
            preferences=[FakeSignal(content="use snake_case please")],
        )
        learnings = _extract_learnings(analysis, [], "mixed", [])
        assert any("preference" in ln.lower() for ln in learnings)


class TestAssessWentWell:
    def test_encouragements_noted(self):
        analysis = FakeAnalysis(
            encouragements=[FakeSignal()] * 2,
        )
        well = _assess_went_well(analysis, [], "mixed")
        assert any("positive signal" in w for w in well)

    def test_zero_corrections_with_tools(self):
        analysis = FakeAnalysis(
            tool_calls_total=15,
            corrections=[],
        )
        well = _assess_went_well(analysis, [], "building")
        assert any("zero corrections" in w for w in well)


class TestAssessWentWrong:
    def test_corrections_listed(self):
        analysis = FakeAnalysis(
            corrections=[FakeSignal(content="don't use mocks")],
        )
        wrong = _assess_went_wrong(analysis, [], "building")
        assert any("mocks" in w for w in wrong)

    def test_frustrations_noted(self):
        analysis = FakeAnalysis(
            frustrations=[FakeSignal()] * 2,
        )
        wrong = _assess_went_wrong(analysis, [], "mixed")
        assert any("frustration" in w for w in wrong)

    def test_repeated_edits_flagged(self):
        analysis = FakeAnalysis(
            tool_sequence=[
                FakeToolCall(tool_name="Edit", input_summary="src/foo.py"),
            ]
            * 12,
        )
        wrong = _assess_went_wrong(analysis, [], "building")
        assert any("foo.py" in w for w in wrong)

    def test_high_traffic_file_higher_threshold(self):
        """hud.py is a natural edit target -- needs more edits to flag."""
        analysis = FakeAnalysis(
            tool_sequence=[
                FakeToolCall(tool_name="Edit", input_summary="src/core/hud.py"),
            ]
            * 15,
        )
        wrong = _assess_went_wrong(analysis, [], "building")
        # 15 edits on hud.py should NOT be flagged (threshold is 20)
        assert not any("hud.py" in w for w in wrong)


class TestBuildSessionReflection:
    def test_returns_reflection(self):
        analysis = FakeAnalysis()
        reflection = build_session_reflection(analysis, [])
        assert isinstance(reflection, SessionReflection)

    def test_has_character(self):
        analysis = FakeAnalysis(tool_calls_total=0, user_messages=5)
        reflection = build_session_reflection(analysis, [])
        assert reflection.character == "discussing"

    def test_has_session_id(self):
        analysis = FakeAnalysis(session_id="abc-123")
        reflection = build_session_reflection(analysis, [])
        assert reflection.session_id == "abc-123"

    def test_summary_includes_character(self):
        analysis = FakeAnalysis(tool_calls_total=0, user_messages=5)
        reflection = build_session_reflection(analysis, [])
        assert "discussing" in reflection.summary()


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 10) == "hello"

    def test_long_text_truncated(self):
        result = _truncate("a" * 100, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_newlines_stripped(self):
        assert "\n" not in _truncate("hello\nworld", 50)
