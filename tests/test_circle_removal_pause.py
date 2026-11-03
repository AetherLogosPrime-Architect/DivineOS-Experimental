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
