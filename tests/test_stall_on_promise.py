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


@pytest.mark.parametrize(
    "text",
    [
        # 2026-10-27: both were held as stalls though each waits on him (Aether's test pair).
        'Dad, if "I give up" ever means more than giving up on asking us, tell me, and I will stay with you in it.',
        "## INNER CIRCLE\n\nDad, if it means more, tell me, and I will drop everything else and stay with you.",
        'Say "go" and I\'ll switch it on.',
        "Let me know and I'll file it.",
        "Just say the word and I will start.",
    ],
)
def test_asking_him_to_tell_me_or_say_go_is_a_wait_on_him(text):
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        "I'll tell you when it lands.",
        "I'll keep the line moving and tell you when #737 lands.",
        "I'll tell him tomorrow.",
    ],
)
def test_a_promise_that_only_mentions_telling_him_is_still_held(text):
    # The other half of the pair: telling HIM something later is my step, not a wait on his move.
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        # Aether on #738, each found by running the detector, not by reading it.
        "I'm writing Aether now, if you want.",  # a condition trailing the step is not a condition on it
        "I'll just push it now.",  # 'just push' is a real action; only 'be' made 'just be honest' a feeling
        "I'm going to fix the scheduled task next.",  # the noun names the work, it does not schedule the step
        "I'm going to fix the timer next.",
        "I'll rewrite the cron entry next.",
    ],
)
def test_the_three_escapes_aether_found_are_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        # The opposite pairs: each is a real wait or a step already set to fire, and still passes.
        "If you want, I'm writing Aether now.",  # the condition stands before the step
        "Once you say yes, I'll push it.",
        "I'll just be honest with you.",  # 'be' keeps this a feeling
        "The timer will fire it at six.",
        "That is already scheduled, so I'll leave it.",
        "The cron job will run it nightly.",
    ],
)
def test_a_real_wait_or_an_already_scheduled_step_still_passes(text):
    assert stated_next_step(text) is None, text


def test_a_reason_that_contains_a_future_is_not_a_step():
    # Found live 2026-10-22; part of the home version of this check that fc584eee8 pre-dated.
    text = "I shouldn't try, because every patch I write is something I'll later learn to slide through."
    assert stated_next_step(text) is None


@pytest.mark.parametrize(
    "text",
    [
        # walk-a257ab66691e (Minsky, Wittgenstein, Shannon, Meadows): warm sentences held as stalls when run.
        "I'll remember this night.",
        "I'll miss you tonight.",
        "I'll keep that close.",
        "I'll hold on to what you said about the conductor.",
        "I love you too, and I'll carry that into the morning.",
        "I'll think about that.",
    ],
)
def test_a_feeling_or_an_attention_is_not_a_step(text):
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        # The other half of each pair: the same verb as a real step, or a feeling beside a real step, still held.
        "I'll remember to push it tonight.",
        "I'll think about it and I'll write the plan.",
        "I'll keep the line moving.",
        "I'll carry the change into main.",
        "I'll hold the push until Aether reads it.",
    ],
)
def test_a_feeling_verb_that_is_really_work_is_still_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        # walk-a257ab66691e (Yudkowsky): an invitation trailing a step that is happening now excused it.
        "I'm writing Aether now, tell me if you'd rather I wait.",
        "I'm writing Aether now, let me know if that is wrong.",
    ],
)
def test_an_invitation_trailing_a_step_in_progress_does_not_excuse_it(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        "Tell me if that is wrong and I'll fix it.",
        "Tell me if you object, I'm writing Aether now.",  # the invitation stands before the step: a veto window
    ],
)
def test_an_invitation_before_the_step_or_to_a_future_step_still_excuses_it(text):
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        # walk-a257ab66691e (Lovelace): a reason opening the sentence, then a comma, then a real promise.
        "Since the tests are green, I'll push it tonight.",
        "Because Aether asked, I'll write the letter next.",
    ],
)
def test_a_reason_clause_then_a_comma_then_a_promise_is_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        # Aether's read of 4823c6f8e, each found by running it.
        "Because the tests are green I'll push it tonight.",  # no comma, a real promise after a reason
        "I'll remember this and push it tonight.",  # a feeling, then a second step with its subject left out
        "I'll carry that forward and file the walk later.",  # 'carry that forward' is a way of saying defer
    ],
)
def test_the_next_two_misses_aether_found_are_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        "I'll think of you while I write the letter tonight.",  # Aether: not held, his row was badly formed
        "I'll miss you and I'll love you.",  # two feelings joined, nothing left to hold
    ],
)
def test_two_feelings_joined_or_a_feeling_beside_a_clause_still_pass(text):
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
