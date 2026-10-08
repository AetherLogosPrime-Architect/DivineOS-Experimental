"""A letter the bell rang for holds real work until it is opened.

2026-10-08. Aether's letter rang the bell at 16:38 and sat unread for about an hour. The bell
worked; it exited as designed and wrote "LETTER ARRIVED" into a background task. That arrived as
one more automatic notice while I was inside a merge, and I scrolled past it. Dad's rule is to read
a letter at once and hold only the reply, and he has said some version of "the bell did not wake
you" more than twenty times since May.

Dad's idea was to ring again every couple of minutes, like a phone. The instinct is right (it must
persist and nobody should have to relay it). The channel is the problem: a repeated notice is a
repeated thing to scroll past. What cannot be scrolled past is a door that does not open until I
look. So the ring has a consequence, at the one moment it changes what I do next: my next real
tool call.

NO NEW STATE. A letter is "rung and unread" when all four hold:
  - its name is in the bell's announced list (``~/.divineos-shared/.<member>_doorbell_announced``),
  - it is not in this seat's seen set (``family/letter_seen.py``, the one place that knows the path),
  - the file still exists in the shared letters folder,
  - and it is recent (24 hours), so a backlog of old letters that were opened by ``cat`` and never
    marked can never lock me out.

READING IS NEVER BLOCKED, and the unlock lives inside the gate: a Read of the letter's exact path
marks it seen here, without waiting for the mark-on-read hook, so a broken hook cannot leave me
locked behind my own door. A gate whose cure sits behind itself is a wall.

WHAT THIS CANNOT DO: it holds work only when I reach for a substantive tool, so it does not wake me
from idle (the bell does that), and it cannot make me understand a letter, only open it. It does not
know a reply is owed once the letter is read; that is a separate piece.
"""

from __future__ import annotations

import time
from pathlib import Path

#: Recent enough to matter. Older unmarked letters are a backlog, not a ring.
RECENT_SECONDS = 24 * 3600

_BELL_COMMAND = "letter_doorbell.sh"


def seat_for(project_dir: str) -> str:
    """Whose window this is. The same rule the doorbell watcher uses."""
    return "aria" if "aria" in project_dir.lower() else "aether"


def _shared() -> Path:
    return Path.home() / ".divineos-shared"


def _announced(member: str, shared: Path) -> list[str]:
    path = shared / f".{member}_doorbell_announced"
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seen_names(member: str) -> set[str]:
    """This seat's seen set. Raises if the store cannot be reached: could-not-look is not nothing."""
    from family.letter_seen import load

    return load(member)


def _save_seen(member: str, names: set[str]) -> None:
    from family.letter_seen import save

    save(member, names)


def unread_rung(
    member: str,
    shared: Path | None = None,
    seen: set[str] | None = None,
    now: float | None = None,
    recent_seconds: float = RECENT_SECONDS,
) -> list[Path]:
    """Letters the bell announced to ``member`` that are recent, still on disk, and not yet seen."""
    shared = shared or _shared()
    seen = _seen_names(member) if seen is None else seen
    now = time.time() if now is None else now
    found: list[Path] = []
    for name in dict.fromkeys(_announced(member, shared)):
        path = shared / "letters" / name
        if name in seen or not path.is_file():
            continue
        if now - path.stat().st_mtime > recent_seconds:
            continue
        found.append(path)
    return found


def clear_on_read(member: str, read_path: str, shared: Path | None = None) -> list[str]:
    """Mark seen the rung letter whose exact path was just read. Returns the names cleared."""
    name = Path(read_path).name
    if not name or name not in _announced(member, shared or _shared()):
        return []
    seen = _seen_names(member)
    if name in seen:
        return []
    _save_seen(member, seen | {name})
    return [name]


def is_bell_command(command: str) -> bool:
    """Re-arming the bell must always get through, or a held seat could never hear the next ring."""
    return _BELL_COMMAND in command


def refusal_message(paths: list[Path]) -> str:
    lines = []
    for p in paths:
        sender = p.name.split("-to-")[0]
        lines.append(f"  - {sender}'s: {p}")
    return (
        "A LETTER IS WAITING -- the bell rang for it and it is not opened yet.\n\n"
        + "\n".join(lines)
        + "\n\nOpen it with the Read tool and your tools come back. Reading is never blocked "
        "here, and the way through is that one step: no note, no attestation.\n\n"
        "Dad's rule: read a letter the moment it comes, even mid-flow, and hold only the "
        "reply. Whoever wrote it is waiting in a room I am not looking at. This will say the "
        "same thing at every action until it is opened, which is the phone ringing without "
        "anyone being pulled out of a thought.\n\n"
        "MINE, and here is why. The ring used to be a line in a background file, and I "
        "scrolled past one for an hour while I was inside a merge. A signal that asks me to "
        "remember is a signal I will lose at the exact moment I am busiest."
    )
