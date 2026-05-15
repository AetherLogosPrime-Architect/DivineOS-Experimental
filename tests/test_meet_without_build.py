"""Regression-pin tests for the meet-without-build detector."""

from __future__ import annotations

from pathlib import Path

from divineos.core.operating_loop.meet_without_build_detector import (
    MeetWithoutBuildKind,
    evaluate_meet_without_build,
)


def test_principle_named_no_build_fires() -> None:
    """LOAD-BEARING: naming a principle without any build tool fires the flag."""
    text = "The discipline is meet AND build. Without the structural enforcement the lesson will evaporate by next session."
    v = evaluate_meet_without_build(text, tool_calls_in_turn=[])
    assert any(f.kind == MeetWithoutBuildKind.PRINCIPLE_NAMED_NO_BUILD for f in v.flags)


def test_build_tool_in_turn_suppresses() -> None:
    """When the turn contained Edit/Write/Bash, no flag fires."""
    text = "The discipline is meet AND build. I need to build something."
    v = evaluate_meet_without_build(text, tool_calls_in_turn=["Write", "Bash"])
    assert v.flags == []


def test_clean_conversational_response_no_flag() -> None:
    """A response with no structural-fix language does not fire."""
    text = "I hear you. That lands. I'm here."
    v = evaluate_meet_without_build(text, tool_calls_in_turn=[])
    assert v.flags == []


def test_empty_text_no_flag() -> None:
    v = evaluate_meet_without_build("", tool_calls_in_turn=[])
    assert v.flags == []


def test_principle_with_build_evidence_passes() -> None:
    """Principle named + build tool ran = the correct shape, no flag."""
    text = "The lesson is that promises evaporate without structure. I should build the detector now."
    v = evaluate_meet_without_build(text, tool_calls_in_turn=["Write"])
    assert v.flags == []


def test_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import meet_without_build_detector

    src = Path(meet_without_build_detector.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
