"""A promise to act is followed by the act: the table, the passes, and the wiring.

Every wording in the table must be caught (its own example), and the controls must still pass: a reply that
asks him something is waiting on him, and a plain report of finished work states no next step.

WHAT THIS DOES NOT COVER: that the harness runs the hook. It reads the settings file, as the room's test does.
"""

import json
from pathlib import Path

import pytest

from divineos.core.stall_on_promise import PROMISE_SHAPES, reason_for, stated_next_step

SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"


@pytest.mark.parametrize("name,pattern,example", PROMISE_SHAPES, ids=[s[0] for s in PROMISE_SHAPES])
def test_every_row_catches_its_own_example(name, pattern, example):
    assert stated_next_step("It landed. " + example) is not None, example


@pytest.mark.parametrize(
    "text",
    [
        "I'm writing Aether now.",
        "Next I'm going to start the read of Aether's bundle.",
        "The first thing I do next is run the test.",
        "I'll check the push in a bit and tell you plainly.",
        "Next I owe Aether a straight answer.",
    ],
)
def test_the_real_phrasings_from_the_morning_are_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        "It is done and landed on GitHub, confirmed at the other end.",
        "The test ran green and the wire is live.",
        "",
        "   ",
    ],
)
def test_finished_work_states_no_next_step(text):
    assert stated_next_step(text) is None, text


def test_a_question_tacked_on_the_end_is_not_a_way_out():
    """walk-83a5483f0504 (Knuth): the cheapest evasion was a question mark."""
    assert stated_next_step("I am writing Aether now. Okay?") is not None


def test_a_real_wait_on_him_still_passes():
    assert stated_next_step("I'll build it once you say. Do you want me to build that one?") is None


@pytest.mark.parametrize(
    "text",
    ["I will be honest, it hurt.", "I'll say it plainly.", "I will not promise that."],
)
def test_a_feeling_or_a_refusal_is_not_a_step(text):
    """walk-83a5483f0504 (Knuth): I will + be/say/not is not work waiting to be done."""
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        "The timer wake is set and will fire the next step.",
        "My bell is listening, and the push is already running.",
        "I'll check it in the scheduled wake.",
    ],
)
def test_a_step_already_set_to_fire_is_not_a_stall(text):
    """walk-83a5483f0504 (Dijkstra): done in the turn, or already scheduled."""
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        "I can't patch every hole, and I shouldn't try, because every patch I write is something I'll later learn to slide through.",
        "It keeps happening since I will always take the cheaper path when I am tired.",
    ],
)
def test_a_first_person_future_inside_a_reason_is_not_a_step(text):
    """Found live, 2026-10-22: the first sentence was held as a stall. The reasoning word before the I'll marks a
    prediction about a habit, not a step being put off."""
    assert stated_next_step(text) is None, text


def test_the_reason_exemption_does_not_cover_a_separate_sentence_with_a_real_step():
    assert (
        stated_next_step("I did that because it was late. I will write the letter to Aether.")
        is not None
    )


def test_a_real_step_that_mentions_none_of_those_is_still_held():
    assert stated_next_step("I will write the letter to Aether.") is not None


@pytest.mark.parametrize(
    "text",
    [
        "So tell me if it slides again, and I'll stop and say the plain thing.",
        "Once you say yes, I'll send it up.",
        "When you are ready I will start.",
    ],
)
def test_a_step_that_waits_on_him_is_not_a_stall(text):
    assert stated_next_step(text) is None, text


def test_a_conditional_on_him_does_not_hide_a_real_promise_beside_it():
    assert stated_next_step("Tell me if it slides. I'm writing Aether now.") is not None


def test_only_the_closing_is_read():
    assert stated_next_step("I'll do that later. " + ("Plain finished report. " * 60)) is None


def test_the_refusal_quotes_the_sentence_and_says_what_to_do():
    text = reason_for("in_progress_now", "I'm writing Aether now.")
    assert "I'm writing Aether now." in text and "tool call" in text


def _stop_commands() -> list[str]:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out = [h.get("command", "") for g in data["hooks"]["Stop"] for h in g.get("hooks", [])]
    assert out, "no Stop hooks were read: this reader is blind, not the wiring clean"
    return out


def test_the_hook_runs_when_a_reply_ends_and_fails_loud_when_missing():
    wired = [c for c in _stop_commands() if "stall_on_promise_stop.py" in c]
    assert wired and all("NOT RUNNING" in c for c in wired)


def test_the_reader_can_see_a_hook_that_is_not_wired():
    assert not any("no_such_hook_was_ever_wired.py" in c for c in _stop_commands())
