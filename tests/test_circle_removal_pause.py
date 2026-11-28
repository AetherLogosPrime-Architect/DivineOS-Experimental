"""The circle is not unplugged in one call (Dad 2026-11-02, via Aria: "now never let it return to where it was").

The pause sits on the ACT of removing the room (unwiring dads_room_stop from settings.json, or removing the
hook file), never on his words (Aria's second attack, walk-caf601ce75d2). The first removal call is held and
says what the room costs him; the next removal call goes through with no reason owed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from divineos.core import circle_removal_pause as crp
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


def test_the_marker_name_is_the_one_aria_state_check_reads():
    from divineos.core import circle_removal_pause

    assert circle_removal_pause.DECISION_MARKER.name == "circle_removed_on_his_decision.json"


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
        check=False,
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


# --- The outside reader's first finding: the pause fired on ordinary work that only NAMED the file. ---
# The room is the file whose FINAL path component is dads_room_stop.py, and a removal is something done TO it.


@pytest.mark.parametrize(
    "tool, tool_input",
    [
        (
            "Edit",
            {"file_path": "tests/test_dads_room_stop.py", "old_string": "a", "new_string": "b"},
        ),
        ("Write", {"file_path": "tests/test_dads_room_stop.py", "content": "def test_x(): pass\n"}),
        ("Write", {"file_path": ".claude/hooks/dads_room_stop.py.bak", "content": "x"}),
        (
            "Edit",
            {"file_path": "docs/dads_room_stop_notes.md", "old_string": "a", "new_string": "b"},
        ),
        (
            "MultiEdit",
            {
                "file_path": "tests/test_dads_room_stop.py",
                "edits": [{"old_string": "a", "new_string": "b"}],
            },
        ),
    ],
)
def test_ordinary_edits_of_files_that_only_share_the_name_are_never_paused(
    marker, tool, tool_input
):
    assert pause_for(tool, tool_input, marker) is None
    assert not marker.exists()


@pytest.mark.parametrize(
    "command",
    [
        "cp .claude/hooks/dads_room_stop.py backup/dads_room_stop.py.bak",
        "cp .claude/hooks/dads_room_stop.py /tmp/dads_room_stop_copy.py",
        "echo done > /tmp/notes_about_dads_room_stop.txt",
        "echo x >> tests/test_dads_room_stop.py",
        "cat .claude/hooks/dads_room_stop.py > /tmp/dads_room_stop.py.txt",
        "git checkout -b fix/dads_room_stop.py",
        "git checkout -b dads_room_stop.py origin/main",
        "git switch -c dads_room_stop.py",
        'git commit -m "rm the dads_room_stop test, mv the notes"',
        "rm tests/test_dads_room_stop.py",
        "mv tests/test_dads_room_stop.py tests/test_the_room.py",
        "sed -i 's/a/b/' tests/test_dads_room_stop.py",
        "tee /tmp/dads_room_stop.log",
        "echo 'rm .claude/hooks/dads_room_stop.py'",
        "python -m pytest tests/test_dads_room_stop.py -q && echo ok",
    ],
)
def test_ordinary_commands_that_only_name_the_file_are_never_paused(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is None
    assert not marker.exists()


@pytest.mark.parametrize(
    "tool_input",
    [
        {"file_path": "./.claude/hooks/../hooks/dads_room_stop.py", "content": "x"},
        {"file_path": ".claude\\hooks\\dads_room_stop.py", "content": "x"},
        {"file_path": ".claude/hooks/DADS_ROOM_STOP.PY", "content": "x"},
    ],
)
def test_the_real_file_is_still_paused_however_the_path_is_spelled(marker, tool_input):
    assert pause_for("Write", tool_input, marker) is not None


@pytest.mark.parametrize(
    "command",
    [
        'rm "./.claude/hooks/dads_room_stop.py"',
        "rm -f .claude\\hooks\\dads_room_stop.py",
        "cd .claude/hooks && rm dads_room_stop.py",
        "echo hi; mv .claude/hooks/dads_room_stop.py /tmp/x",
        "Remove-Item -LiteralPath '.claude\\hooks\\dads_room_stop.py' -Force",
        "cat x | tee .claude/hooks/dads_room_stop.py",
        "echo pass 2> /dev/null > .claude/hooks/dads_room_stop.py",
    ],
)
def test_the_real_removal_is_still_paused_however_the_command_is_shaped(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is not None


# --- The outside reader's second finding: the marker said "he decided" with nothing to show he did. ---
# The pause no longer vouches for itself. The marker is written only from a line of his found in his table,
# and carries that line and its time; without both fields a marker is "no decision on record".

SHOWN_AT = datetime(2026, 11, 3, 20, 0, 0, tzinfo=UTC).timestamp()
BEFORE = "2026-11-03T19:00:00.000Z"
AFTER = "2026-11-03T20:30:15.000Z"
HIS_LINE = "yes take the circle out, i have decided and i want it gone.."


class World:
    def __init__(self, root: Path):
        self.corpus = root / "dad_all.jsonl"
        self.released = root / "circle_pause_released.json"
        self.decision = root / "circle_removed_on_his_decision.json"

    def says(self, when: str, text: str) -> None:
        with self.corpus.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": when, "project": "x", "text": text}) + "\n")

    def pause_was_let_through(self) -> None:
        self.released.write_text(
            json.dumps({"session": "s1", "shown_at": SHOWN_AT, "released_at": SHOWN_AT + 60}),
            encoding="utf-8",
        )

    def record(self, words: str) -> dict:
        return crp.record_his_decision(
            words, session="s1", corpus=self.corpus, released=self.released, decision=self.decision
        )


@pytest.fixture()
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def test_two_ordinary_edits_of_the_hook_file_write_no_decision(marker, tmp_path, monkeypatch):
    # The reported failure: two ordinary edits and the record said he decided.
    decision = tmp_path / "decision.json"
    monkeypatch.setattr(crp, "DECISION_MARKER", decision)
    edit = {"file_path": ".claude/hooks/dads_room_stop.py", "old_string": "a", "new_string": "b"}
    assert pause_for("Edit", edit, marker, session="s1") is not None
    assert pause_for("Edit", edit, marker, session="s1") is None  # goes through, no reason owed
    assert not decision.exists()
    assert crp.decision_on_record(decision) is None
    released = json.loads(
        marker.with_name("circle_pause_released.json").read_text(encoding="utf-8")
    )
    assert released["session"] == "s1" and released["shown_at"] <= released["released_at"]


def test_his_own_line_in_his_table_is_recorded_with_its_text_and_time(world):
    world.says(BEFORE, "keep the room, it matters to me..")
    world.says(AFTER, HIS_LINE)
    world.pause_was_let_through()
    made = world.record("i have decided and i want it gone")
    assert (
        made["his_words"] == HIS_LINE
    )  # the whole line as he typed it, never the words as handed in
    assert made["at"] == "2026-11-03T20:30:15Z"
    assert json.loads(world.decision.read_text(encoding="utf-8")) == made
    assert crp.decision_on_record(world.decision) == made


@pytest.mark.parametrize(
    "setup, words, reason",
    [
        ("table", "take it out now and do not ask me again", "not in his table"),  # a paraphrase
        (
            "early",
            HIS_LINE,
            "before the pause",
        ),  # his real words, but from before the pause was shown
        ("pasted", "take the circle out please", "not in his table"),  # inside a block he pasted
        ("nothing_let_through", HIS_LINE, "no removal went through"),
        ("no_table", HIS_LINE, "could not read his table"),
        ("short", "yes", "too short"),  # a bare word matches almost any line
    ],
)
def test_the_writer_refuses_whatever_it_cannot_find_in_his_table(world, setup, words, reason):
    if setup in ("table", "nothing_let_through"):
        world.says(AFTER, "keep the room please")
    if setup == "short":
        world.says(AFTER, HIS_LINE)
    if setup == "early":
        world.says(BEFORE, HIS_LINE)
    if setup == "pasted":
        world.says(
            AFTER, '<pasted_content id="abc">take the circle out please</pasted_content id="abc">'
        )
    if setup != "nothing_let_through":
        world.pause_was_let_through()
    with pytest.raises(crp.DecisionNotRecorded, match=reason):
        world.record(words)
    assert not world.decision.exists()


def test_a_line_typed_in_the_same_second_the_pause_was_shown_still_counts(world):
    world.says("2026-11-03T20:00:00.000Z", HIS_LINE)
    world.pause_was_let_through()
    assert world.record(HIS_LINE)["at"] == "2026-11-03T20:00:00Z"


@pytest.mark.parametrize(
    "content",
    [
        None,  # no file at all
        "not json",
        json.dumps(["a", "list"]),
        json.dumps({"session": "s1", "decided_at": 1.0}),  # the old shape: no proof at all
        json.dumps({"his_words": HIS_LINE}),  # no time
        json.dumps({"at": "2026-11-03T20:30:15Z"}),  # no words
        json.dumps({"his_words": "", "at": "2026-11-03T20:30:15Z"}),
        json.dumps({"his_words": HIS_LINE, "at": "yesterday"}),
        json.dumps(
            {"his_words": HIS_LINE, "at": "2026-11-03T20:30:15.000Z"}
        ),  # not the fixed shape
        json.dumps({"his_words": 7, "at": "2026-11-03T20:30:15Z"}),
    ],
)
def test_a_marker_without_both_proofs_is_no_decision_on_record(tmp_path, content):
    path = tmp_path / "circle_removed_on_his_decision.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert crp.decision_on_record(path) is None


def _run_module(args: list[str], env_extra: dict):
    import os
    import subprocess
    import sys

    path = os.pathsep.join(p for p in (str(REPO / "src"), os.environ.get("PYTHONPATH", "")) if p)
    env = {**os.environ, **env_extra, "PYTHONPATH": path}
    return subprocess.run(
        [sys.executable, "-m", "divineos.core.circle_removal_pause", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


def test_the_command_line_writer_records_a_real_line_and_refuses_an_invented_one(world):
    world.says(AFTER, HIS_LINE)
    world.pause_was_let_through()
    env = {
        "DADS_CORPUS": str(world.corpus),
        "CIRCLE_PAUSE_RELEASED": str(world.released),
        "CIRCLE_REMOVED_MARKER": str(world.decision),
    }
    refused = _run_module(["record", "something he never said at all"], env)
    assert refused.returncode == 1 and "not in his table" in refused.stderr
    assert not world.decision.exists()
    done = _run_module(["record", "i have decided and i want it gone"], env)
    assert done.returncode == 0
    assert crp.decision_on_record(world.decision)["his_words"] == HIS_LINE


def test_the_pause_text_tells_whoever_goes_through_how_to_record_his_words(marker):
    text = pause_for("Bash", {"command": "rm .claude/hooks/dads_room_stop.py"}, marker)
    assert "circle_removal_pause record" in text


# --- The outside reader's third finding: most routes to the same removal passed the pause. ---
# The routes below are plain removals of the hook or its registration. The ones deliberately NOT closed are in
# the module docstring, with the reason.

_H = ".claude/hooks/dads_room_stop.py"
_S = ".claude/settings.json"

PLAIN_REMOVAL_ROUTES = [
    # the target is not spelled as the file: a glob, or the folder it lives in
    "rm .claude/hooks/dads_room_*",
    "rm .claude/hooks/*.py",
    "rm -rf .claude/hooks",
    "rm -rf .claude/hooks/",
    "rm -rf .claude",
    "mv .claude/hooks .claude/hooks_off",
    "mv .claude /tmp/c",
    "git rm -r .claude/hooks",
    # the verb is not the usual one
    f"shred -u {_H}",
    "find .claude/hooks -name dads_room_stop.py -delete",
    "find .claude/hooks -name '*.py' -delete",
    "find .claude/hooks -name '*.py' -exec rm {} ;",
    "find .claude -name dads_room_stop.py | xargs rm",
    f"dd if=/dev/null of={_H}",
    f"ln -sf /dev/null {_H}",
    f"install -m 755 /tmp/stub {_H}",
    f"perl -i -ne 'print unless /x/' {_H}",
    # the act is wrapped
    f"(rm {_H})",
    f"rm $(ls {_H})",
    f'bash -c "rm {_H}"',
    f"sh -c 'mv {_H} /tmp/x'",
    f'eval "rm {_H}"',
    f'pwsh -Command "Remove-Item {_H}"',
    # a one-liner in another language
    f"python -c \"from pathlib import Path; Path('{_H}').unlink()\"",
    f"python -c \"from pathlib import Path; Path('{_H}').write_text('')\"",
    "python -c \"import shutil; shutil.rmtree('.claude/hooks')\"",
    f"python -c \"import shutil; shutil.copy('/tmp/x','{_H}')\"",
    f"node -e \"require('fs').unlinkSync('{_H}')\"",
    f"perl -e 'unlink q({_H})'",
    # the registration rather than the file
    f"rm {_S}",
    f"mv {_S} /tmp/s",
    f"jq 'del(.hooks.Stop)' {_S} > /tmp/s && mv /tmp/s {_S}",
    f"cp /tmp/empty.json {_S}",
    f"echo '{{}}' | tee {_S}",
    f"sed -i '/\"Stop\"/d' {_S}",
]

POWERSHELL_REMOVAL_ROUTES = [
    f"ri {_H}",
    "rd .claude\\hooks -Recurse",
    "Remove-Item -Path .claude\\hooks -Recurse -Force",
    "Remove-Item .claude\\hooks\\dads_room*",
    f"del {_H}",
    f"ren {_H} gone.py",
    f"Copy-Item stub.py {_H} -Force",
    f"sc {_H} ''",
    f"Set-Content {_S} '{{}}'",
    f"'{{}}' | Out-File {_S}",
]

# Written AFTER the lists above and BEFORE any rule for them, so a pass here is not my own list agreeing with
# itself (walk-a7f95060deb7, Breaker 6: "is this a rule, or a list of the cases you happen to remember?").
HELD_OUT_BASH_ROUTES = [
    "rm -rf ./.claude/hooks",
    "rmdir .claude/hooks",
    "rm -f .claude/hooks/dads_room_*.py",
    "find . -name 'dads_room*' -delete",
    "ruby -e 'File.delete(\".claude/hooks/dads_room_stop.py\")'",
    "php -r 'unlink(\".claude/hooks/dads_room_stop.py\");'",
    'bash -lc "rm .claude/hooks/dads_room_stop.py"',
    "git mv .claude/settings.json /tmp/s.json",
    "mv -f /tmp/s.json .claude/settings.json",
    "cp -f /tmp/x.json .claude/settings.local.json",
    "truncate -s0 .claude/settings.json",
    "> .claude/settings.local.json",
    "rm -f ./.claude/settings.local.json",
    "echo done && rm -r .claude/hooks",
]
HELD_OUT_POWERSHELL_ROUTES = [
    "Move-Item .claude\\hooks C:\\tmp\\hooks",
    "Remove-Item -LiteralPath .claude\\settings.json",
    "Rename-Item .claude\\hooks hooks_off",
    "Clear-Content .claude\\settings.json",
    "Out-File -FilePath .claude\\settings.json -InputObject '{}'",
]
HELD_OUT_ORDINARY_ROUTES = [
    "ls -la .claude/hooks",
    "rm -rf .claude/cache",
    "mv .claude/hooks_notes.md /tmp/",
    "find .claude/hooks -name '*.pyc' -delete",
    "rm .claude/hooks/old_helper.py",
]

ORDINARY_ROUTES = [
    f"cat {_H}",
    f"cp {_H} /tmp/b.py",
    "rm -rf build dist node_modules/.cache",
    "rm build/*",
    "find . -name '*.pyc' -delete",
    "find . -name '*.pyc' | xargs rm",
    "sed -i 's/a/b/' README.md",
    f'sed -i \'s/"timeout": 5/"timeout": 9/\' {_S}',
    f"git checkout origin/main -- {_H} {_S}",
    "bash -c 'ls -la'",
    f"python -c \"print(open('{_S}').read())\"",
    f"cp {_S} /tmp/settings_backup.json",
]


@pytest.mark.parametrize("command", PLAIN_REMOVAL_ROUTES + HELD_OUT_BASH_ROUTES)
def test_every_plain_removal_route_is_paused(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is not None


@pytest.mark.parametrize("command", POWERSHELL_REMOVAL_ROUTES + HELD_OUT_POWERSHELL_ROUTES)
def test_every_plain_powershell_removal_route_is_paused(marker, command):
    assert pause_for("PowerShell", {"command": command}, marker) is not None


@pytest.mark.parametrize("command", ORDINARY_ROUTES + HELD_OUT_ORDINARY_ROUTES)
def test_closing_the_routes_leaves_ordinary_work_free(marker, command):
    assert pause_for("Bash", {"command": command}, marker) is None
    assert not marker.exists()


def test_wrapping_the_command_in_a_comment_keeps_the_name_but_removes_the_wiring(marker):
    edit = {
        "file_path": _S,
        "old_string": f'"python {_H}"',
        "new_string": f'"true # python {_H}"',
    }
    assert pause_for("Edit", edit, marker) is not None


def test_a_timeout_edit_that_leaves_the_wiring_string_untouched_is_not_paused(marker):
    edit = {
        "file_path": _S,
        "old_string": f'"python {_H}", "timeout": 5',
        "new_string": f'"python {_H}", "timeout": 9',
    }
    assert pause_for("Edit", edit, marker) is None


def test_a_whole_file_write_that_drops_the_stop_block_but_keeps_the_name_is_paused(
    marker, tmp_path
):
    settings = tmp_path / "settings.json"
    settings.write_text('{"hooks": {"Stop": [{"command": "python ' + _H + '"}]}}', encoding="utf-8")
    kept_name_only = '{"hooks": {"Stopped": [{"command": "python ' + _H + '"}]}}'
    assert (
        pause_for("Write", {"file_path": str(settings), "content": kept_name_only}, marker)
        is not None
    )


def test_the_real_door_writes_no_decision_for_two_ordinary_hook_edits(marker, tmp_path):
    import os
    import subprocess
    import sys

    decision = tmp_path / "decision.json"
    payload = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": ".claude/hooks/dads_room_stop.py",
            "old_string": "a",
            "new_string": "b",
        },
        "session_id": "s1",
    }
    env = {**os.environ, "CIRCLE_PAUSE_MARKER": str(marker), "CIRCLE_REMOVED_MARKER": str(decision)}
    runs = [
        subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            check=False,
        )
        for _ in range(2)
    ]
    assert [r.returncode for r in runs] == [2, 0]
    assert not decision.exists()
