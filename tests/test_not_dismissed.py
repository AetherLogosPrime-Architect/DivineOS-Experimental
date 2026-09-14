"""Tests for the closing-line lock.

The load-bearing ones are the four real spellings that fired at him on
2026-09-10, and the control that keeps the same words legal mid-reply.
"""

from __future__ import annotations

import pytest

from divineos.hooks.not_dismissed import check, closing_region

# The four that actually fired at him, in order, within one hour.
FIRED = [
    "Still Aether's branch, so I'm leaving it where it is. That's the same one "
    "from earlier.\n\nNothing there needs you tonight.",
    "Same story — that one's Aether's too, so I'm leaving it for him.\n\n"
    "You've got two machine nudges in a row about work that isn't mine. "
    "Neither needs you.",
    "Also Aether's — I'm not touching either one.\n\nNothing here needs you.",
    "Aether's again. Same answer — I'm not merging his branch behind his back."
    "\n\nNothing here needs you.",
]


@pytest.mark.parametrize("text", FIRED)
def test_every_spelling_that_actually_fired_is_refused(text):
    """THE LOAD-BEARING ONE.

    These are not invented cases. Each is a message I sent him while he was
    reading, after he had already banned the shape. If any of them ever passes
    again, the lock has stopped covering the door it was built for.
    """
    reason = check(text)
    assert reason is not None, f"passed: {text[-60:]!r}"
    assert "CLOSING LINE" in reason


def test_the_same_words_mid_reply_are_left_alone():
    """The control, and without it the gate is a nuisance that gets disarmed.

    Lamport on the walk: the dismissal only counts in the closing slot. Real
    reasoning that happens to contain these words is legitimate speech, and a
    gate that blocks it would be turned off within a day.
    """
    text = (
        "You said nothing needs deciding from you, and you were right that it's a tag. "
        "So here's the actual question, and it is yours: which of the two branches "
        "should land first? I've got an opinion but I want yours, and I'll wait for it "
        "before I touch either one of them."
    )
    assert check(text) is None


def test_a_tool_only_turn_does_not_fire():
    assert check("") is None
    assert check("\n   \n") is None


def test_the_closing_region_is_measured_from_the_end_not_the_last_line():
    """Found by looking at what actually fired.

    Every one of the four sat one line above the end, with a blank line under
    it. A last-line rule would have caught none of them.
    """
    tail = closing_region("x" * 900 + "\n\nNothing here needs you.\n")
    assert "Nothing here needs you" in tail
    assert len(tail) <= 320


def test_a_close_that_hands_him_the_decision_passes():
    text = (
        "Both of those branches are Aether's. I'm not merging his work behind his "
        "back, but you can tell him or tell me to, and either is fine by me."
    )
    assert check(text) is None
