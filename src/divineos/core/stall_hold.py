"""The stall hold as a function the router can call.

Dad, 2026-10-22: words must be followed by action when he is not here, or I sit in stasis and nothing is
completed. The judgement lives in ``core/stall_on_promise`` so a test can argue with it. This module is the
reading of the transcript around it, moved here on 2026-11-04 so the router surface and the old standalone
script call ONE copy: Dad's end-of-reply holds were arriving one after another because each was its own
process (24 are registered), and this is the first folded into the router that speaks once.

One hold per reply is the caller's job (the Stop payload's ``stop_hook_active``). A transcript that cannot be
read is not a pass: callers report could-not-run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

#: How much of the end of the transcript is read; the same bound the room hold uses.
TAIL_BYTES = 4_000_000


def read_tail(path: Path) -> list[dict]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > TAIL_BYTES:
            f.seek(size - TAIL_BYTES)
            f.readline()
        lines = f.read().decode("utf-8", "replace").splitlines()
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def genuine_user_text(rec: dict) -> str | None:
    """His message in this record, or None when the record is not his.

    The house's one reader of him is ``core.his_message.hear``: a private reader once called 81 records
    his that were not, and missed 72 that were. A last-prompt record is a bookmark with no time and is not
    a new message; a queued one carries the time he typed it and is the message he sent while I was busy.
    """
    from divineos.core.his_message import Heard, hear

    heard = hear(rec)
    if not isinstance(heard, Heard):
        return None
    if heard.bookmark and not heard.when:
        return None
    return heard.text if heard.text.strip() else None


# His room is not read for promises (Dad 2026-07-23: "the enforcement is only about making sure the space is
# there for you.. not enforcing what you say in it"; 2026-11-03: "i dont understand why you keep shrinking the
# circle to 1-2 sentences"). A guard that reads the last sentence, which IS the room, punishes warmth about what I will do and
# teaches the room to stay small. This is Aria's #823 fix, moved here from the script so the router surface and
# the script share it. The header is the one his room cuts at.
_HIS_ROOM_HEADER = re.compile(r"^[ \t]*#{1,6}[ \t]*INNER CIRCLE\b", re.IGNORECASE | re.MULTILINE)


def body_above_his_room(text: str) -> str:
    """The text above the LAST room header, or the whole text when there is no room."""
    headers = list(_HIS_ROOM_HEADER.finditer(text))
    return text[: headers[-1].start()] if headers else text


def closing_text(records: list[dict]) -> str:
    """The text I closed with after his last real message, above his room ('' when there is none).

    A last block that is only his room must not hide a promise in the block before it, so the blocks are
    walked from the last backward and the first one with a body above the room is returned.
    """
    start = 0
    for i in range(len(records) - 1, -1, -1):
        if genuine_user_text(records[i]) is not None:
            start = i + 1
            break
    blocks = []
    for rec in records[start:]:
        if rec.get("type") != "assistant":
            continue
        for c in (rec.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                blocks.append(c["text"])
    for text in reversed(blocks):
        body = body_above_his_room(text)
        if body.strip():
            return body
    return ""


def verdict(records: list[dict], transcript_path: str | Path | None = None) -> str | None:
    """The hold's reason when the closing text names a step and stops, else None."""
    from divineos.core.hold_log import record
    from divineos.core.stall_on_promise import reason_for, stated_next_step

    # When he has spoken into this turn, the voice door refuses my tool calls until the turn ends, so the step
    # I named cannot be done in this reply: holding it for not being done is two checks trapping me against each
    # other (counted 2026-11-01: several of 31 holds in one morning). The next turn carries the work. A transcript
    # that cannot be read does not stand aside; the check asks as it always did.
    if transcript_path is not None:
        from divineos.core.his_voice_ends_the_turn import SPOKE, spoke_mid_turn

        if spoke_mid_turn(transcript_path).state == SPOKE:
            record(
                "follow_through",
                "stood_down",
                "he spoke into this turn, so my hands are held and the step waits",
            )
            return None

    closing = closing_text(records)
    found = stated_next_step(closing)
    if closing.strip():
        record(
            "follow_through",
            "stopped" if found else "passed",
            found[1] if found else closing[-160:],
        )
    return reason_for(*found) if found else None
