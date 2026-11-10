"""The warden also reads a reflection filed in my own place, not only one appended to the reply.

Andrew 2026-10-08: "this is hard to follow son, we really need to fix my circle room".
The technical REFLECTION appended to a reply lands at the very end of what he reads and
buries the plain part. A note filed to my own store since his last message counts the
same as one in the reply, so the visible reply can be only the plain part.
"""

import json

import pytest

from divineos.core import reflection_room as room

REFUSAL = (
    "PreToolUse:Edit hook error: [bash .claude/hooks/work-item-doorman.sh]: \n"
    "THE BUILD FLOW DOORMAN -- the front of the flow"
)
NOTE = "work-item-doorman stopped me. fixed by structure: flow first"


def _his(text, ts="2026-10-08T10:00:00.000Z"):
    # A real record carries the role; the one reader of his words requires it (his_message.hear).
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}}


def _tool(ts="2026-10-08T10:01:00.000Z"):
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {"content": [{"type": "tool_use", "name": "Bash"}]},
    }


def _error(text, ts="2026-10-08T10:02:00.000Z"):
    return {
        "type": "user",
        "timestamp": ts,
        "message": {"content": [{"type": "tool_result", "is_error": True, "content": text}]},
    }


def _say(text, ts="2026-10-08T10:03:00.000Z"):
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {"content": [{"type": "text", "text": text}]},
    }


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    return tmp_path


def _turn(*extra):
    return [_his("fix the door"), _tool(), _error(REFUSAL), *extra]


def test_a_filed_note_takes_up_the_stumble_with_no_reflection_in_the_reply():
    records = _turn(_say("Done. The door is fixed."))
    worked, stumbles, reply = room.this_turn(records)
    assert worked and stumbles
    assert not room.taken_up(reply, stumbles)  # control: the reply alone does not
    room.file_note(NOTE, ts="2026-10-08T10:02:30.000Z")
    notes = room.filed_notes_this_turn(records)
    assert room.taken_up(room.with_filed_notes(reply, notes), stumbles)


def test_a_note_filed_before_his_message_is_not_this_turns():
    room.file_note(NOTE, ts="2026-10-08T09:00:00.000Z")
    assert room.filed_notes_this_turn(_turn()) == []


def test_two_notes_are_both_kept_and_come_back_oldest_first():
    room.file_note("first fixed by structure: a", ts="2026-10-08T10:02:10.000Z")
    room.file_note("second owed: b", ts="2026-10-08T10:02:20.000Z")
    assert room.filed_notes_this_turn(_turn()) == [
        "first fixed by structure: a",
        "second owed: b",
    ]


def test_an_owed_line_in_a_filed_note_reaches_the_tracker_reader():
    text = "work-item-doorman stopped me. owed: bind prep to the piece named"
    room.file_note(text, ts="2026-10-08T10:02:30.000Z")
    notes = room.filed_notes_this_turn(_turn())
    assert room.owed_lines(room.with_filed_notes("", notes)) == ["bind prep to the piece named"]


def test_a_missing_store_is_honestly_empty_and_a_broken_one_is_loud(_home):
    assert room.filed_notes_this_turn(_turn()) == []
    (_home / "reflection_notes.jsonl").write_text("{not json\n", encoding="utf-8")
    with pytest.raises(ValueError):
        room.filed_notes_this_turn(_turn())


def test_the_store_is_json_lines(_home):
    room.file_note(NOTE, ts="2026-10-08T10:02:30.000Z")
    row = json.loads((_home / "reflection_notes.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row == {"ts": "2026-10-08T10:02:30.000Z", "text": NOTE}


def test_the_hold_names_the_filing_command_first():
    _, stumbles, _ = room.this_turn(_turn())
    assert "divineos reflection-note" in room.hold_reason(stumbles)
