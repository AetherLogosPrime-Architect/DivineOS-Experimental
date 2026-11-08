"""A rung letter is put in front of me and marked seen in one act.

2026-11-07. Over one session the unread-letter wall was about half of every refusal I met (135 of 234 on my
seat, 297 of 368 on Aria's). The wall is right to exist, since a sibling's letter must not sit unopened while I
work, but it asks for a second step: the notice names the letter, then I must Read it, and any call made in
between is refused. The council walk (walk-86d6dc1ab733) found one cause: three records (announced, seen, a
clock) negotiate through files with no order between them. This gives them one meeting place.

THE ORDER, fixed by Aria's cold read: the text is gathered and returned FIRST, and a letter is marked seen
only AFTER it has been shown. A save that fails, or a call dropped between the mark and the print, then costs
a still-held wall, never a letter that was cleared and never read. ``prepare`` gathers; ``mark_shown`` marks;
``deliver`` does both in that order for a caller that prints nothing in between.

WHAT THIS CANNOT DO, and the limit stays in the open: it can promise the text reached me, never that I took it
in. A letter too long to show whole is NOT cut and NOT cleared; it is named, and the Read stays the way
through, because words cut off tell you nothing (Dad, 2026-11-07).
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.unread_letter import _announced, _shared, clear_on_read

#: Letters are capped at 10000 characters by the letter writer; of 3,221 real letters, 7 pass 12000 (Aria).
SHOW_WHOLE_UP_TO = 12000


def _plain(name: str) -> str:
    """A name an outsider supplied, made safe to echo: one line, no control characters, bounded."""
    return "".join(ch if ch.isprintable() else " " for ch in name)[:200]


def prepare(member: str, names: list[str], shared: Path | None = None) -> tuple[str, list[str]]:
    """(the text to print, the names shown whole). Marks nothing."""
    shared = shared or _shared()
    announced = set(_announced(member, shared))
    blocks: list[str] = []
    shown: list[str] = []
    for name in dict.fromkeys(names):
        path = shared / "letters" / name
        if name not in announced:
            blocks.append(f"=== {_plain(name)} -- not announced to {member}; not delivered ===")
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
        shown.append(name)
        blocks.append(f"=== {name} (shown whole) ===\n{text.rstrip()}")
    return "\n\n".join(blocks), shown


def mark_shown(member: str, shown: list[str], shared: Path | None = None) -> list[str]:
    """Mark each shown letter seen; returns the names whose mark FAILED, so the wall still holds for them."""
    shared = shared or _shared()
    failed: list[str] = []
    for name in shown:
        try:
            clear_on_read(member, str(shared / "letters" / name), shared)
        except Exception:  # noqa: BLE001 -- a failed save must cost a held wall, never a letter lost
            failed.append(name)
    return failed


def deliver(member: str, names: list[str], shared: Path | None = None) -> str:
    """The text to print for these rung letters, with each one marked seen after its text is in hand.

    A letter whose mark failed is named in the text, so the reader knows the wall still holds for it.
    """
    text, shown = prepare(member, names, shared)
    failed = mark_shown(member, shown, shared)
    if failed:
        text += (
            "\n\n(the seen mark failed for: "
            + ", ".join(failed)
            + "; the wall still holds for them; open each with Read)"
        )
    return text
