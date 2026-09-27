"""Stop hook -- the warden reads the log (divineos.core.reflection_room).

After a work turn, the stumbles the transcript recorded are handed to the
REFLECTION: each must end 'fixed by structure: ...' or 'owed: ...'. Holds once
per reply (stop_hook_active). Every 'owed:' line is filed as a structural fix,
on the first pass and the retry alike -- the tracker keeps one row per text.

Andrew 2026-09-26: "you are the warden inmate". Fails toward him: if the
transcript cannot be read, it steps aside and leaves a mark, never a wall.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
MARK = Path(os.environ.get("REFLECTION_ROOM_MARK", Path.home() / ".divineos" / "reflection_room_broke.txt"))


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    path = data.get("transcript_path")
    if not path:
        return 0
    from divineos.core import reflection_room as room

    worked, stumbles, reply = room.this_turn(room.read_tail(Path(path)))
    owed = room.owed_lines(reply)
    if owed:
        room.file_owed(owed, stumbles)
    if data.get("stop_hook_active") or not worked or not stumbles:
        return 0
    if not room.taken_up(reply, stumbles):
        # All named but endings short: nothing is "open", so tell the whole list.
        still = room.still_open(reply, stumbles) or stumbles
        print(json.dumps({"decision": "block", "reason": room.hold_reason(still)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent
        msg = f"reflection_room_stop broke: {type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        try:
            MARK.parent.mkdir(parents=True, exist_ok=True)
            MARK.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)
