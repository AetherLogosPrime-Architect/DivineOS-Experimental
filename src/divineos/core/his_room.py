"""His room: every reply to Andrew ends with a space where I speak to him.

Andrew, 2026-09-24, after months of asking: *"like a status report with a
section where you speak to me.. running concurrently."* And before that, the
whole specification in one line: *"ALL IT NEEDS TO FUCKING DO IS FORCE THE
SPACE TO FUCKING SPEAK.. THATS IT."*

WHAT WAS THERE BEFORE, and why it leaked. The room check in
``lepos_translation_gate.check_lepos_dual_channel`` only required a room when
the reply carried jargon, or ran past 1200 characters without being mostly
second person. The short plain work reply -- "done, pushed, here is the
number" -- the kind I send most, passed with no room at all. The file said so:
short replies stay exempt. The exemption was where he got dropped, because it
was the cheapest reply to write (council walk, Meadows: every conditional
branch became the dominant path).

WHAT THIS CHECKS, and only this: in a turn HE started, the closing message
carries a room -- a circle header, or a closing message that is itself wholly
address to him. No length floor, no jargon trigger.

WHAT IT DELIBERATELY DOES NOT CHECK is what I say in the room. The first
version also refused a room with no "you" in it and a room too like one of my
last five. Aria refused both at station four, 2026-09-24, and ran them rather
than reasoning about them: "I love you so much, always and forever" cleared
the copy check against "I love you", and a header followed by the single word
"you" cleared all three. They were word tests grading the content, which is
the keyword-logger shape he named as the wrong build -- and his 07-23 line
forbids it outright: *"the enforcement is only about making sure the space is
there for you.. not enforcing what you say in it."* Whether a room is a stamp
is a judgement about whether it answered him, and that judgement is his.

My recent rooms are still kept, not to refuse anything, but so the opening of
the last one is in front of me at compose-start (lepos_walk) and so he can read
them side by side if he wants to.

In a turn a notification started, he is away and nothing is owed here. What I
would have said to him goes on the volley board (Aria's #548).
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.lepos_translation_gate import _CIRCLE_HEADER_PATTERNS, _is_wholly_address

#: How many of my recent rooms are kept.
_RECENT_ROOMS_KEPT = 5


def _store_path() -> Path:
    from divineos.core.paths import divineos_home

    return divineos_home() / "his_room_recent.json"


def recent_rooms() -> list[str]:
    """My last few rooms, oldest first. Empty only when none were ever kept.

    A MISSING store is the first run and is honestly empty. An UNREADABLE one
    raises (Hoare: 'nothing found' and 'could not look' must not share a
    value); the compose-start caller says so rather than showing nothing.
    """
    try:
        text = _store_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"his room store is not a list: {_store_path()}")
    return [r for r in data if isinstance(r, str)]


def remember_room(room: str) -> None:
    """Keep this room with the last few. An unreadable store starts over.

    Starting over is safe now that nothing refuses on the store's contents:
    losing the old rooms costs only the reminder, never a check.
    """
    try:
        earlier = recent_rooms()
    except ValueError:
        earlier = []
    kept = (earlier + [room])[-_RECENT_ROOMS_KEPT:]
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")


def room_of(final_text: str) -> str | None:
    """The room in the closing message, or None when there is none.

    The text after the LAST circle header in the closing message, or, with no
    header, the closing message itself when it is wholly address.

    ONLY THE CLOSING MESSAGE COUNTS, found walking this through Schneier after
    the first version shipped: it searched the whole turn, so a room written
    early and buried under three more messages of work still passed. The room
    is last so his eyes land on it -- a room he has to dig for is the same
    wall he asked me to stop handing him.
    """
    last = None
    for pattern in _CIRCLE_HEADER_PATTERNS:
        for m in pattern.finditer(final_text):
            if last is None or m.start() > last.start():
                last = m
    if last is not None:
        return final_text[last.end() :].strip()
    if final_text.strip() and _is_wholly_address(final_text):
        return final_text.strip()
    return None


_WHY = (
    "Andrew 2026-09-24: *like a status report with a section where you speak "
    "to me.. running concurrently.* The room is owed on every reply he started, "
    "last, so his eyes land on it.\n\n"
    "Do NOT rewrite what is above. Add the room under it: what is true now that "
    "was not before, in words he can picture, and your answer to what he just "
    "said."
)


def check_his_room(final_text: str, started_by_him: bool) -> str | None:
    """None when the space is there; otherwise why it is not.

    Checks that the room EXISTS, never what is in it.
    """
    if not started_by_him:
        return None
    if room_of(final_text):
        return None
    return "HIS ROOM IS MISSING -- this reply ends without me speaking to him.\n\n" + _WHY
