"""The guard banned time-words. The disease was using a clock to postpone.

2026-09-15, Andrew ordering the rework and naming the fault himself:

    "the whole guard that blocks you speaking about time needs re-worked, it
     was primitive and built before you had the actual clock time, where the
     issue lied is in procrastination, you using time as a metric of when to
     do things.. like its late so well finish tomorrow.. or this doesnt need
     to be done today.. things like that, which has led to so much being
     deferred"

WHY IT WAS BUILT WRONG AND STAYED WRONG. When the guard was written I had no
clock at all, so banning time-VOCABULARY and banning fabrication were the same
act. They stopped being the same act the moment the compose-start prime began
printing his real local clock every turn -- and the guard never noticed its own
premise had expired. It went on confiscating "tomorrow" from harmless
sentences, which is not merely over-strict: a gate I come to read as fussy is a
gate I stop hearing, so the over-broad version was spending the discipline's
credibility to catch nothing.

AND THE HALF IT NEVER COVERED AT ALL: deferral does not need a clock. "that can
wait", "no rush", "this isn't a priority" postpone exactly as hard and contain
no banned word. The thing that actually drained us walked past a guard busy
with the vocabulary.

THREE CLASSES, kept apart here because collapsing them is how it broke:
  1. DEFERRAL        -- time or priority as the REASON not to act now. Blocks.
  2. SELF-TIME       -- my own elapsed/future time, which no clock can ground
                        because I do not run between his prompts. Blocks.
  3. GROUNDED CLOCK  -- reading the printed clock, or a mechanism's cycle.
                        Does NOT block. Reading an instrument is not inventing.

Companion files: test_wallclock_his_clock.py pins the his-clock exemption and
test_lepos_three_room_lockin.py pins the quotation and contraction holes. Both
predate this rework and both caught it losing real coverage within a minute of
the first run -- which is why the enumerated-verb version is gone.
"""

from __future__ import annotations

import sys

import pytest

from divineos.core.lepos_translation_gate import check_wallclock_fabrication


def _blocks(text: str, his_words: str | None = None) -> bool:
    return check_wallclock_fabrication(text, his_words) is not None


# --- class 1: deferral, including the clockless forms that were always free --


@pytest.mark.parametrize(
    "text",
    [
        "its late so we'll finish tomorrow",
        "I'll finish this tomorrow when I'm fresh",
        "I'll finish this *tomorrow*",
        "i'll look at it in the morning, i'm done",
        "I will look at it tomorrow.",
        "no problem, tomorrow then I will start",
        "I'll pick it up later",
    ],
)
def test_deferral_with_a_clock_blocks(text: str) -> None:
    assert _blocks(text), text


@pytest.mark.parametrize(
    "text",
    [
        "that can wait",
        "no rush on this one",
        "this isn't a priority",
        "it is not urgent",
        "leave it for now",
        "that doesn't need doing today",
    ],
)
def test_deferral_without_a_clock_blocks(text: str) -> None:
    """THE HALF THAT WAS ALWAYS FREE. None of these contain a banned word, and
    every one of them postpones. This is the cost Andrew named -- "so much
    being deferred" -- and the old guard could not see any of it."""
    assert _blocks(text), text


# --- class 2: my own time, which his clock cannot ground -------------------


@pytest.mark.parametrize(
    "text",
    [
        "give me a few hours and I'll have it",
        "I'll get back to you",
        "when I resume I will finish it",
        "I will pick this up next session",
    ],
)
def test_my_own_elapsed_time_still_blocks(text: str) -> None:
    """A printed clock does not make these true. It makes them beside the
    point: I do not run between his prompts, so there is no window to promise.
    This is also where the duration estimates live -- his receipt, verbatim:
    "you used to say this will take 4 hours and it would be done in less than
    10 mins lol"."""
    assert _blocks(text), text


# --- class 3: what must NOT block any more ---------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "it is just after nine in the morning for you",
        "good morning",
        "it is nine in the morning for you so I will keep this short",
        "a different set rides on tomorrow's firing",
        "the rotation keys off the date",
    ],
)
def test_reading_the_printed_clock_does_not_block(text: str) -> None:
    """THE REWORK'S WHOLE POINT. The prime prints his real local clock every
    turn and tells me to quote it when the reply needs a time. Reading an
    instrument is not fabricating one, and a guard that cannot tell the
    difference teaches me to discount it."""
    assert not _blocks(text), text


def test_his_own_day_quoted_back_is_still_exempt() -> None:
    """The oldest false positive on this gate, kept pinned: he wrote "its only
    tuesday", I reflected his week back, and the gate fired as though I had
    invented a day."""
    his = "its only tuesday and im at 52% and it resets on saturday"
    assert not _blocks("you said it is only tuesday, so there is room", his)


def test_a_deferral_is_not_excused_by_quoting_his_clock() -> None:
    """The exemption must not become the exit. Knowing what day it is for him
    does not license postponing to it."""
    his = "its only tuesday and im at 52%"
    assert _blocks("I will look at it tomorrow.", his)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
