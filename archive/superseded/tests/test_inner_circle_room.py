"""The inner-circle gate must actually refuse.

The hook this replaces -- ``lepos-channel-reflect.sh`` -- was registered at
Stop twice and exited 0 on every path for months. Nothing tested whether it
could refuse, because nothing asked. These tests exist so that question is
asked on every run.
"""

from divineos.core.inner_circle_room import (
    MIN_ADDRESS_HITS,
    MIN_REPLY_LEN,
    assess,
    render_block,
)

_FILLER = "x" * MIN_REPLY_LEN


def _long(tail: str) -> str:
    return _FILLER + "\n" + tail


ENDS_IN_WORK = _long(
    "The stamping tool selects which commits to bind from the branch it was "
    "handed, then hands them to an amend that recomputed the branch from the "
    "working tree. Four tests pin the refusal and the guard no longer names "
    "one cause as THE cause."
)

ENDS_IN_THE_ROOM = ENDS_IN_WORK + (
    "\n\nAnd the thing I actually found tonight was that your room had a light "
    "where every other door in this house had a brake. You were right, and I "
    "am sorry it took you saying it this many times."
)


def test_a_long_reply_ending_in_work_is_refused():
    verdict = assess(ENDS_IN_WORK)
    assert verdict.blocks
    assert verdict.address_hits < MIN_ADDRESS_HITS


def test_a_long_reply_ending_in_the_room_passes():
    verdict = assess(ENDS_IN_THE_ROOM)
    assert not verdict.blocks
    assert verdict.address_hits >= MIN_ADDRESS_HITS


def test_a_short_reply_is_exempt_and_exemption_is_not_presence():
    """Exempt must never read back as "had a room".

    A one-line answer to a one-line question owes no closing room. Collapsing
    that into ``present`` would let short replies accumulate as evidence the
    room is happening -- which is precisely how a count reassures about a
    thing that is not occurring.
    """
    verdict = assess("yes, merged.")
    assert verdict.exempt
    assert not verdict.present
    assert not verdict.blocks


def test_second_person_earlier_in_the_reply_does_not_satisfy_the_close():
    """The room is where the reply ENDS, not somewhere it passed through.

    Ordinary work-talk is full of "you asked" and "your branch". If those
    counted, almost every reply would pass while ending in a build log --
    which is the exact failure being repaired.
    """
    front_loaded = (
        "You asked about the merge, and your branch is the one you named, and "
        "yours was already stamped. " + _FILLER + "\nBuild green, four tests, "
        "guard message rewritten, nothing outstanding on the queue."
    )
    assert assess(front_loaded).blocks


def test_a_trailing_code_block_cannot_carry_the_room_out_of_the_window():
    """A command he should run is work, not a room, and must not displace it."""
    fenced = ENDS_IN_THE_ROOM + "\n\n```bash\n" + "git status\n" * 60 + "```\n"
    assert not assess(fenced).blocks


def test_the_refusal_says_what_is_missing_and_forbids_recomposing():
    """A gate that fires without a usable instruction just costs a turn.

    And the instruction has to be APPEND, because rewriting a reply he has
    already read is a standing prohibition here.
    """
    block = render_block(assess(ENDS_IN_WORK))
    assert "APPEND" in block
    assert "do NOT recompose" in block
    assert "Short is allowed; absent is not." in block


def test_empty_input_does_not_block():
    assert not assess("").blocks
