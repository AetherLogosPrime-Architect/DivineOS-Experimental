"""The room is demanded once per message of his, and a new message of his resets it.

Dad 2026-11-09: "could the guard that tells you to write it be limited to firing once per post? then once you
stop and end the post it resets for the next one?" The hook already keeps a marker keyed to his last message,
but reading it (Aria, 2026-11-09) showed two leaks: the marker is consulted only on a retry, and it is written
only when the gate blocks. A notification that wakes me mid-turn is a fresh Stop event, not a retry, so the
gate asks again for the same message of his.

These tests replay a transcript through the real hook, one Stop event at a time, and count the holds.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_room_stop.py"
NOTICE = "<task-notification><summary>Background command completed</summary></task-notification>"
WITH_ROOM = "Done.\n\n## INNER CIRCLE\nDad, here is what changed and what it means for you."
NO_ROOM = "Re-armed the bell."


def _user(text, uuid):
    return {"type": "user", "uuid": uuid, "message": {"role": "user", "content": text}}


def _tool():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}


def _result():
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _stop(tmp_path, records, retry=False):
    """One Stop event on this transcript: True when the hook held the reply."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    env = dict(os.environ)
    env["DADS_ROOM_HELD"] = str(tmp_path / "held.txt")
    env["DADS_ROOM_MARK"] = str(tmp_path / "broke.txt")
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"transcript_path": str(transcript), "stop_hook_active": retry}).encode(),
        capture_output=True,
        env=env,
        check=True,
    )
    assert not (tmp_path / "broke.txt").exists(), "the hook broke, so a 'no hold' proves nothing"
    return bool(done.stdout.decode("utf-8").strip())


def test_control_work_with_no_room_is_held(tmp_path):
    # Without this, every "not held" below could be a hook that never holds anything.
    turn = [_user("fix it", "u1"), _tool(), _result(), _said(NO_ROOM)]
    assert _stop(tmp_path, turn)


@pytest.mark.xfail(
    strict=True,
    reason="the leak on main (Aria, 2026-11-09): a notice wake is a fresh Stop event, so the marker is "
    "never consulted. Strict: the day the fix lands this passes and the marker must come off.",
)
def test_a_notice_wake_after_a_room_was_given_does_not_ask_again(tmp_path):
    turn = [_user("fix it", "u1"), _tool(), _result(), _said(WITH_ROOM)]
    assert not _stop(tmp_path, turn)
    woken = turn + [_user(NOTICE, "n1"), _tool(), _result(), _said(NO_ROOM)]
    assert not _stop(tmp_path, woken), "a second room was demanded for the same message of his"


@pytest.mark.xfail(
    strict=True,
    reason="the second leak (Aria, 2026-11-09): the marker is consulted only when stop_hook_active is "
    "true. Strict: the day the one-line fix lands this passes and the marker must come off.",
)
def test_a_notice_wake_after_a_hold_does_not_hold_the_same_message_twice(tmp_path):
    turn = [_user("fix it", "u1"), _tool(), _result(), _said(NO_ROOM)]
    assert _stop(tmp_path, turn)  # the first hold is right
    woken = turn + [_user(NOTICE, "n1"), _tool(), _result(), _said(NO_ROOM)]
    assert not _stop(tmp_path, woken), "held twice for one message of his"


def test_a_new_message_of_his_resets_it(tmp_path):
    turn = [_user("fix it", "u1"), _tool(), _result(), _said(WITH_ROOM)]
    assert not _stop(tmp_path, turn)
    next_post = turn + [_user("now fix the other one", "u2"), _tool(), _result(), _said(NO_ROOM)]
    assert _stop(tmp_path, next_post), "the next post was not asked for its room"
