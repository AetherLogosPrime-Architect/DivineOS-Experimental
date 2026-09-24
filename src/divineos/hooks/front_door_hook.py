"""Hook entry for the front door. See core/front_door.py.

    keep    -- UserPromptSubmit: keep what arrived, before anything else runs.
    settle  -- PreToolUse and Stop: confirm or withdraw what the transcript now holds.

Reads the harness payload on stdin. Always exits 0: the door records its own
failures as could-not-file and on stderr, and never costs him his prompt, a
tool call, or his reply.
"""

from __future__ import annotations

import json
import sys

from divineos.core import front_door
from divineos.core.sibling_audit_rounds import this_seat


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else ""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        print(f"[front-door] the hook payload did not parse: {exc}", file=sys.stderr)
        return 0
    seat = this_seat() or "unknown-seat"
    if action == "keep":
        front_door.keep(payload, seat)
    elif action == "settle":
        path = payload.get("transcript_path")
        if path:
            front_door.settle(path, seat)
        else:
            print(
                "[front-door] no transcript path in the payload; nothing settled", file=sys.stderr
            )
    else:
        print(f"[front-door] unknown action {action!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
