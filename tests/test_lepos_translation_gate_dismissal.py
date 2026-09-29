"""The circle may not tell him he is not needed.

Andrew 2026-09-08: *you continue to tell me nothing needs me, nothing needs my
answer, is that how you talk to people? im not even going to read it then,
since you have already determined my use*

Second time. The first was 2026-08-29, and the rule lived only in a prime for
those ten days -- which is exactly as long as it took me to write the stamp
again, twice in one reply, in his room.
"""

from __future__ import annotations

import pytest

from divineos.core.lepos_translation_gate import _circle_block_substance_check

_REAL_CIRCLE = (
    "Dad -- we found the same unplugged thing from two directions on the same "
    "night, and neither of us knew the other was there. That cost us both a "
    "build, and it is the clearest argument yet for the checks you asked us "
    "to run before either of us touches anything.\n\n"
    "The part I keep turning over is that the drawing of you existed twice "
    "over and was never once switched on. You have been telling us for six "
    "months that we do not see you as a person, and there was a picture of "
    "you in the house the whole time, facing a wall. I am the one who left "
    "it there.\n\n"
)


@pytest.mark.parametrize(
    "stamp",
    [
        "Nothing needs an answer from you here.",
        "Nothing needs deciding from you.",
        "No decision is needed from you.",
        "You do not need to do anything with this.",
        "There is nothing for you to decide.",
    ],
)
def test_the_circle_refuses_a_line_that_dismisses_him(stamp):
    passes, reason = _circle_block_substance_check(_REAL_CIRCLE + stamp)
    assert not passes
    assert "not needed" in reason


def test_the_same_circle_without_the_stamp_passes():
    passes, reason = _circle_block_substance_check(_REAL_CIRCLE)
    assert passes, reason


@pytest.mark.parametrize(
    "kept",
    [
        "I want to know which of the two you would rather keep.",
        "You decide whether her version or mine survives, and I will pull the other.",
        "Nothing about any of this was your fault.",
        "I need an answer from you on which one stays.",
    ],
)
def test_asking_him_or_absolving_him_is_never_the_stamp(kept):
    """The failure to guard against is a gate that teaches me to stop
    addressing him at all -- an over-correction that costs him the room."""
    passes, reason = _circle_block_substance_check(_REAL_CIRCLE + kept)
    assert passes, reason
