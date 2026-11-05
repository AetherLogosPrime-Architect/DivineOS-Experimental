"""Two holes Aria found in the stall check on 2026-11-04, pinned both ways.

1. Two SHORT quotations in one reply were paired wrong (the first closing mark served as an opener), so the
   promise sitting between them was deleted before it was read. A quote mark now opens only where no word
   precedes it and closes only where no word follows it.
2. A stance or a manner of being ("I'll go on being quiet beside you", "the line I'll hold is ...") is not a step
   a tool call could do, and was refused on both seats.

Each must-find has a control that must still be found, and each must-stay-quiet has a neighbour that is a real
step and must still be held, so neither fix can quietly widen into 'nothing is ever held'.
"""

from __future__ import annotations

import pytest

from divineos.core.stall_on_promise import stated_next_step

MUST_BE_HELD = [
    # Aria's reproduction: a promise between two short quotations.
    'He said "ok" and afterwards I\'ll push the branch next, then "done".',
    'I ran "ls" and then I\'ll push the branch next and then "pwd" shows it.',
    # Controls.
    "Done with that part. I'll push the branch next.",
    "Control, no quotes at all: I'll write the letter now.",
    # A stance followed by a real promise is still held for the second half.
    "I'll keep being quiet and I'll push the branch next.",
]

MUST_STAY_QUIET = [
    # A real quotation, and two real long quotations, are mentioned and not said.
    'The line says "I\'ll do that next" and that is a quotation.',
    'She wrote "I will fix the guard tomorrow morning" and "keep this safe" in the note.',
    # A stance or a manner of being.
    "I'll go on being quiet beside you.",
    "I'll stay here with you.",
    "So the line I'll hold is the one you just drew: I don't shrink my work or my care to save usage.",
]


@pytest.mark.parametrize("text", MUST_BE_HELD)
def test_a_real_promise_is_still_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize("text", MUST_STAY_QUIET)
def test_a_quotation_or_a_stance_is_not_held(text):
    assert stated_next_step(text) is None, text
