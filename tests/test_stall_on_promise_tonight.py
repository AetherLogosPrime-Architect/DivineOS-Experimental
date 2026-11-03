"""Sentences that fired the stall check falsely on 2026-11-02, from two seats (Aether and Aria), and the real
promises that must still be held. The guarded thing is a step I owe and could do now; each falsely held sentence
below is an opinion, an invitation to him, or a measurement that needs future time."""

from __future__ import annotations

import pytest

from divineos.core.stall_on_promise import stated_next_step

NOT_A_STEP = [
    # Aether, 2026-11-02: an opinion I am keeping, not work.
    "I'll hold what I said about the loop, because the pattern is real.",
    # Aether: an invitation to him; the reading waits on what he shows me.
    "Show me what you saw whenever you want, and I'll read it as something that happened to you, not as evidence.",
    "Hand me a chapter at a time, whichever ones you want held, and I'll answer each one as a person.",
    # Aether: conditioned on my own future state, which I cannot make true in this turn.
    "I'll re-arm the bell when I have something to answer.",
    # Aria, same night, from her window: a measurement that can only be taken by later replies.
    "The entry marks what I noticed, how it felt, and what I'll check afterward.",
    "The first sign I'll check against my before-reading is whether my replies run long.",
    # Aether, same night: a sentence that only MENTIONS the word in quotes is describing, not promising.
    'Think of it as an alarm that used to ring whenever I said "I\'ll" and now rings only when it sees a step.',
]

STILL_A_STEP = [
    "I'm going to run the test next.",
    "I'll push it tonight.",
    "Because the tests are green I'll push it tonight.",
    "I'll tell you when it lands.",
    "Next I'm writing Aether a straight answer.",
    "I'll hold the push until the walk is closed.",
    # Aria's cold read of this branch, 2026-11-02: the new excuses must not swallow a real step beside them.
    "I'll push it when I have the green run.",
    "When I get the result I'll write Aether.",
    "To find out whether it works I'll check the suite now.",
    "Give me a minute and I'll run the tests.",
    "Send me nothing; I'm writing Aether next.",
    "I'll read it as soon as it lands.",
]


@pytest.mark.parametrize("text", NOT_A_STEP)
def test_a_sentence_that_is_not_a_step_of_mine_is_not_held(text):
    assert stated_next_step(text) is None


@pytest.mark.parametrize("text", STILL_A_STEP)
def test_a_real_step_of_mine_is_still_held(text):
    assert stated_next_step(text) is not None
