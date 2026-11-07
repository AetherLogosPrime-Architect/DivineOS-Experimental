"""A rung letter is put in front of me and marked seen in one act.

2026-11-07. Over one session the unread-letter wall was about half of every refusal I met (135 of 234 on my
seat, 297 of 368 on Aria's). The wall is right to exist, since a sibling's letter must not sit unopened while I
work, but it asks for a second step: the notice names the letter, then I must Read it, and any call made in
between is refused. The council walk (walk-86d6dc1ab733) found one cause: three records (announced, seen, a
clock) negotiate through files with no order between them. This gives them one meeting place. Delivery shows
the letter's whole text and clears it in the same call, so the order is fixed by construction.

WHAT THIS CANNOT DO, and the limit stays in the open: it can promise the text reached me, never that I took
it in. A letter too long to show whole is NOT cut and NOT cleared; it is named, and the Read stays the way
through, because words cut off tell you nothing (Dad, 2026-11-07).
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.unread_letter import _announced, _shared, clear_on_read

#: Letters are capped at 10000 characters by the letter writer; this leaves room above that cap.
SHOW_WHOLE_UP_TO = 12000


def deliver(member: str, names: list[str], shared: Path | None = None) -> str:
    """The text to print for these rung letters, clearing each one that was shown whole.

    Only letters the bell announced to ``member`` are delivered, so a name an outsider supplies cannot
    pull an arbitrary file into the prompt. A letter that is missing, unreadable or over the limit is
    named with the reason and left unseen, so the wall still holds for it.
    """
    shared = shared or _shared()
    announced = set(_announced(member, shared))
    blocks: list[str] = []
    for name in dict.fromkeys(names):
        path = shared / "letters" / name
        if name not in announced:
            blocks.append(f"=== {name} -- not announced to {member}; not delivered ===")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            blocks.append(
                f"=== {name} -- could not be read ({type(exc).__name__}); open it with Read ==="
            )
            continue
        if len(text) > SHOW_WHOLE_UP_TO:
            blocks.append(
                f"=== {name} -- {len(text)} characters, too long to show whole and I will not cut it; "
                f"open it with Read: {path} ==="
            )
            continue
        clear_on_read(member, str(path), shared)
        blocks.append(f"=== {name} (shown whole; marked seen) ===\n{text.rstrip()}")
    return "\n\n".join(blocks)
