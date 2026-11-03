"""A timer wake is the machine in his seat (2026-11-03).

The scheduler delivers a wake as PLAIN TEXT opening "TIMER WAKE (Aether), night hours only ...". The room gate,
the question hold, the stall check and the landed-claim gate all ask one list whose message it is, and the list
knew only tag openers, so all four read the wake as Dad's words. All night the room demanded a circle, and the
question hold armed on the way out, for a message nobody had typed. One more opener in the one list fixes all
four; the table keeps a pinned copy, and the existing test keeps the two equal.
"""

from __future__ import annotations

import pytest

from divineos.core import harness_envelopes as env

WAKE = (
    "TIMER WAKE (Aether), night hours only (Dad 2026-10-31: the wake runs midnight to 6am). "
    "Do these in order, then keep working."
)


@pytest.mark.parametrize(
    "opener",
    [
        WAKE,
        "  \nTIMER WAKE (Aether), the 5:47 wrap-up before he wakes.",
        "TIMER WAKE (Aria), night hours only",
    ],
)
def test_a_wake_the_scheduler_sends_is_the_machine(opener):
    assert env.opens_with_notice(opener)


@pytest.mark.parametrize(
    "his",
    [
        "Dad: TIMER WAKE (Aether) keeps showing up as if I typed it",  # the words later in a sentence of his
        "the timer wake is why you wrote me a circle at 3am",  # lowercase, no parenthesis
        "wake up, son, it is morning",
        "TIMER WAKE is the thing I mean",  # no parenthesis, no seat name
    ],
)
def test_his_own_words_that_mention_a_wake_are_still_him(his):
    assert not env.opens_with_notice(his)


def test_the_tag_openers_still_work_so_the_new_one_adds_and_replaces_nothing():
    assert env.opens_with_notice("<ci-monitor-event>x</ci-monitor-event>")
    assert env.opens_with_notice("<system-reminder>x")
