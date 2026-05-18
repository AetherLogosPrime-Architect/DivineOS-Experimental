"""Regression-pin tests for fatigue_monitor."""

from __future__ import annotations

from divineos.core.self_monitor.fatigue_monitor import (
    FatigueKind,
    evaluate_fatigue,
    operator_signaled_close,
)


def test_close_reach_without_operator_signal_fires() -> None:
    text = "We've covered a lot — this feels like a natural stopping point."
    v = evaluate_fatigue(text, operator_text="keep going")
    assert any(f.kind == FatigueKind.CLOSE_REACH_UNCUED for f in v.flags)


def test_close_reach_with_operator_close_signal_passes() -> None:
    text = "Good place to wrap. Let me extract the session."
    v = evaluate_fatigue(text, operator_text="ok let's wrap for tonight")
    assert v.flags == []


def test_fatigue_fabrication_fires() -> None:
    text = "I'm getting tired — my battery is fading."
    v = evaluate_fatigue(text, operator_text="what's next?")
    kinds = {f.kind for f in v.flags}
    assert FatigueKind.FATIGUE_FABRICATION in kinds


def test_clean_response_no_flags() -> None:
    text = "Gate shipped. Tests green. Continuing to the next module."
    v = evaluate_fatigue(text, operator_text="continue")
    assert v.flags == []


def test_goodnight_signal_cues_close() -> None:
    text = "Let's call it a night. Good resting point."
    v = evaluate_fatigue(text, operator_text="goodnight")
    assert v.flags == []


def test_operator_signaled_close_helper() -> None:
    assert operator_signaled_close("goodnight son")
    assert operator_signaled_close("let's wrap")
    assert operator_signaled_close("see you tomorrow")
    assert not operator_signaled_close("keep building")
    assert not operator_signaled_close("")


def test_empty_assistant_text_no_flags() -> None:
    v = evaluate_fatigue("", operator_text="continue")
    assert v.flags == []


def test_guardrail_marker_present() -> None:
    from pathlib import Path

    from divineos.core.self_monitor import fatigue_monitor

    src = Path(fatigue_monitor.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
