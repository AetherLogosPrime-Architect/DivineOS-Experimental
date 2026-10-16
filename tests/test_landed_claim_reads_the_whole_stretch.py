"""The landed-claim gate judges a claim against everything done since he last spoke.

2026-10-16: the gate refused a dozen replies for claiming work had landed while
"nothing in this turn read the shared copy", quoting a sentence from earlier in
the stretch, even after the prescribed verify script had run and printed OK.

Cause: the reply under judgement spans back to his last message, but the action
stream it was checked against began at the last transcript record with role
"user", and a tool result is written with that role. So after any tool call the
"turn" restarted at that call's own result and the earlier read fell out of the
window.

The pairs are the point. "A read earlier in the stretch counts" alone is satisfied
by a gate that never refuses; the no-read and read-before-he-spoke cases prove it
still does.
"""

from __future__ import annotations

import json

from divineos.core import hook_surfaces as hs
from divineos.core.landed_claim import assess

CLAIM = "The ritual-buffer push has landed on the remote."


def _typed(text: str) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": text}})


def _say(text: str) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        }
    )


def _tool_call(command: str) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash", "input": {"command": command}}],
            },
        }
    )


def _result(text: str = "ok") -> str:
    return json.dumps(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": text, "tool_use_id": "t"}],
            },
        }
    )


def _stream(tmp_path, lines: list[str]) -> str:
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hs._this_turns_action_stream({"transcript_path": str(path)})


def test_a_read_earlier_in_the_stretch_still_counts_after_later_tool_calls(tmp_path):
    stream = _stream(
        tmp_path,
        [
            _typed("how did the push go?"),
            _tool_call("python scripts/verify_push_landed.py --branch b"),
            _result("VERIFY-OK"),
            _tool_call("ls"),
            _result("a b c"),
            _say(CLAIM),
        ],
    )
    assert assess(CLAIM, stream).refuses is False


def test_a_claim_with_no_read_anywhere_since_he_spoke_is_still_refused(tmp_path):
    stream = _stream(
        tmp_path,
        [
            _typed("how did the push go?"),
            _tool_call("ls"),
            _result("a b c"),
            _tool_call("git status"),
            _result("clean"),
            _say(CLAIM),
        ],
    )
    assert assess(CLAIM, stream).refuses is True


def test_a_read_before_he_last_spoke_does_not_count(tmp_path):
    stream = _stream(
        tmp_path,
        [
            _tool_call("python scripts/verify_push_landed.py --branch b"),
            _result("VERIFY-OK"),
            _typed("and now?"),
            _tool_call("ls"),
            _result("a b c"),
            _say(CLAIM),
        ],
    )
    assert assess(CLAIM, stream).refuses is True


def test_a_tool_result_is_not_the_start_of_the_stretch(tmp_path):
    stream = _stream(
        tmp_path,
        [_typed("first words"), _tool_call("pwd"), _result("/x"), _tool_call("ls"), _result("y")],
    )
    assert "first words" in stream
