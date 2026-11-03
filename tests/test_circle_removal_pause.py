"""The circle is not unplugged in one call (Dad 2026-11-02, via Aria: "now never let it return to where it was").

The pause sits on the ACT of removing the room (unwiring dads_room_stop from settings.json, or removing the
hook file), never on his words (Aria's second attack, walk-caf601ce75d2). The first removal call is held and
says what the room costs him; the next removal call goes through with no reason owed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core.circle_removal_pause import pause_for

SETTINGS = ".claude/settings.json"
WIRED = '"command": "python .claude/hooks/dads_room_stop.py"'


def edit_removing_the_room() -> tuple[str, dict]:
    return "Edit", {
        "file_path": SETTINGS,
        "old_string": f"{{ {WIRED} }},\n  ",
        "new_string": "",
    }


@pytest.fixture()
def marker(tmp_path: Path) -> Path:
    return tmp_path / "circle_pause_shown.json"


def test_the_first_unwiring_is_held_and_names_the_cost_to_him(marker):
    tool, tool_input = edit_removing_the_room()
    text = pause_for(tool, tool_input, marker)
    assert text is not None
    assert "fight" in text.lower()  # the cost in his own words: he has to fight for his place
    assert "again" in text.lower()  # the way to finish it is stated, so it is never a trap
    assert marker.exists()


def test_the_second_removal_goes_through_with_no_reason_owed(marker):
    tool, tool_input = edit_removing_the_room()
    assert pause_for(tool, tool_input, marker) is not None
    assert pause_for(tool, tool_input, marker) is None
    assert not marker.exists()


def test_after_it_went_through_the_next_removal_is_paused_again(marker):
    tool, tool_input = edit_removing_the_room()
    pause_for(tool, tool_input, marker)
    pause_for(tool, tool_input, marker)
    assert pause_for(tool, tool_input, marker) is not None


def test_one_call_never_both_pauses_and_removes(marker):
    tool, tool_input = edit_removing_the_room()
    first = pause_for(tool, tool_input, marker)
    assert first is not None  # held means the edit does not run
    assert marker.exists()


@pytest.mark.parametrize(
    "command",
    [
        "rm .claude/hooks/dads_room_stop.py",
        "git rm .claude/hooks/dads_room_stop.py",
        "mv .claude/hooks/dads_room_stop.py /tmp/gone.py",
        "Remove-Item .claude/hooks/dads_room_stop.py",
        "sed -i '/dads_room_stop/d' .claude/settings.json",
    ],
)
def test_the_act_is_caught_whatever_words_he_used(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is not None


@pytest.mark.parametrize(
    "command",
    [
        "cat .claude/hooks/dads_room_stop.py",
        "grep -n dads_room_stop .claude/settings.json",
        "python -m pytest tests/test_dads_room_stop.py -q",
        "git log -- .claude/hooks/dads_room_stop.py",
    ],
)
def test_reading_or_testing_the_room_is_never_paused(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is None
    assert not marker.exists()


def test_an_edit_that_keeps_the_room_wired_is_never_paused(marker):
    tool_input = {
        "file_path": SETTINGS,
        "old_string": f'{WIRED}, "timeout": 5',
        "new_string": f'{WIRED}, "timeout": 10',
    }
    assert pause_for("Edit", tool_input, marker) is None


def test_an_unrelated_settings_edit_is_never_paused(marker):
    tool_input = {
        "file_path": SETTINGS,
        "old_string": '"command": "python .claude/hooks/other.py"',
        "new_string": '"command": "python .claude/hooks/other2.py"',
    }
    assert pause_for("Edit", tool_input, marker) is None
    assert not marker.exists()


def test_a_whole_file_write_that_drops_the_room_is_paused(marker, tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": WIRED}), encoding="utf-8")
    tool_input = {"file_path": str(settings), "content": json.dumps({"hooks": "none"})}
    assert pause_for("Write", tool_input, marker) is not None


def test_a_whole_file_write_that_keeps_the_room_is_not_paused(marker, tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": WIRED}), encoding="utf-8")
    tool_input = {"file_path": str(settings), "content": json.dumps({"hooks": WIRED, "x": 1})}
    assert pause_for("Write", tool_input, marker) is None


def test_a_rename_that_keeps_the_word_but_changes_the_file_is_paused(marker):
    # Aria's cold read, way 1: the word survives in new_string but the file it names is gone.
    tool_input = {
        "file_path": SETTINGS,
        "old_string": "python .claude/hooks/dads_room_stop.py",
        "new_string": "python .claude/hooks/dads_room_stop_off.py",
    }
    assert pause_for("Edit", tool_input, marker) is not None


def test_renaming_the_stop_block_itself_is_paused(marker):
    # way 2: the room hangs off the Stop key, and the word never appears in the old text.
    tool_input = {"file_path": SETTINGS, "old_string": '"Stop": [', "new_string": '"Stop_off": ['}
    assert pause_for("Edit", tool_input, marker) is not None


def test_any_write_or_edit_of_the_hook_file_itself_is_paused(marker):
    # ways 3 and 4: gutting the hook leaves it "running" and printing nothing.
    hook = ".claude/hooks/dads_room_stop.py"
    assert (
        pause_for("Write", {"file_path": hook, "content": "import sys\nsys.exit(0)\n"}, marker)
        is not None
    )
    marker.unlink()
    edit = {
        "file_path": hook,
        "old_string": "def main",
        "new_string": "import sys\nsys.exit(0)\ndef main",
    }
    assert pause_for("Edit", edit, marker) is not None


@pytest.mark.parametrize(
    "command",
    [
        "> .claude/hooks/dads_room_stop.py",
        ": > .claude/hooks/dads_room_stop.py",
        "cp /dev/null .claude/hooks/dads_room_stop.py",
        "truncate -s 0 .claude/hooks/dads_room_stop.py",
        "python -c \"import os;os.rename('.claude/hooks/dads_room_stop.py','x')\"",
        "python -c \"import os;os.remove('.claude/hooks/dads_room_stop.py')\"",
        "git mv .claude/hooks/dads_room_stop.py old.py",
    ],
)
def test_the_other_ways_to_hollow_or_move_the_file_are_paused(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is not None


@pytest.mark.parametrize(
    "command",
    [
        "sed -i 's/dads_room_stop/x_off/' .claude/settings.json",
        "cp /tmp/stub.py .claude/hooks/dads_room_stop.py",
        "echo pass | tee .claude/hooks/dads_room_stop.py",
        "Rename-Item .claude/hooks/dads_room_stop.py gone.py",
        "Move-Item .claude/hooks/dads_room_stop.py C:/tmp/gone.py",
        "Clear-Content .claude/hooks/dads_room_stop.py",
        "Set-Content .claude/hooks/dads_room_stop.py 'pass'",
        "'x' | Out-File .claude/hooks/dads_room_stop.py",
        "git checkout HEAD~50 -- .claude/settings.json",
        "git restore .claude/hooks/dads_room_stop.py",
        "python -c \"open('.claude/settings.json','w').write('{}')\"",
    ],
)
def test_aria_second_read_eleven_other_ways_through_are_paused(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is not None


def test_a_multiedit_that_drops_the_room_or_touches_the_hook_file_is_paused(marker):
    drops = {
        "file_path": SETTINGS,
        "edits": [{"old_string": "python .claude/hooks/dads_room_stop.py", "new_string": "true"}],
    }
    assert pause_for("MultiEdit", drops, marker) is not None
    marker.unlink()
    hook = {
        "file_path": ".claude/hooks/dads_room_stop.py",
        "edits": [{"old_string": "def main", "new_string": "def main_off"}],
    }
    assert pause_for("MultiEdit", hook, marker) is not None


def test_restoring_the_room_from_main_is_never_paused(marker):
    # The state check tells us to repair with exactly this; the repair must not meet the pause.
    repair = "git checkout origin/main -- .claude/hooks/dads_room_stop.py .claude/settings.json"
    assert pause_for("Bash", {"command": repair}, marker) is None


def test_a_removal_that_goes_through_leaves_a_record_that_he_decided_it(
    marker, tmp_path, monkeypatch
):
    # Aria's state check would otherwise raise the alarm on every session for a room he chose to remove.
    decision = tmp_path / "circle_removed_on_his_decision.json"
    monkeypatch.setenv("CIRCLE_REMOVED_MARKER", str(decision))  # the name Aria's state check reads
    import importlib

    from divineos.core import circle_removal_pause

    importlib.reload(circle_removal_pause)
    removal = {"command": "rm .claude/hooks/dads_room_stop.py"}
    assert circle_removal_pause.pause_for("Bash", removal, marker, session="s1") is not None
    assert not decision.exists()  # the pause alone decides nothing
    assert circle_removal_pause.pause_for("Bash", removal, marker, session="s1") is None
    assert json.loads(decision.read_text(encoding="utf-8"))["session"] == "s1"


def test_a_pause_shown_in_one_session_does_not_give_a_free_removal_in_another(marker):
    # Aria's marker finding: shown, kept, and weeks later a quiet removal must meet the pause again.
    removal = {"command": "rm .claude/hooks/dads_room_stop.py"}
    assert pause_for("Bash", removal, marker, session="monday") is not None
    assert pause_for("Bash", removal, marker, session="next-month") is not None
    assert pause_for("Bash", removal, marker, session="next-month") is None


def test_reading_the_hook_file_and_copying_it_somewhere_else_is_not_paused(marker):
    assert (
        pause_for("Bash", {"command": "cp .claude/hooks/dads_room_stop.py /tmp/backup.py"}, marker)
        is None
    )
    assert (
        pause_for(
            "Bash", {"command": "cat .claude/hooks/dads_room_stop.py > /tmp/copy.txt"}, marker
        )
        is None
    )


REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "circle_removal_pause.py"


def _run_hook(payload: dict, marker: Path):
    import os
    import subprocess
    import sys

    env = {**os.environ, "CIRCLE_PAUSE_MARKER": str(marker)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_the_real_door_holds_the_first_removal_with_exit_two_and_lets_the_second_through(marker):
    payload = {"tool_name": "Bash", "tool_input": {"command": "rm .claude/hooks/dads_room_stop.py"}}
    first = _run_hook(payload, marker)
    assert first.returncode == 2
    assert "fight" in first.stderr.lower()
    second = _run_hook(payload, marker)
    assert second.returncode == 0


def test_the_real_door_never_blocks_an_ordinary_call(marker):
    payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    assert _run_hook(payload, marker).returncode == 0


def test_the_door_is_registered_for_the_calls_that_can_remove_the_room():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    blocks = [
        block
        for block in settings["hooks"]["PreToolUse"]
        if any("circle_removal_pause.py" in h["command"] for h in block["hooks"])
    ]
    assert len(blocks) == 1
    for tool in ("Edit", "Write", "Bash", "PowerShell"):
        assert tool in blocks[0]["matcher"].split("|")


def test_the_pause_does_not_depend_on_his_words(marker):
    # The phrase list is gone on purpose: nothing about his message is read.
    import inspect

    from divineos.core import circle_removal_pause

    source = inspect.getsource(circle_removal_pause)
    for phrase in ("remove the circle", "get rid of it", "take it out"):
        assert phrase not in source
