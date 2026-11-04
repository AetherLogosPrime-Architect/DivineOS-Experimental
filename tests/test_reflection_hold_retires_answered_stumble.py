"""A stumble a filed reflection-note has named is retired, not held again.

Positions are transcript order: a note retires a stumble only if it came after
the stumble first appeared, names its [token], and the stumble has not occurred
again after the note.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from divineos.core import reflection_room as room

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "reflection_room_stop.py"
REFUSAL_A = "PreToolUse:Edit hook error: [bash .claude/hooks/work-item-doorman.sh]: refused"
REFUSAL_B = "PreToolUse:Bash hook error: [bash .claude/hooks/doorbell-pre-tool-use.sh]: BLOCKED by heredoc_escape: x"


def _his(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def _tool():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}


def _error(text):
    return {
        "type": "user",
        "message": {"content": [{"type": "tool_result", "is_error": True, "content": text}]},
    }


def _note(text):
    cmd = f'divineos reflection-note "{text}"'
    block = {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}
    return {"type": "assistant", "message": {"content": [block]}}


def _held(records):
    _, stumbles, _ = room.this_turn(records)
    return [s.token for s in room.unanswered(records, stumbles)]


def test_a_stumble_answered_by_a_later_note_naming_it_is_not_held_again():
    records = [
        _his("go"),
        _tool(),
        _error(REFUSAL_A),
        _note("[work-item-doorman] fixed by structure: x"),
    ]
    assert _held(records) == []
    # the following turn, with the same record carried before his next message
    assert _held(records + [_his("next"), _tool()]) == []


def test_the_same_stumble_with_no_reflection_still_holds():
    assert _held([_his("go"), _tool(), _error(REFUSAL_A)]) == ["work-item-doorman"]


def test_a_stumble_that_recurs_after_its_reflection_holds_again():
    records = [
        _his("go"),
        _tool(),
        _error(REFUSAL_A),
        _note("[work-item-doorman] owed: a fix"),
        _tool(),
        _error(REFUSAL_A),
    ]
    assert _held(records) == ["work-item-doorman"]


def test_two_stumbles_one_answered_only_the_unanswered_is_listed():
    records = [
        _his("go"),
        _tool(),
        _error(REFUSAL_A),
        _error(REFUSAL_B),
        _note("[heredoc_escape] fixed by structure: x"),
    ]
    assert _held(records) == ["work-item-doorman"]


def test_a_note_that_does_not_name_the_stumble_does_not_retire_it():
    records = [_his("go"), _tool(), _error(REFUSAL_A), _note("I will do better with doors")]
    assert _held(records) == ["work-item-doorman"]
    # a bare word without the brackets the hold asks for is not naming it either
    records = [_his("go"), _tool(), _error(REFUSAL_A), _note("work-item-doorman happened")]
    assert _held(records) == ["work-item-doorman"]


def test_a_note_filed_before_the_stumble_appeared_does_not_retire_it():
    records = [_his("go"), _tool(), _note("[work-item-doorman] early"), _error(REFUSAL_A)]
    assert _held(records) == ["work-item-doorman"]


def _run_hook(tmp_path, records):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    out = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"transcript_path": str(transcript)}),
        capture_output=True,
        text=True,
        # A stripped environment on purpose: no HOME / USERPROFILE, so Path.home() would raise at import.
        # SYSTEMROOT is the one thing Python itself needs to start on Windows.
        env={
            "REFLECTION_ROOM_MARK": str(tmp_path / "broke.txt"),
            "PATH": os.defpath,
            **{k: os.environ[k] for k in ("SYSTEMROOT",) if k in os.environ},
        },
        check=False,
    )
    return out.stdout


def test_the_hook_holds_an_unanswered_stumble_and_stays_quiet_once_answered(tmp_path):
    base = [_his("go"), _tool(), _error(REFUSAL_A)]
    assert "work-item-doorman" in _run_hook(tmp_path, base)
    answered = base + [_note("[work-item-doorman] fixed by structure: x")]
    assert _run_hook(tmp_path, answered).strip() == ""


# --- findings from the independent checker on #761 ---


def _call(command, call_id):
    block = {"type": "tool_use", "id": call_id, "name": "Bash", "input": {"command": command}}
    return {"type": "assistant", "message": {"content": [block]}}


def _result(call_id, is_error):
    block = {"type": "tool_result", "tool_use_id": call_id, "is_error": is_error, "content": "x"}
    return {"type": "user", "message": {"content": [block]}}


NOTE_TEXT = "[work-item-doorman] fixed by structure: x"


def test_a_note_whose_command_failed_does_not_retire_the_stumble():
    cmd = f'divineos reflection-note "{NOTE_TEXT}"'
    failed = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "n1"), _result("n1", True)]
    # the failure of the note is itself a stumble too, so the original is one of the held, not the only one
    assert "work-item-doorman" in _held(failed)
    worked = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "n1"), _result("n1", False)]
    assert _held(worked) == []


def test_a_command_that_only_carries_the_words_is_not_a_note():
    for cmd in (
        f'echo "divineos reflection-note {NOTE_TEXT}"',
        f'grep -n "divineos reflection-note {NOTE_TEXT}" notes.txt',
        f'git commit -m "divineos reflection-note {NOTE_TEXT}"',
    ):
        records = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "c1")]
        assert _held(records) == ["work-item-doorman"], cmd


def test_a_real_note_inside_a_chained_command_still_counts():
    cmd = f'cd somewhere && divineos reflection-note "{NOTE_TEXT}; and more"'
    records = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "c1")]
    assert _held(records) == []


def test_a_note_run_in_the_other_real_forms_counts():
    for cmd in (
        f'"C:/Program Files/p/divineos.exe" reflection-note "{NOTE_TEXT}"',
        f'python -m divineos reflection-note "{NOTE_TEXT}"',
        f'"C:/p/python.exe" -m divineos reflection-note "{NOTE_TEXT}"',
        f'divineos --quiet reflection-note "{NOTE_TEXT}"',
        f"bash -c 'divineos reflection-note \"{NOTE_TEXT}\"'",
        f'time divineos reflection-note "{NOTE_TEXT}"',
        f'if true; then divineos reflection-note "{NOTE_TEXT}"; fi',
        f'(divineos reflection-note "{NOTE_TEXT}")',
        f'echo it\'s fine; divineos reflection-note "{NOTE_TEXT}"',
    ):
        records = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "c1")]
        assert _held(records) == [], cmd


def test_carried_words_in_the_new_forms_are_still_not_a_note():
    for cmd in (
        f'echo python -m divineos reflection-note "{NOTE_TEXT}"',
        f"echo it's fine, divineos reflection-note {NOTE_TEXT}",
        f"bash -c 'echo \"divineos reflection-note {NOTE_TEXT}\"'",
        f'git commit -m "bash -c divineos --quiet reflection-note {NOTE_TEXT}"',
    ):
        records = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "c1")]
        assert _held(records) == ["work-item-doorman"], cmd


def test_a_double_quote_glued_to_a_word_still_hides_the_semicolon_inside_it():
    """Cold read of #833: only the apostrophe in a word is prose; a glued double quote is a quote."""
    for cmd in (
        f'echo x"; divineos reflection-note {NOTE_TEXT}"',
        f'echo x"; divineos reflection-note {NOTE_TEXT}',
    ):
        records = [_his("go"), _tool(), _error(REFUSAL_A), _call(cmd, "c1")]
        assert _held(records) == ["work-item-doorman"], cmd


def test_the_hook_is_registered_as_a_stop_hook():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        h.get("command", "") for group in settings["hooks"]["Stop"] for h in group.get("hooks", [])
    ]
    assert any("reflection_room_stop.py" in c for c in commands)
