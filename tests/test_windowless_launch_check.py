"""A launch that gives every child program its own window must be refused.

2026-10-07: a test sweep started by a launcher with the detached flags opened one
console window per child program, hundreds of them, over Dad's screen ("i couldnt
even see anything i was typing blind"). The check reads the text of the launch,
the one place anything can act, because nothing can see his screen.

Controls first: a check that refused every launch would pass every refusal test, so
the cases that MUST be allowed are as numerous as the ones that must not be. The
routes the check cannot see are pinned as OPEN, by name, so they read as a gap and
never as coverage.

The flag names are built from pieces: this file must not trip its own check.
"""

from __future__ import annotations

import pytest

from divineos.core import hook_router as hr
from divineos.core import hook_surfaces as hs
from divineos.core import windowless_launch_check as wl

DETACHED = "DETACHED" + "_PROCESS"
NEW_CONSOLE = "CREATE_NEW" + "_CONSOLE"


def _refuses(tool: str, **tool_input) -> bool:
    got = wl.should_refuse(tool, tool_input)
    # strict: a None slipping out of a branch is a bug a bare truthiness check hides
    assert got is True or got is False, got
    return got


class TestWhatItRefuses:
    def test_a_python_launcher_written_to_a_file(self):
        body = f"import subprocess\nsubprocess.Popen(cmd, creationflags={DETACHED})\n"
        assert _refuses("Write", file_path="C:/x/detach.py", content=body)

    def test_the_new_console_flag_is_refused_too(self):
        assert _refuses(
            "Write", file_path="launch.ps1", content=f"# {NEW_CONSOLE}\nStart-Process x"
        )

    def test_an_edit_that_adds_the_flag_to_a_code_file(self):
        assert _refuses("Edit", file_path="run.py", new_string=f"flags = {DETACHED}")

    def test_a_multiedit_that_adds_it_in_one_of_its_edits(self):
        edits = [
            {"old_string": "a", "new_string": "b"},
            {"old_string": "c", "new_string": DETACHED},
        ]
        assert _refuses("MultiEdit", file_path="run.py", edits=edits)

    def test_a_shell_command_that_launches_with_the_flag(self):
        cmd = f"python -c \"import subprocess; subprocess.Popen(['x'], creationflags={DETACHED})\""
        assert _refuses("Bash", command=cmd)

    def test_a_powershell_command_that_launches_with_the_flag(self):
        assert _refuses("PowerShell", command=f'python -c "Popen(creationflags={DETACHED})"')

    def test_the_flag_name_in_lower_case_is_still_the_flag(self):
        assert _refuses("Write", file_path="x.py", content=f"creationflags = {DETACHED.lower()}")

    def test_a_code_file_under_tests_is_not_a_hiding_place(self):
        """The exemptions are prose and reads, never a folder name."""
        assert _refuses("Write", file_path="tests/helper.py", content=f"x = {DETACHED}")


class TestWhatItMustAllow:
    """The controls. If any of these is refused the check is a wall, not a door."""

    def test_a_markdown_note_that_mentions_the_flag(self):
        assert not _refuses("Write", file_path="notes/why.md", content=f"never use {DETACHED}")

    def test_a_text_file_that_mentions_the_flag(self):
        assert not _refuses("Write", file_path="why.txt", content=DETACHED)

    def test_a_search_that_only_names_the_flag(self):
        assert not _refuses("Bash", command=f"grep -rn {DETACHED} src")

    def test_a_command_that_names_the_flag_but_launches_nothing(self):
        assert not _refuses("PowerShell", command=f"Select-String -Pattern {DETACHED} -Path x")

    def test_an_ordinary_launch_with_no_flag(self):
        assert not _refuses("Bash", command="python -m pytest tests -q")

    def test_an_ordinary_code_write(self):
        assert not _refuses(
            "Write", file_path="run.py", content="import subprocess\nsubprocess.run(cmd)"
        )

    def test_the_quiet_flag_on_its_own_is_fine(self):
        body = "subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW)"
        assert not _refuses("Write", file_path="run.py", content=body)

    @pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Task", "TodoWrite"])
    def test_tools_that_launch_nothing_pass(self, tool):
        assert not _refuses(tool, command=DETACHED, content=DETACHED, file_path="x.py")

    def test_an_empty_payload(self):
        assert wl.should_refuse("Bash", None) is False
        assert wl.should_refuse("Write", {}) is False

    def test_a_launch_word_with_no_flag_is_not_enough(self):
        """Found by changing the check line by line: nothing pinned this branch, so a
        check that refused every launch would have passed."""
        assert not _refuses(
            "Bash", command="python -c \"import subprocess; subprocess.run(['x'])\""
        )
        assert not _refuses("PowerShell", command="Start-Process notepad")

    def test_a_read_only_search_naming_both_the_flag_and_a_launcher_word_passes(self):
        """The read-only exemption itself: it only matters when both are present."""
        assert not _refuses("Bash", command=f"grep -rn 'Popen.*{DETACHED}' src")

    def test_if_the_read_only_judge_cannot_be_loaded_the_command_is_not_waved_through(
        self, monkeypatch
    ):
        import sys

        monkeypatch.setitem(sys.modules, "divineos.hooks.pre_tool_use_gate", None)  # import fails
        assert wl._is_readonly(f"grep -rn 'Popen.*{DETACHED}' src") is False

    def test_an_odd_item_in_a_multiedit_does_not_crash_the_check(self):
        edits = ["not a mapping", None, {"new_string": "x = 1"}]
        assert not _refuses("MultiEdit", file_path="run.py", edits=edits)


class TestWhatItCannotSeeAndSaysSo:
    """OPEN ROUTES. These assert the check does NOT refuse them today. They are here so
    the gap reads as a gap: the fix is quiet children by default, not a cleverer
    string match."""

    def test_OPEN_the_flag_as_a_hex_number(self):
        assert not _refuses(
            "Write", file_path="x.py", content="subprocess.Popen(c, creationflags=0x8)"
        )

    def test_OPEN_the_flag_built_from_two_strings(self):
        body = 'name = "DETACHED" + "_PROCESS"\nflag = getattr(subprocess, name)\nPopen(c, creationflags=flag)'
        assert not _refuses("Write", file_path="x.py", content=body)


def test_the_refusal_says_what_happened_and_the_way_through():
    msg = wl.refusal_message()
    assert "typing blind" in msg
    assert "run_in_background" in msg
    assert "CREATE_NO_WINDOW" in msg


class TestTheSurface:
    def test_it_refuses_through_the_surface_with_the_message(self):
        out = hs.windowless_launch_surface(
            {"tool_name": "Write", "tool_input": {"file_path": "x.py", "content": DETACHED}}
        )
        assert out is not None and out.refused
        assert "WINDOWS ON DAD'S SCREEN" in out.reason

    def test_it_stays_quiet_on_an_ordinary_write(self):
        out = hs.windowless_launch_surface(
            {"tool_name": "Write", "tool_input": {"file_path": "x.py", "content": "x = 1"}}
        )
        assert out is not None and not out.refused

    def test_a_broken_check_says_so_and_does_not_read_as_a_pass(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("check broke")

        monkeypatch.setattr(wl, "should_refuse", boom)
        out = hs.windowless_launch_surface(
            {"tool_name": "Write", "tool_input": {"file_path": "x.py", "content": DETACHED}}
        )
        assert out is not None and out.state == "could-not-run"
        assert "unguarded" in out.error

    def test_install_registers_it_on_pretooluse(self):
        hs.install()
        assert "windowless_launch" in hr.registered("PreToolUse")
