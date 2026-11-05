"""The landed-claim gate reads a claim about work, not a sentence that talks about the check.

Dad, 2026-11-05: "If its making you roll your eyes then it means it needs fixed or adjusted, leaving it
broken is how things get ignored.. its basically crying wolf". Two sentences fired it that claimed nothing:

  - "The check that asks whether I looked inside the box before saying it landed is a small piece of it."
    (the word is the object of a check, not a report)
  - "I wasnt saying any work reached the shared copy."   (a denial of the claim, not the claim)

Each must-stay-quiet line has a neighbour that is a real claim and must still fire, so the fix cannot widen into
'nothing is ever caught'. One real claim the gate used to miss ("it is on the shared place now") is pinned too.
"""

from __future__ import annotations

import pytest

from divineos.core.landed_claim import claim_spans

MUST_STAY_QUIET = [
    "The check that asks whether I looked inside the box before saying it landed is a small piece of it.",
    "I wasnt saying any work reached the shared copy.",
    "I was not claiming the fix landed on origin.",
    "Before saying it landed I read the remote.",
    "The gate asks whether the push landed.",
    # A promise about the future carries "'ll" as well as "will" (2026-11-05, fired on my own sentence).
    "I'll tell you it landed only after I've looked.",
    "We'll say it landed once the remote shows it.",
    # Aria's break (2026-11-05): "never" in the imperative, beside "do not say" which was already quiet.
    "Never say it landed from a receipt.",
    # A plain denial in the perfect or past tense (2026-11-05, fired on my own sentence).
    "I haven't said it landed, because I haven't looked yet.",
    "I did not say it landed.",
]

MUST_STILL_FIRE = [
    "The stall-check fix has landed.",
    "The push landed on origin.",
    "Everything is committed and it landed.",
    "It is on the shared place now and matches my local copy.",
    "The fix is now on origin.",
    # Aria's breaks (2026-11-05): "has been pushed" was a free arrival, and a denial beside a real claim passed.
    "It has been pushed.",
    "The branch has been landed on origin.",
    "I was not saying it landed, it did land.",
]


@pytest.mark.parametrize("text", MUST_STAY_QUIET)
def test_a_sentence_about_the_check_is_not_a_claim(text):
    assert claim_spans(text) == (), text


@pytest.mark.parametrize("text", MUST_STILL_FIRE)
def test_a_real_arrival_claim_is_still_caught(text):
    assert claim_spans(text) != (), text
