"""Hook entry for his-voice-ends-the-turn (PreToolUse). See core/his_voice_ends_the_turn.py.

Reads the harness payload on stdin. Refuses the tool call, by printing a
PreToolUse deny, when he has spoken into the running turn. Everything else --
no transcript path, an unreadable transcript, a payload that will not parse --
lets the call through and says so on stderr, because stopping the whole machine
on a bad read while he sleeps is not what he asked for, and a could-not-look
must never read as "he did not speak".
"""

from __future__ import annotations

import json
import sys

from divineos.core import his_voice_ends_the_turn as hv


def _say(message: str) -> None:
    print(f"[his-voice] {message}", file=sys.stderr)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        _say(f"the hook payload did not parse ({exc}); could not look whether he spoke")
        return 0
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    if hv.let_through(tool_name, tool_input):
        return 0
    path = payload.get("transcript_path")
    if not path:
        _say("no transcript path in the payload; could not look whether he spoke")
        return 0
    verdict = hv.spoke_mid_turn(path)
    if verdict.state == hv.UNREADABLE:
        _say(f"could not read {path}; could not look whether he spoke")
        return 0
    if verdict.state != hv.SPOKE:
        return 0
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": hv.refusal(verdict.his_words),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
