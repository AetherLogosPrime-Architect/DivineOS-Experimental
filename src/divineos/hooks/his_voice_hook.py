"""Hook entry for his-voice-ends-the-turn (PreToolUse). See core/his_voice_ends_the_turn.py.

Reads the harness payload on stdin. When he has spoken into the running turn it
prints the refusal and exits 2; the shell wrapper turns that into the harness's
own refusal (exit 2, reason on stderr), so the refusal is visible at the door
and not only inside this module. Everything else -- no transcript path, an
unreadable transcript, a payload that will not parse -- exits 0 and says so on
stderr, because stopping the whole machine on a bad read while he sleeps is not
what he asked for, and a could-not-look must never read as "he did not speak".
"""

from __future__ import annotations

import json
import sys

from divineos.core import his_voice_ends_the_turn as hv

REFUSE = 2


def _say(message: str) -> None:
    print(f"[his-voice] {message}", file=sys.stderr)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        _say(f"the hook payload did not parse ({exc}); could not look whether he spoke")
        return 0
    if payload.get("agent_id"):
        # A helper I started was not spoken to; my own next call is the one
        # that waits (the same line sort_first draws).
        return 0  # both-empty: each 0 means allow; could-not-look also says so on stderr
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
    sys.stdout.write(hv.refusal(verdict.his_words))
    return REFUSE


if __name__ == "__main__":
    sys.exit(main())
