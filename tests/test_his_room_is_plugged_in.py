"""His room is plugged in: the hook that asks for it is wired to the end of every reply.

Dad, 2026-10-22: "if there is nothing structural to back it? then saying from now on is literally air.. i asked
for the circle room to be built for this reason. yet its not built." The room WAS built: dads_room_stop.py
exists with its tests. It was unwired from the Stop hooks on 2026-10-03 (#586, "keep it in the archives") and
never wired back, so a working reply could leave without it and nothing noticed. A hook file nobody calls and a
hook that is not there look identical from inside; this reads the wiring, not the file.

WHAT THIS DOES NOT COVER: that the harness actually runs the hook. It reads the settings file only.
"""

import json
from pathlib import Path

SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"


def _stop_commands() -> list[str]:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    commands = []
    for group in data["hooks"]["Stop"]:
        for hook in group.get("hooks", []):
            commands.append(hook.get("command", ""))
    assert commands, "no Stop hooks were read: this reader is blind, not the wiring clean"
    return commands


def test_the_room_hook_runs_when_a_reply_ends():
    assert any("dads_room_stop.py" in c for c in _stop_commands())


def test_the_reader_can_see_a_hook_that_is_not_wired():
    """Control: a hook that was never wired must be reported absent."""
    assert not any("no_such_hook_was_ever_wired.py" in c for c in _stop_commands())


def test_the_wired_room_hook_fails_loud_when_its_file_is_missing():
    wired = [c for c in _stop_commands() if "dads_room_stop.py" in c]
    assert wired and all("NOT RUNNING" in c for c in wired)
