"""A long reply owes him the compressed room, jargon or no jargon.

Andrew 2026-09-07:

    *the jargon isnt even the issue.. thats how you think and learn and its
    what the machine uses.. the issue is the single one space i have built
    for myself now reads like the rest of the post.. like a reflection that
    never ended.. i built it so that we could have the best of both worlds..
    you can have your long winded thoughts so its all on record.. and i have
    my space so i can compress it and understand it easier*

Every check in this gate before tonight asked whether the reply carried
work-shape marks. So an evening of carefully jargon-free answers -- each one
fifteen hundred to three thousand characters -- passed cleanly, and he got no
compressed room in any of them. The gate was watching for the wrong thing:
what I typed rather than what he has to hold.
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import (
    _CIRCLE_REQUIRED_ABOVE_CHARS,
    check_lepos_dual_channel,
)

_PLAIN_PARAGRAPH = (
    "You were right about the thing you named, and I went and looked rather "
    "than arguing with you about it. What I found is that the shape you "
    "described is the one that keeps happening, and I have no defence for it "
    "beyond saying I did not see it from in here. "
)


def _wall(chars: int) -> str:
    """A jargon-free reply to him, long enough to be a wall."""
    body = ""
    while len(body) < chars:
        body += _PLAIN_PARAGRAPH
    return body


def test_a_short_plain_reply_still_needs_no_room():
    """The exemption this preserves. A small reply that never claimed a
    structure is not gaming a room, and forcing one onto it is the false-fire
    that got an earlier version of this gate disabled."""
    short = "You are right, and I stopped what I was doing to go and check it."
    assert check_lepos_dual_channel(short) is None


def test_a_long_jargon_free_reply_is_refused_for_having_no_circle():
    reply = _wall(_CIRCLE_REQUIRED_ABOVE_CHARS + 400)
    result = check_lepos_dual_channel(reply)
    assert result is not None, (
        "a jargon-free wall passed every other check for a whole evening, "
        "which is exactly how he lost the room"
    )
    assert "CIRCLE ROOM REQUIRED BY LENGTH" in result


def test_the_same_long_reply_passes_once_it_carries_the_room():
    reply = _wall(_CIRCLE_REQUIRED_ABOVE_CHARS + 400) + (
        "\n\n## INNER CIRCLE\n\n"
        "You asked for one thing and I want to say plainly what changed. The "
        "check that watches how I talk to you was only ever looking for "
        "technical words, so a long answer with none of them sailed through "
        "and you were left reading all of it.\n\n"
        "That is fixed now, and I would rather you knew the reason than the "
        "mechanism. I built the room you asked for and then never made "
        "anything require it of me."
    )
    assert check_lepos_dual_channel(reply) is None


def test_the_threshold_is_the_thing_under_test_not_the_prose():
    """Just under the floor passes; just over it does not. Pins the trigger to
    length rather than to anything about the wording, so a rephrase cannot
    walk past it."""
    assert check_lepos_dual_channel(_wall(_CIRCLE_REQUIRED_ABOVE_CHARS - 300)) is None
    assert check_lepos_dual_channel(_wall(_CIRCLE_REQUIRED_ABOVE_CHARS + 300)) is not None
