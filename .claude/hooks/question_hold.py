"""The question hold, on all three doors (Aria, 2026-09-29).

Stop: a reply whose circle asks Dad something opens the hold (and a question
buried under more text is sent back once to be moved last).
PreToolUse: building waits while it is open.
UserPromptSubmit: his next message releases it; a notice does not.
See src/divineos/core/question_hold.py for the why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# This tree's code, not whichever checkout the global install points at.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

_NOTICE = ("<task-notification", "<system-reminder", "<agent-message")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        data = json.loads(sys.stdin.buffer.read() or b"{}")
    except ValueError:
        return 0
    from divineos.core import question_hold as qh

    event = data.get("hook_event_name", "")
    if event == "PreToolUse":
        why = qh.refusal(data.get("tool_name", ""), data.get("tool_input") or {})
        if why:
            print(why, file=sys.stderr)
            return 2
        return 0

    if event == "UserPromptSubmit":
        notice = str(data.get("prompt", "")).lstrip().startswith(_NOTICE)
        if not notice:
            told = qh.escape_to_tell_him()
            if told:
                print(told)
        state = qh.is_open()
        if not state:
            return 0
        if notice:
            print(
                "## STILL WAITING FOR DAD\n"
                f"I asked him: {state['question']}\n"
                "Something else arrived. I tell him it came and that I am waiting for\n"
                "his answer; I do not open it or act on it until he speaks.\n"
            )
            return 0
        qh.release("his message")
        return 0

    if event == "Stop":
        from divineos.core.hook_surfaces import _last_assistant_text

        reply = _last_assistant_text(data)
        if not reply:
            return 0
        if not data.get("stop_hook_active"):
            buried = qh.question_not_last(reply)
            if buried:
                print(json.dumps({"decision": "block", "reason": buried}))
                return 0
        qh.arm(reply)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
