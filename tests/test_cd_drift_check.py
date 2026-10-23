"""A `cd` at the top level of a Bash line cannot move my home.

2026-10-22: `cd family/letters && cp ...` moved the app's primary folder three times, and the
bell, the hooks and a whole turn broke behind it. The measurement table is in
docs/drafts/a_cd_cannot_move_my_home_draft_2026-10-22.md. These tests drive the real check and the
real surface; the controls are the cases that must keep passing, because a refusal that also
refuses the work copies would be worse than the drift.
"""

from __future__ import annotations

import pytest

from divineos.core import cd_drift_check as check
from divineos.core.hook_surfaces import cd_drift_surface

ROOT = "C:/DIVINE OS/DivineOS-Experimental"
HOME = "C:/Users/aethe"


def refuses(command: str) -> bool:
    return check.should_refuse(command, project_root=ROOT, home=HOME)


class TestWhatItRefuses:
    @pytest.mark.parametrize(
        "command",
        [
            'cd "/c/DIVINE OS/DivineOS-Experimental/family/letters" && cp a b',
            "cd family/letters && cp a b",
            "cd family/letters; ls",
            "cd ./family/letters && ls",
            "cd /c/Users/aethe/.divineos-shared/letters && ls",
            "cd ~/.divineos-shared/letters && cat x",
            "cd /c/Users/aethe/.divineos/drawer && ls",
            "git status && cd family/letters && ls",
            "cd family/letters",
            "pushd family/letters",
            "builtin cd family/letters && ls",
            "command cd family/letters && ls",
            "{ cd family/letters; ls; }",
            "if true; then cd family/letters; fi",
            "cd -P family/letters && ls",
            "cd -- family/letters && ls",
            "cd 'C:\\DIVINE OS\\DivineOS-Experimental\\family\\letters' && ls",
        ],
    )
    def test_a_top_level_cd_into_a_folder_the_app_knows_is_refused(self, command):
        assert refuses(command), command


class TestWhatItMustLetThrough:
    @pytest.mark.parametrize(
        "command",
        [
            # controls from the measurement table: never moved the home
            "cd /c/w-gate && git status",
            "cd /c/w-draftskip && git status",
            'cd "/c/DIVINE OS/DivineOS-Experimental" && divineos briefing',
            "cd /c/Users/aethe/.divineos-shared && ls",
            # the right paths the refusal teaches
            "(cd family/letters && cp a b)",
            "( cd /c/Users/aethe/.divineos-shared/letters && ls )",
            "x=$(cd family/letters && pwd)",
            "git -C family/letters log -1",
            "cp family/letters/a family/letters/b",
            # things that are not a cd into a known folder
            "cd",
            "cd -",
            "cd ~",
            'cd "$SOME_DIR" && ls',
            "bash -c 'cd family/letters && ls'",
            "echo cd family/letters",
            "ls family/letters",
            "grep -r cd family/letters",
        ],
    )
    def test_the_work_copies_and_the_safe_forms_still_pass(self, command):
        assert not refuses(command), command

    def test_a_folder_outside_the_root_that_is_not_a_known_home_passes(self):
        assert not refuses("cd /c/Users/aethe/Downloads && ls")


class TestTheRefusalTeachesTheRightPath:
    def test_it_names_the_three_forms_and_the_way_back(self):
        text = check.refusal_message("cd family/letters && cp a b")
        assert "( cd" in text and "git -C" in text and "full path" in text
        assert "Set-Location" in text, "the way back must be named, it was the only exit"


class TestTheSurface:
    def test_it_refuses_a_bash_cd_into_a_known_folder(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", ROOT)
        out = cd_drift_surface(
            {"tool_name": "Bash", "tool_input": {"command": "cd family/letters && ls"}}
        )
        assert out is not None and out.refused

    def test_it_lets_the_control_through(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", ROOT)
        out = cd_drift_surface(
            {"tool_name": "Bash", "tool_input": {"command": "cd /c/w-gate && git status"}}
        )
        assert out is not None and not out.refused

    def test_it_ignores_other_tools(self):
        out = cd_drift_surface({"tool_name": "Write", "tool_input": {}})
        assert out is not None and not out.refused

    def test_it_is_registered_for_pre_tool_use(self):
        from divineos.core import hook_surfaces
        from divineos.core.hook_router import registered

        hook_surfaces.install()
        assert "cd_drift" in registered("PreToolUse")
