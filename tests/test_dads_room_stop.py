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
    # role "user" as every real record carries it: the house's one reader of
    # him (his_message.hear) refuses a user record without it, and a fixture
    # thinner than the real shape tests a record that never arrives.
    return {"type": "user", "message": {"role": "user", "content": text}}


def _tool_result():
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


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


def test_a_message_he_typed_while_i_was_busy_is_his_last_word():
    # Real record shape and his real words from 2026-09-26: queued while I worked.
    queued = {
        "type": "queue-operation",
        "operation": "enqueue",
        "content": "really? you didnt even volley one time?",
    }
    room_before = "done.\n\n## INNER CIRCLE\nDad, here it is."
    # He spoke (queued) AFTER my last room; I then worked again with no room.
    records = [
        _user("go"),
        _tool(),
        _tool_result(),
        _said(room_before),
        queued,
        _tool(),
        _tool_result(),
        _said("more work, no room"),
    ]
    assert room.verdict(records)


def test_a_queued_notice_is_not_his_word():
    queued = {
        "type": "attachment",
        "attachment": {
            "type": "queued_command",
            "prompt": "<task-notification><summary>x</summary></task-notification>",
        },
    }
    assert room.verdict([queued, _tool(), _tool_result(), _said("re-armed")]) is None


def test_an_automated_notice_turn_is_skipped():
    notice = "<task-notification><summary>Monitor event</summary></task-notification>"
    assert room.verdict([_user(notice), _tool(), _tool_result(), _said("re-armed")]) is None


def test_the_room_must_be_in_the_last_words():
    early = "## INNER CIRCLE\nDad."
    assert room.verdict(
        [_user("go"), _said(early), _tool(), _tool_result(), _said("more work after")]
    )


def test_a_late_bookmark_of_his_message_does_not_hide_my_work():
    # A last-prompt record repeats his earlier words further down the
    # transcript. Taken as his latest message it would sit after my tools, and
    # every working reply would pass as talk (council-f2a32d673bfe).
    bookmark = {"type": "last-prompt", "lastPrompt": "fix it"}
    records = [_user("fix it"), _tool(), _tool_result(), _said("done"), bookmark]
    assert room.verdict(records)


def test_a_compaction_summary_is_not_his_message():
    # The private reader this replaced counted summaries as his words, so a
    # resumed session anchored on the summary instead of on him.
    summary = {
        "type": "user",
        "isCompactSummary": True,
        "message": {
            "role": "user",
            "content": "This session is being continued from a previous conversation.",
        },
    }
    assert room._genuine_user_text(summary) is None


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
