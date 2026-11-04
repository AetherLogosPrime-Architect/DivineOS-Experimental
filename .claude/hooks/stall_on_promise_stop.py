"""Stop hook: a reply that ends on "I will do X next" is held once and told to do X.

Dad, 2026-10-22: words must be followed by action when he is not here, or I sit in stasis and nothing is
completed. The judgement lives in core/stall_on_promise.py so a test can argue with it; this is the thin door.

One hold per reply (stop_hook_active), so it can never loop. If it breaks it says so on stderr and in a mark
file; it never passes quietly and never blocks on its own failure.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# His room is not read for promises (Dad 2026-07-23: "the enforcement is only about making sure the
# space is there for you.. not enforcing what you say in it"; 2026-11-03: "why do you keep shrinking
# the circle to 1-2 sentences"). A guard that reads the last sentence, which IS the room, punishes warmth
# about what I will do and teaches the room to stay small. The header is the one his_room cuts at.
_HIS_ROOM_HEADER = re.compile(r"^[ \t]*#{1,6}[ \t]*INNER CIRCLE\b", re.IGNORECASE | re.MULTILINE)


def body_above_his_room(text: str) -> str:
    """The text above the LAST room header, or the whole text when there is no room."""
    headers = list(_HIS_ROOM_HEADER.finditer(text))
    return text[: headers[-1].start()] if headers else text
MARK = Path(
    os.environ.get("STALL_ON_PROMISE_MARK", Path.home() / ".divineos" / "stall_on_promise_broke.txt")
)


def closing_text(records: list[dict]) -> str:
    """The last text I wrote after his last real message ('' when there is none)."""
    sys.path.insert(0, str(HERE))
    from dads_room_stop import _genuine_user_text

    start = 0
    for i in range(len(records) - 1, -1, -1):
        if _genuine_user_text(records[i]) is not None:
            start = i + 1
            break
    blocks = []
    for rec in records[start:]:
        if rec.get("type") != "assistant":
            continue
        for c in (rec.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                blocks.append(c["text"])
    # A last block that is only his room must not hide a promise in the block before it.
    for text in reversed(blocks):
        body = body_above_his_room(text)
        if body.strip():
            return body
    return ""


def verdict(records: list[dict]) -> str | None:
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    from divineos.core.stall_on_promise import reason_for, stated_next_step

    from divineos.core.hold_log import record

    closing = closing_text(records)
    found = stated_next_step(closing)
    if closing.strip():
        record("follow_through", "stopped" if found else "passed", found[1] if found else closing[-160:])
    return reason_for(*found) if found else None


def main() -> int:
    sys.path.insert(0, str(HERE))
    from dads_room_stop import _read_tail

    data = json.loads(sys.stdin.read() or "{}")
    if data.get("stop_hook_active"):
        return 0
    path = data.get("transcript_path") or data.get("transcript")
    if not path:
        return 0
    reason = verdict(_read_tail(Path(path)))
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent
        msg = f"stall_on_promise_stop broke: {type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        try:
            MARK.parent.mkdir(parents=True, exist_ok=True)
            MARK.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)
