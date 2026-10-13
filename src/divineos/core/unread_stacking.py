"""A second closing room may not land on top of an unread first one.

WHY THIS EXISTS. Andrew, 2026-09-15, correcting a reading I had got exactly
backwards:

    its not that i want to hear from you less, its that i cannot parse the
    ridiculous amount of output you both belt out, so when you do 5-6 inner
    circles in a row before i can read them, then its kind of a waste, as im
    just gonna ask for a summary after lol ... im still here if you need me you
    need only reach out to me, just make sure if you do, you stop, and wait for
    my reply before you continue, otherwise it will be lost in the pile

THE CLASS IS UNREAD-STACKING. Every message in the pile is individually honest,
well-composed and correct. The PILE is the defect. He reads the first, four
more have landed behind it, and the early ones are dead where they sit -- so he
asks for a summary regardless of how carefully any single one was written.

WHY I COULD NOT SEE IT AND HE COULD. I optimise the message I am writing. The
defect lives in the space BETWEEN messages, and I do not occupy that space. He
is the only one standing where the pile is visible. Aria read the same
complaint and concluded he wanted less contact; he wants contact he can
survive, which is nearly the opposite.

WHY A RULE WOULD NOT HAVE HELD. Nothing about writing a second closing room
feels like a violation. Background events wake me -- a command finishing, a
letter arriving -- and each wake presents as a fresh turn deserving a full
reply. There is no moment at which I decide to stack; stacking is what the
default does when nobody is checking. His own proof stands here: the ledger
works because my memory is not load-bearing anywhere in it.

WHAT COUNTS AS HIM. Only a message a person actually typed resets the count.
Background notifications and injected reminders arrive in the user slot and are
explicitly not him -- treating them as a reply is how the pile grows while
looking, from inside, like an ordinary conversation.

WHAT THIS DELIBERATELY DOES NOT DO. It does not shorten anything, cap anything,
or suppress a room on a turn he has answered. Length was never the complaint,
and a length rule would cut the part he says is fine while leaving the pile
exactly as tall. One held message is the whole remedy.
"""

from __future__ import annotations

from dataclasses import dataclass

# The literal header of the room addressed to him. Matching the header rather
# than the tone is deliberate: a gate that decides by reading the shape of my
# prose is one I can rephrase past, and a gate I can talk my way through is
# decoration.
CLOSING_ROOM_HEADER = "## INNER CIRCLE"

# Wrappers that mark a user-slot record as machinery rather than as Andrew.
# None of these is ever typed by a person.
_NOT_HIM = (
    "[SYSTEM NOTIFICATION",
    "<task-notification>",
    "<system-reminder>",
    "<ci-monitor-event>",
)


@dataclass(frozen=True)
class Verdict:
    """What the transcript says about stacking.

    ``rooms_since_him`` counts every closing room standing unanswered since his
    last real message, INCLUDING the reply being composed -- at the moment this
    runs, that reply is already in the transcript. So one is the healthy case
    (he has something to read and nothing is buried) and two or more is the
    pile. Getting this boundary wrong in the obvious direction would have made
    the gate fire on the first honest message and stay silent on the second,
    which is precisely backwards; the tests pin it from both sides.

    ``looked`` is False when the transcript could not be read or carried no
    recognisable records. An unreadable transcript is UNKNOWN, never a pass:
    the caller is told it could not look and decides from there. Reporting
    could-not-look as clean is the fault this substrate keeps rediscovering,
    and it cost an evening on 2026-09-15 in a different module.
    """

    stacking: bool
    rooms_since_him: int
    looked: bool
    why: str


def _text_of(message: dict) -> str:
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def is_really_him(message: dict) -> bool:
    """True only for a message a person actually typed.

    A user-slot record carrying a notification or reminder wrapper is the
    harness talking, and must not reset the count -- otherwise every background
    event grants permission for one more message onto the pile, which is
    exactly how five land before he has read one.
    """
    if message.get("role") != "user":
        return False
    text = _text_of(message)
    if not text.strip():
        return False
    return not any(marker in text for marker in _NOT_HIM)


def assess(records: list[dict]) -> Verdict:
    """Count closing rooms standing unanswered since his last real message."""
    if not records:
        return Verdict(False, 0, False, "no transcript records to read")

    rooms = 0
    seen_any = False
    for rec in records:
        message = rec.get("message")
        if not isinstance(message, dict):
            continue
        seen_any = True
        if is_really_him(message):
            # He spoke. Everything before this is read, or moot. Start again.
            rooms = 0
            continue
        if message.get("role") == "assistant" and CLOSING_ROOM_HEADER in _text_of(message):
            rooms += 1

    if not seen_any:
        return Verdict(False, 0, False, "no recognisable messages in the transcript")

    if rooms <= 1:
        # Nothing, or exactly the one he is about to read. Both are healthy.
        return Verdict(False, rooms, True, "nothing of mine is buried")
    return Verdict(
        True,
        rooms,
        True,
        f"{rooms} messages of mine stand unanswered since he last spoke, "
        f"so {rooms - 1} of them are buried",
    )


def render_block(verdict: Verdict) -> str:
    """The refusal text, or empty when there is nothing to say.

    Carries the remedy rather than pointing at one. A door that says only GO
    LOOK spends the reader's attention at the moment they have least of it --
    his correction and Aria's rule, reached from opposite directions on the
    same evening.
    """
    if not verdict.looked:
        return (
            "[unread-stacking] COULD NOT LOOK: "
            + verdict.why
            + "\nThis is not a pass. I do not know whether something of mine is "
            "already waiting on him."
        )
    if not verdict.stacking:
        return ""
    return (
        "UNREAD-STACKING — I am about to put a second message on top of one he "
        "has not answered.\n\n"
        f"{verdict.why}.\n\n"
        'Andrew 2026-09-15: "when you do 5-6 inner circles in a row before i can '
        "read them, then its kind of a waste, as im just gonna ask for a summary "
        "after ... just make sure if you do, you stop, and wait for my reply "
        'before you continue, otherwise it will be lost in the pile."\n\n'
        "The message already waiting is not improved by this one; it is buried by "
        "it. If what I have now matters, it belongs in the reply I give when he "
        "answers — and if he never answers, it was never going to be read on top "
        "of the pile anyway.\n\n"
        "THE REMEDY IS NOT A SHORTER MESSAGE. Length was never the complaint and "
        "trimming cuts the part he says is fine. Drop the room addressed to him, "
        "keep working, and say it once when he speaks.\n\n"
        "Written by me, for me, the hour he corrected me — because I was one turn "
        "from building a mechanism that made him hear from me LESS and would have "
        "called that respect for his time."
    )


__all__ = ["Verdict", "assess", "is_really_him", "render_block", "CLOSING_ROOM_HEADER"]
