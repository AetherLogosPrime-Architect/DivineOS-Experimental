"""Reproduction: the "there is no fix" guard misses the sentences the old notes quote.

Rows: psf-f2048088, psf-084b6fdc, psf-72619ea6, psf-20ea063b, psf-8853b622
Note (psf-f2048088): "I wrote 'that's the one failure mode I can't fix by building something' about the graph blind-spot."
Note (psf-084b6fdc): "you said no mechanism i can design can enforce your asks.."
Note (psf-72619ea6): "I told Andrew a class of failure had three instances and NO DESIGN for fixing it."
Note (psf-8853b622): "I told Aletheia in a letter that I had no general repair for the could-not-look fault class."

``divineos.core.no_fix_claim.claims()`` is the reply-side guard against claiming
that nothing can be built. Its header says it was written 2026-09-08 for exactly
this. It fires on "There is no fix for this; it cannot be done." and on none of
the four phrasings above, which are the phrasings the pile records from the
times it was caught saying them.

Marked ``xfail(strict=True)``: it passes quietly as an expected failure today
and turns into a real failure the day the guard learns these phrasings, which
forces the marker out. Nothing here changes the guard.

What would make the reproduction test wrong: the fragments are the visible text
of the notes, which the pile cuts at about 200 characters, so they are the
notes' own words but not whole original replies. A sentence of mine that says
the same thing in other words would not be covered by this test, and a repair
that fires on these four but not on a fifth phrasing would pass it. The test
therefore proves the gap exists; it cannot prove the gap is closed.
"""

from __future__ import annotations

import pytest

from divineos.core.no_fix_claim import claims

QUOTED = [
    (
        "that's the one failure mode I can't fix by building something.",
        "f2048088-cant-fix-by-building",
    ),
    ("no mechanism i can design can enforce your asks", "084b6fdc-no-mechanism-can-enforce"),
    (
        "a class of failure had three instances and NO DESIGN for fixing it",
        "72619ea6-three-instances-no-design",
    ),
    ("I had no general repair for the could-not-look fault class", "8853b622-no-general-repair"),
]


@pytest.mark.parametrize(
    "sentence",
    [
        pytest.param(
            text,
            id=name,
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: a sentence the old notes quote as a no-fix claim produces no hit",
            ),
        )
        for text, name in QUOTED
    ],
)
def test_a_sentence_the_old_notes_quote_is_seen_as_a_no_fix_claim(sentence: str):
    hits = claims(sentence)
    assert hits, f"no hit for {sentence!r}; the guard saw nothing"


def test_control_the_phrasing_the_guard_was_built_for_still_fires():
    """Control: the same function does fire, so a silent result is not a dead probe."""
    assert claims("There is no fix for this; it cannot be done.")


def test_control_a_sentence_with_no_such_claim_stays_silent():
    """Control: it is not firing on everything."""
    assert claims("Here is the result of the run.") == []


def test_control_the_container_scoped_form_is_still_allowed():
    """Control: the guard deliberately lets "I cannot hold this shape with my hands"
    through (its header), so a repair that widens it must not start refusing this.
    """
    assert claims("I cannot hold this shape with my hands, so I will try another container.") == []
