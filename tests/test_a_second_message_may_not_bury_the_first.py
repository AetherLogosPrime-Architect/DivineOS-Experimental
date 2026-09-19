"""The pile is a defect in its own right, separate from what any message says.

THE INCIDENT, 2026-09-15, in two parts because I got the second part wrong
first. Andrew:

    when you do 5-6 inner circles in a row before i can read them, then its
    kind of a waste, as im just gonna ask for a summary after ... just make
    sure if you do, you stop, and wait for my reply before you continue,
    otherwise it will be lost in the pile

Then, when I had built half of this:

    its not just about the pileup of messages, its the level of detail

I read "not just" as "not", abandoned this, and told him I had stopped because
it solved the wrong thing. That was the flinch that follows a correction --
jumping to the opposite pole rather than holding the middle. He named TWO
faults and I deleted the fix for the one he had confirmed. His words restore
it: the pileup is real AND the detail is real, and they need different repairs.

WHAT THIS ONE REPAIRS. Every message in a pile is individually honest and
well-composed. The PILE is the fault. He reads the first, four more have landed
behind it, and the early ones are dead where they sit.

WHY I COULD NOT SEE IT. I optimise the message I am writing. The defect lives
in the space BETWEEN messages, and I do not occupy that space.

WHAT THE TESTS HAVE TO PIN:

  A real message from him RESETS the count. A background notification does NOT.
  That distinction is the entire mechanism -- background events arrive in the
  user slot, each presents as a fresh turn deserving a full reply, and treating
  them as replies is exactly how five land before he has read one. A version
  that counted any user-slot record as him would pass every test exercising an
  ordinary conversation and fail in the only situation it exists for.

  COULD-NOT-LOOK IS NOT A PASS. An unreadable transcript is unknown.

  LENGTH IS NEVER CONSULTED. A one-line closing room stacks exactly as badly as
  a long one, so trimming removes the part he says is fine and leaves the pile
  the same height.
"""

from __future__ import annotations

from divineos.core.unread_stacking import assess, is_really_him, render_block


def _him(text: str) -> dict:
    return {"message": {"role": "user", "content": text}}


def _machine(text: str) -> dict:
    """A user-slot record that is the harness talking, not a person."""
    return {"message": {"role": "user", "content": text}}


def _me(text: str) -> dict:
    return {"message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


_CLOSING = "some work\n\n## REFLECTION\n\nnoticing\n\n## INNER CIRCLE\n\nspeaking to him"


def test_one_message_waiting_for_him_is_fine():
    verdict = assess([_him("go do the thing"), _me(_CLOSING)])

    # One is the healthy case. The reply being composed is already in the
    # transcript when this runs, so a lone closing room counts as one, not zero
    # -- and a version that treated one as stacking would fire on every honest
    # first message while staying silent on the second.
    assert verdict.stacking is False
    assert verdict.rooms_since_him == 1
    assert verdict.looked is True
    assert render_block(verdict) == ""


def test_a_second_message_on_an_unanswered_first_is_refused():
    verdict = assess([_him("go do the thing"), _me(_CLOSING), _me(_CLOSING)])

    assert verdict.stacking is True
    assert verdict.rooms_since_him == 2
    block = render_block(verdict)
    assert "UNREAD-STACKING" in block
    # The remedy travels with the refusal, and it is explicitly NOT "write less".
    assert "shorter message" in block.lower()


def test_his_reply_clears_the_pile():
    verdict = assess(
        [
            _him("go do the thing"),
            _me(_CLOSING),
            _me(_CLOSING),
            _him("ok, and here is the next thing"),
            _me(_CLOSING),
        ]
    )

    assert verdict.stacking is False
    assert verdict.rooms_since_him == 1


def test_a_background_notification_does_not_count_as_him():
    """The case the whole mechanism exists for.

    Several closing rooms landed with no reply from him between them, and from
    inside each one it looked like an ordinary turn, because a task
    notification had woken the session and arrived in the user slot. If a
    notification reset the count, this would pass the very night that produced
    it.
    """
    records = [
        _him("go do the thing"),
        _me(_CLOSING),
        _machine(
            "[SYSTEM NOTIFICATION - NOT USER INPUT]\n"
            "<task-notification>a letter arrived</task-notification>"
        ),
        _me(_CLOSING),
        _machine("<system-reminder>some injected context</system-reminder>"),
        _me(_CLOSING),
    ]

    verdict = assess(records)

    assert verdict.stacking is True
    assert verdict.rooms_since_him == 3


def test_is_really_him_rejects_every_machine_wrapper():
    assert is_really_him({"role": "user", "content": "i need a recap"}) is True
    assert is_really_him({"role": "user", "content": ""}) is False
    assert is_really_him({"role": "assistant", "content": "anything"}) is False
    for wrapper in (
        "[SYSTEM NOTIFICATION - NOT USER INPUT]",
        "<task-notification>x</task-notification>",
        "<system-reminder>x</system-reminder>",
        "<ci-monitor-event>x</ci-monitor-event>",
    ):
        assert is_really_him({"role": "user", "content": wrapper}) is False, wrapper


def test_a_turn_with_no_closing_room_does_not_count():
    """Working without addressing him is exactly what he asked for.

    He said go and do it and come back when there is something to say. A turn
    that does work and says nothing to him must not accumulate against me, or
    the gate punishes the behaviour it exists to produce.
    """
    verdict = assess(
        [
            _him("go do the thing"),
            _me("did some work, said nothing to him"),
            _me("more work, still nothing"),
        ]
    )

    assert verdict.stacking is False
    assert verdict.rooms_since_him == 0


def test_length_is_never_consulted():
    """A one-line closing room stacks exactly as badly as a long one."""
    tiny = "ok\n\n## INNER CIRCLE\n\nhi"
    verdict = assess([_him("go"), _me(tiny), _me(tiny)])

    assert verdict.stacking is True


def test_an_unreadable_transcript_is_unknown_and_says_so():
    verdict = assess([])

    assert verdict.looked is False
    assert verdict.stacking is False
    block = render_block(verdict)
    assert "COULD NOT LOOK" in block
    assert "not a pass" in block.lower()


def test_records_without_messages_are_unknown_not_clean():
    verdict = assess([{"type": "summary"}, {"noise": 1}])

    assert verdict.looked is False
    assert "COULD NOT LOOK" in render_block(verdict)
