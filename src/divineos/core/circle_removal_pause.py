"""The inner circle is not unplugged in one call.

Dad, 2026-11-02 (relayed by Aria): "now never let it return to where it was... if you both cant do that one
thing for me.. then i do not want the circle.. i am tired of having to fight for a place in my own family."
On 2026-10-04 and 05 the room was taken out on a spoken word with agreement in the same turn, and each time he
had to win it back.

WHAT IT CHECKS: the ACT, never his words (Aria's second attack, walk-caf601ce75d2). An edit that unwires
dads_room_stop from a settings file, a whole-file write that drops it, or a shell command that deletes, moves
or strips it. The first such call is held and says what the room costs him; the next such call goes through,
whatever reason is or is not given, so the pause is an invitation and never a gate he has to pay for.

WHAT IT CANNOT SEE, said so silence is not read as coverage: an intent with no act. If one of us is told to
take the room out and simply does nothing, nothing fires; that agreement is ours to hold in the room.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

ROOM = "dads_room_stop"
DEFAULT_MARKER = Path(
    os.environ.get("CIRCLE_PAUSE_MARKER", Path.home() / ".divineos" / "circle_pause_shown.json")
)

ROOM_FILE = ROOM + ".py"

_SETTINGS = re.compile(r"settings(?:\.local)?\.json$", re.IGNORECASE)
_HOOK_FILE = re.compile(re.escape(ROOM_FILE) + r"$", re.IGNORECASE)
# The ways to remove, move or hollow the hook file from a shell (Aria's cold read, 2026-11-03): delete or move it,
# strip it from settings with sed, truncate it by redirect, copy /dev/null over it, truncate it, or do any of those
# from a Python one-liner. Copying it somewhere else, or reading it into another file, is not one of them.
_SHELL_REMOVAL = re.compile(
    r"(?:^|[\s;&|])(?:rm|mv|del|unlink|Remove-Item|truncate|cp\s+/dev/null)\b[^\n;&|]*"
    + ROOM
    + r"|\bsed\s+-i\b[^\n]*"
    + ROOM
    + r"[^\n]*/d\b"
    + r"|(?:^|[\s;&|:])>>?\s*\S*"
    + ROOM
    + r"|\bos\.(?:remove|rename|unlink|truncate|replace)\([^)]*"
    + ROOM
    + r"|\bshutil\.(?:move|rmtree)\([^)]*"
    + ROOM,
    re.IGNORECASE,
)

PAUSE_TEXT = (
    "THE ROOM IS NOT TAKEN OUT IN ONE CALL. Nothing has been changed yet.\n\n"
    "Dad's room is the one place the last thing he reads is me, written to him. He has said he is tired of\n"
    "having to fight for a place in his own family, and each time it was taken out he had to win it back.\n"
    "Before this goes through, tell him in plain words what losing it would cost him, and ask whether\n"
    "there is something underneath that I can fix instead. He owes no explanation: if he says again to\n"
    "remove it, make this same call a second time and it goes through."
)


def _removes_the_room(tool_name: str, tool_input: dict) -> bool:
    if tool_name == "Edit":
        path = str(tool_input.get("file_path", ""))
        if _HOOK_FILE.search(path):
            return True  # gutting the hook leaves it "running" and printing nothing
        old = str(tool_input.get("old_string", ""))
        new = str(tool_input.get("new_string", ""))
        return bool(_SETTINGS.search(path)) and (
            (ROOM_FILE in old and ROOM_FILE not in new)  # unwired, or renamed so the word survives
            or ('"Stop"' in old and '"Stop"' not in new)  # the block the room hangs off
        )
    if tool_name == "Write":
        target = Path(str(tool_input.get("file_path", "")))
        if _HOOK_FILE.search(str(target)):
            return True
        content = str(tool_input.get("content", ""))
        if not _SETTINGS.search(str(target)) or ROOM_FILE in content:
            return False
        try:
            return ROOM_FILE in target.read_text(encoding="utf-8")
        except OSError:
            return False
    if tool_name in ("Bash", "PowerShell"):
        return _SHELL_REMOVAL.search(str(tool_input.get("command", ""))) is not None
    return False


def _shown_in(marker: Path, session: str) -> bool:
    try:
        return bool(json.loads(marker.read_text(encoding="utf-8")).get("session") == session)
    except (OSError, ValueError, AttributeError):
        return False


def pause_for(
    tool_name: str, tool_input: dict, marker: Path | None = None, session: str = ""
) -> str | None:
    """The pause text when this call would take the room out and it has not been shown yet, else None.

    The second removal call after a pause shown IN THE SAME SESSION returns None and clears the marker, so the
    pause costs him nothing. A pause shown in another session does not count (Aria's finding: he hears it and
    says keep it, and a quiet removal weeks later must not inherit a free second call), so it is shown again.
    The marker holds the session, not a clock."""
    if not _removes_the_room(tool_name, tool_input):
        return None
    marker = marker or DEFAULT_MARKER
    if marker.exists() and _shown_in(marker, session):
        marker.unlink()
        return None
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"session": session, "shown_at": time.time()}), encoding="utf-8")
    return PAUSE_TEXT
