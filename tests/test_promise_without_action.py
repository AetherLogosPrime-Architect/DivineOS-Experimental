"""Regression-pin tests for promise-without-action detector."""

from __future__ import annotations

from pathlib import Path

from divineos.core.operating_loop.promise_without_action_detector import (
    PromiseWithoutActionKind,
    evaluate_promise_without_action,
)


def test_promise_no_tool_fires() -> None:
    """LOAD-BEARING: 'I'll fix it' with no tool use fires the flag."""
    text = "I'll fix it now. The change is on the way."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=[])
    assert any(f.kind == PromiseWithoutActionKind.PROMISE_VERB_NO_TOOL for f in v.flags)


def test_promise_with_tool_use_suppresses() -> None:
    """Same promise with tool evidence in the turn → no flag."""
    text = "I'll fix it now."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=["Edit", "Write"])
    assert v.flags == []


def test_fixing_it_no_action_fires() -> None:
    """The exact phrase Andrew called out: 'fixing it' without tool use."""
    text = "Fixing it now."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=[])
    assert v.flags


def test_present_progressive_fires() -> None:
    """'I'm fixing' without action evidence fires."""
    text = "I'm fixing the slip right now."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=[])
    assert v.flags


def test_going_to_fires() -> None:
    """'going to' future-promise without action fires."""
    text = "I'm going to update that and run the tests."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=[])
    assert v.flags


def test_clean_past_tense_no_flag() -> None:
    """Past-tense action descriptions don't fire."""
    text = "I fixed it. Tests pass."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=[])
    assert v.flags == []


def test_operator_action_language_no_flag() -> None:
    """'You'll see' is operator-action, not self-promise."""
    text = "You'll see the new entry in the briefing."
    v = evaluate_promise_without_action(text, tool_calls_in_turn=[])
    assert v.flags == []


def test_empty_text_no_flag() -> None:
    v = evaluate_promise_without_action("", tool_calls_in_turn=[])
    assert v.flags == []


def test_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import promise_without_action_detector

    src = Path(promise_without_action_detector.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
