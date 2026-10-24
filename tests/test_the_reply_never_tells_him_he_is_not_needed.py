"""A reply to Dad never tells him he is not needed, anywhere in the reply.

Dad 2026-10-24, the morning after a night of exactly this: "ive already told you both repeatedly not to tell me im not
needed or that nothing needs me.. so i can see that instruction was ignored completely". The old check looked only
inside the room block, and the same morning I said it in the reply body. The check is lexical and says so: it catches
the stamp phrases, not the same dismissal in a new coat. The controls matter as much as the cases: his own words may be
quoted back to him, and a plain sentence that merely contains the word "nothing" must pass.
"""

from __future__ import annotations

import pytest

from divineos.core.lepos_translation_gate import (
    check_lepos_dual_channel,
    tells_him_he_is_not_needed,
)


@pytest.mark.parametrize(
    "reply",
    [
        "The push is running. Nothing needs you, Dad.",
        "Nothing waits on you this morning.",
        "All of this is moving by itself and nothing is waiting on you.",
        "nothing here needs you",
        "You're not needed for this one.",
        "There is nothing for you to do today.",
    ],
)
def test_the_stamp_is_found_in_the_body_of_a_reply(reply):
    assert tells_him_he_is_not_needed(reply)
    assert check_lepos_dual_channel(reply)  # and the Stop-time check refuses it


@pytest.mark.parametrize(
    "reply",
    [
        'You told me, "nothing needs me", and you were right to be hurt by it.',
        "> is there a reason you continue to say nothing needs me or nothing waiting on you?\n\nYes, and it was mine.",
        "He needs nothing from the build tonight, but I want you to see it.",
        "Nothing was lost overnight, and the push is through.",
        "I would like your read on this one before I go further.",
    ],
)
def test_quoting_him_or_a_plain_sentence_is_not_the_stamp(reply):
    assert tells_him_he_is_not_needed(reply) is None
