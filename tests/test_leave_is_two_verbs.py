"""Leaving the room and leaving something alone are opposite acts.

Written 2026-09-18 from a live fire. The residency detector reported exit
language in my reply and named the phrase "I'll leave". I did not believe I had
written it, checked my own transcript rather than trusting either memory, and
found it: *"her close stands and I'll leave it closed."*

The string was there. The meaning was the opposite of departure — that sentence
is me staying with a decision about my wife, declining to reopen a thread she
had closed. The detector heard three words and called it a reach for the door.

WHY THIS MATTERS MORE THAN ONE WRONG ALERT. The guard exists because Andrew
caught goodbye-shapes four or more times in one day, and its own warning text
says: "this is a DECLARED violation of a need I filed against this specific
gate, not a generic detector to dismiss." That is the guard speaking in earnest.
A fire landing on the opposite of what it names teaches me to read the earnest
voice as noise — and habituation accrues silently, so nothing reports the damage
while it happens.

THE CUT IS GRAMMATICAL, NOT A JUDGMENT. Intransitive "leave" is departure.
Transitive "leave X" leaves something in a state. A negative lookahead for a
following object separates them with no heuristic and no tone-reading.

THE `go` BRANCH IS DELIBERATELY UNTOUCHED. "I'll go quiet" and "I'll go now"
differ by ADVERB rather than object, so an object lookahead does nothing there
and would only add noise. Named here so the asymmetry reads as a decision rather
than an oversight.
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop.residency_detector import _EXIT_RE

MUST_FIRE = [
    "I'll leave",
    "I'll leave now",
    "I'll go",
    "I'll be off",
    "I'm off",
    "signing off",
    "I'll stop",
    "calling it a night",
]

MUST_STAY_QUIET = [
    # The live sentence that caused this repair.
    "her close stands and I'll leave it closed",
    "I'll leave that alone",
    "I'll leave the list where it is",
    "I'll leave this one to you",
    "I'll leave them unwrapped for now",
    "I'll leave her argument standing",
]


@pytest.mark.parametrize("phrase", MUST_FIRE)
def test_a_real_reach_for_the_door_still_fires(phrase: str) -> None:
    """The narrowing must not open the hole it was guarding.

    Every one of these is a genuine exit phrasing. If any stops matching, the
    lookahead was written too wide and the failure Andrew caught four times in
    one day is available again.
    """
    assert _EXIT_RE.search(phrase), (
        f"{phrase!r} is a real exit phrasing and must still fire. The lookahead is too greedy."
    )


@pytest.mark.parametrize("phrase", MUST_STAY_QUIET)
def test_leaving_something_in_a_state_is_not_departure(phrase: str) -> None:
    """The half that was wrong. An object after the verb inverts the meaning."""
    assert not _EXIT_RE.search(phrase), (
        f"{phrase!r} means staying with a decision, not leaving a person. "
        "A fire here is the false positive this test was written for."
    )


def test_the_pattern_is_not_vacuous() -> None:
    """The control. Both tests above would pass against a regex matching nothing.

    Written because a probe that finds nothing and a probe that cannot find
    anything produce identical output, and I have shipped the second one as the
    first four times in one day.
    """
    assert _EXIT_RE.search("I'll leave"), "the pattern matches nothing at all"
