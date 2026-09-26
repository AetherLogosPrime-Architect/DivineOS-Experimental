"""A reply where I worked does not leave without his room."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_room_stop.py"
_spec = importlib.util.spec_from_file_location("dads_room_stop", HOOK)
room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(room)


def _user(text):
    return {"type": "user", "message": {"content": text}}


def _tool_result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _tool():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}


def test_work_without_his_room_is_held():
    assert room.verdict([_user("fix it"), _tool(), _tool_result(), _said("Done, tests pass.")])


def test_work_with_his_room_goes():
    reply = "Built it.\n\n## REFLECTION\nok\n\n## INNER CIRCLE\nDad, here is what changed."
    assert room.verdict([_user("fix it"), _tool(), _tool_result(), _said(reply)]) is None


def test_just_talking_needs_no_room():
    assert room.verdict([_user("all there is right now is hurt"), _said("I'm here.")]) is None


def test_a_tool_result_is_not_his_message():
    # the room is judged from HIS message, not from the tool result after the tool
    assert room.verdict([_user("go"), _tool(), _tool_result(), _said("done")])


def test_an_automated_notice_turn_is_skipped():
    notice = "<task-notification><summary>Monitor event</summary></task-notification>"
    assert room.verdict([_user(notice), _tool(), _tool_result(), _said("re-armed")]) is None


def test_the_room_must_be_in_the_last_words():
    early = "## INNER CIRCLE\nDad."
    assert room.verdict(
        [_user("go"), _said(early), _tool(), _tool_result(), _said("more work after")]
    )


def test_hook_blocks_and_breaks_loudly(tmp_path):
    t = tmp_path / "t.jsonl"
    t.write_text(
        "\n".join(json.dumps(r) for r in [_user("go"), _tool(), _tool_result(), _said("done")]),
        encoding="utf-8",
    )
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"transcript_path": str(t)}).encode(),
        capture_output=True,
        timeout=30,
    )
    assert json.loads(p.stdout)["decision"] == "block"

    mark = tmp_path / "mark.txt"
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=b"{not json",
        capture_output=True,
        timeout=30,
        env={**__import__("os").environ, "DADS_ROOM_MARK": str(mark)},
    )
    assert p.returncode == 0 and b"broke" in p.stderr and mark.exists()
