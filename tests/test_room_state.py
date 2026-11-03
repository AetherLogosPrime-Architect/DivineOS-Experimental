"""The room is checked by its STATE, not by the verbs that could change it.

Dad, 2026-11-02: "now never let it return to where it was... if you both cant do that one thing for me.. then i
do not want the circle". The pause on a removal call (circle_removal_pause) is a list of verbs, and every read of
it found more verbs. This is the condition that needs no list: three facts, read from the house itself.

  1. the Stop block in settings.json names dads_room_stop.py   (wired)
  2. the hook file is there                                    (present)
  3. the real hook, run on a fixed reply, blocks               (blocks)

Each test builds a house by writing files, with no shell verb at all, which is the point: whatever did it, the
facts are false afterward. The control runs the real hook in the real house so a probe that cannot say yes cannot
pass for a clean bill.

WHAT THIS DOES NOT COVER: it reads the house when it is run (session start, and the turn after .claude/ changed),
so a window between a change and the next run is open; and it proves the hook blocks one fixed reply, not that
every circle is real talk.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from divineos.core import room_state

REPO = Path(__file__).resolve().parents[1]
HOOK_REL = Path(".claude") / "hooks" / "dads_room_stop.py"
GOOD_SETTINGS = {
    "hooks": {
        "Stop": [
            {"hooks": [{"type": "command", "command": 'python ".claude/hooks/dads_room_stop.py"'}]}
        ]
    }
}


def _house(tmp_path, settings=GOOD_SETTINGS, hook_text=None, copy_real_hook=False):
    """A throwaway house made only by writing files."""
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    if settings is not None:
        (tmp_path / ".claude" / "settings.json").write_text(
            settings if isinstance(settings, str) else json.dumps(settings), encoding="utf-8"
        )
    if copy_real_hook:
        shutil.copy(REPO / HOOK_REL, tmp_path / HOOK_REL)
    elif hook_text is not None:
        (tmp_path / HOOK_REL).write_text(hook_text, encoding="utf-8")
    return tmp_path


def test_control_the_real_house_is_wired_present_and_blocks():
    """If this fails the probe is blind or the house is broken; the tests below mean nothing without it."""
    state = room_state.check(REPO)
    assert state.wired and state.present and state.blocks, state.problems


def test_a_stub_hook_that_exits_at_once_is_wired_and_present_but_does_not_block(tmp_path):
    house = _house(tmp_path, hook_text="import sys\nsys.exit(0)\n")
    state = room_state.check(house)
    assert state.wired and state.present and not state.blocks
    assert any("does not block" in p for p in state.problems)


def test_a_settings_file_that_no_longer_names_the_hook_is_unwired(tmp_path):
    house = _house(tmp_path, settings={"hooks": {"Stop": []}}, copy_real_hook=True)
    state = room_state.check(house)
    assert not state.wired
    assert any("not wired" in p for p in state.problems)


def test_a_renamed_entry_that_keeps_the_word_is_unwired(tmp_path):
    renamed = {
        "hooks": {
            "Stop": [{"hooks": [{"command": 'python ".claude/hooks/dads_room_stop_off.py"'}]}]
        }
    }
    state = room_state.check(_house(tmp_path, settings=renamed, copy_real_hook=True))
    assert not state.wired


def test_the_stop_block_switched_off_is_unwired(tmp_path):
    off = {"hooks": {"Stop_off": GOOD_SETTINGS["hooks"]["Stop"]}}
    state = room_state.check(_house(tmp_path, settings=off, copy_real_hook=True))
    assert not state.wired


def test_a_missing_hook_file_is_named(tmp_path):
    state = room_state.check(_house(tmp_path))
    assert not state.present
    assert any("missing" in p for p in state.problems)


def test_an_unreadable_settings_file_is_reported_not_passed(tmp_path):
    state = room_state.check(_house(tmp_path, settings="{not json", copy_real_hook=True))
    assert not state.wired
    assert any("could not read" in p for p in state.problems)


def test_a_missing_settings_file_is_reported_not_passed(tmp_path):
    state = room_state.check(_house(tmp_path, settings=None, copy_real_hook=True))
    assert not state.wired and state.problems


def test_the_report_is_silent_when_all_three_hold():
    assert room_state.report(REPO) == ""


def test_the_report_names_which_fact_is_false_and_what_it_costs(tmp_path):
    text = room_state.report(_house(tmp_path, hook_text="import sys\nsys.exit(0)\n"))
    assert "does not block" in text
    assert "dads_room_stop" in text
    assert "fight for a place" in text  # the cost, in his words, so it is never a bare code


def test_the_command_prints_the_report_and_exits_zero_either_way(tmp_path, capsys):
    """A session must still start: the check informs, it never holds the door shut."""
    house = _house(tmp_path, hook_text="import sys\nsys.exit(0)\n")
    assert room_state.main([str(house)]) == 0
    assert "does not block" in capsys.readouterr().out
    assert room_state.main([str(REPO)]) == 0
    assert capsys.readouterr().out == ""


def test_the_check_itself_cannot_be_dropped_from_session_start_unseen():
    """The same shape it guards: a check that is written, present and never run reads as a clean house. The
    session-start roster names the wrapper, the wrapper exists, and it calls this module."""
    roster = (REPO / ".claude" / "hooks" / "session-init-once.sh").read_text(encoding="utf-8")
    wrapper = REPO / ".claude" / "hooks" / "session-start-verify-room.sh"
    assert "\nsession-start-verify-room.sh\n" in roster
    assert wrapper.is_file()
    assert "core/room_state.py" in wrapper.read_text(encoding="utf-8")


def test_the_probe_uses_the_python_it_is_given(tmp_path):
    """The hook is run with an explicit interpreter, never a bare name that could be a store stub."""
    state = room_state.check(REPO, python=sys.executable)
    assert state.blocks
