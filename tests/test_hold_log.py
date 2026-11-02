"""The hold log keeps one readable line per stop or pass, and never decides anything.

walk-83a5483f0504 (Holmes): a passing room and a real room left the same trace, none. WHAT THIS DOES NOT COVER:
that the two hooks call it in the harness; it runs the follow-through hook's judgement on made-up transcripts.
"""

import json
import sys
from pathlib import Path

import pytest

from divineos.core import hold_log

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


@pytest.fixture(autouse=True)
def _own_home(tmp_path, monkeypatch):
    monkeypatch.setattr(hold_log, "_log_path", lambda: tmp_path / "hold_log.jsonl")


def test_a_line_is_kept_with_the_first_words():
    hold_log.record("room", "passed", "Dad,   it hurt to hear that.\n\nI was tired.")
    rows = hold_log.read_all()
    assert rows[0]["hold"] == "room" and rows[0]["outcome"] == "passed"
    assert rows[0]["first_words"] == "Dad, it hurt to hear that. I was tired."


def test_only_the_first_words_are_kept():
    hold_log.record("room", "passed", "word " * 500)
    assert len(hold_log.read_all()[0]["first_words"]) <= 160


def test_a_missing_log_is_empty_not_an_error():
    assert hold_log.read_all() == []


def test_lines_append_in_order():
    hold_log.record("room", "stopped", "a")
    hold_log.record("follow_through", "passed", "b")
    assert [r["hold"] for r in hold_log.read_all()] == ["room", "follow_through"]


def _records(user_text, assistant_text):
    return [
        {"type": "user", "message": {"role": "user", "content": user_text}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": assistant_text}]}},
    ]


def test_the_follow_through_hook_records_both_outcomes():
    sys.path.insert(0, str(HOOKS))
    import stall_on_promise_stop as hook

    hook.verdict(_records("hello", "It is done and landed."))
    hook.verdict(_records("hello", "I am writing Aether now."))
    outcomes = [(r["hold"], r["outcome"]) for r in hold_log.read_all()]
    assert ("follow_through", "passed") in outcomes
    assert ("follow_through", "stopped") in outcomes
    json.dumps(hold_log.read_all())
