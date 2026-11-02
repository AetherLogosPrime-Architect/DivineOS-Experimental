"""Stop hook: a reply that ends on "I will do X next" is held once and told to do X.

Dad, 2026-10-22: words must be followed by action when he is not here, or I sit in stasis and nothing is
completed. The judgement lives in core/stall_on_promise.py so a test can argue with it; this is the thin door.

One hold per reply (stop_hook_active), so it can never loop. If it breaks it says so on stderr and in a mark
file; it never passes quietly and never blocks on its own failure.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
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
    last = ""
    for rec in records[start:]:
        if rec.get("type") != "assistant":
            continue
        for c in (rec.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                last = c["text"]
    return last


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
