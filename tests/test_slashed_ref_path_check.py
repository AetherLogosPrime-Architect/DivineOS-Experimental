"""A git argument the Windows shell rewrites is refused before it can lie.

Every row here was measured against real git on 2026-09-23 before this was
written (the table is in the module docstring). The rule is empirical, so the
table IS the specification: each mangled row must refuse and each untouched
row must pass.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from divineos.core import slashed_ref_path_check as check
from divineos.core.hook_surfaces import slashed_ref_path_surface

WINDOWS = {"env": {"MSYSTEM": "MINGW64"}, "platform": "win32"}
POSIX = {"env": {}, "platform": "linux"}


class TestTheMeasuredTable:
    @pytest.mark.parametrize(
        "command",
        [
            "git cat-file -e origin/main:.claude/settings.json",
            "git cat-file -e origin/main:.gitignore",
            "git show refs/heads/aria/x:.gitignore",
            'git cat-file -e "origin/main:.gitignore"',
            "git -C . cat-file -e origin/main:.gitignore",
            "git show origin/main:.github/workflows/ci.yml",
        ],
    )
    def test_the_rewritten_shapes_refuse(self, command: str) -> None:
        assert check.should_refuse(command, **WINDOWS)

    @pytest.mark.parametrize(
        "command",
        [
            "git cat-file -e eb27fe23:.claude/hooks/x.sh",
            "git show HEAD:.claude/settings.json",
            "git show origin/main:src/divineos/__init__.py",
            "git show origin/main:./README.md",
            "git show origin/main:README.md",
            "git log --oneline origin/main",
        ],
    )
    def test_the_untouched_shapes_pass(self, command: str) -> None:
        assert not check.should_refuse(command, **WINDOWS)


class TestTheRemedyClearsIt:
    """Wayne on the walk: applying the printed remedy to a refused command
    must make it pass -- the fix is complete, not advisory."""

    COMMAND = "git cat-file -e origin/main:.gitignore"

    def test_the_prefix_clears_the_command(self) -> None:
        assert check.should_refuse(self.COMMAND, **WINDOWS)
        assert not check.should_refuse(f"MSYS_NO_PATHCONV=1 {self.COMMAND}", **WINDOWS)

    def test_an_environment_that_already_opts_out_is_left_alone(self) -> None:
        env = {"MSYSTEM": "MINGW64", "MSYS_NO_PATHCONV": "1"}
        assert not check.should_refuse(self.COMMAND, env=env, platform="win32")

    def test_the_message_names_the_argument_and_what_git_would_receive(self) -> None:
        msg = check.refusal_message(self.COMMAND)
        assert "origin/main:.gitignore" in msg
        assert "origin\\main;.gitignore" in msg
        assert "MSYS_NO_PATHCONV=1" in msg
        assert "which_refs_carry.py" in msg


class TestItStaysOutOfTheWay:
    def test_nothing_is_refused_where_nothing_is_rewritten(self) -> None:
        assert not check.should_refuse("git cat-file -e origin/main:.gitignore", **POSIX)

    @pytest.mark.parametrize(
        "command",
        [
            "echo origin/main:.gitignore",
            "grep -rn origin/main:.claude docs",
        ],
    )
    def test_prose_mentioning_the_shape_without_git_is_not_refused(self, command: str) -> None:
        """Hinton on the walk: only git's argv is rewritten into a lie here."""
        assert not check.should_refuse(command, **WINDOWS)


class TestTheBoundaryIsNamed:
    def test_a_target_built_in_a_variable_is_not_seen(self) -> None:
        """Measured: a variable does not protect the argument from the rewrite,
        and text cannot see what the variable will hold. Pinned as a known gap
        so the passing tests above do not imply it is covered."""
        assert not check.should_refuse('r=origin/main; git cat-file -e "$r:.gitignore"', **WINDOWS)


class TestTheDoorbellDispatchesIt:
    def test_the_surface_refuses_through_the_payload(self, monkeypatch) -> None:
        monkeypatch.setenv("MSYSTEM", "MINGW64")
        monkeypatch.setattr(sys, "platform", "win32")
        out = slashed_ref_path_surface(
            {"tool_name": "Bash", "tool_input": {"command": "git show origin/main:.gitignore"}}
        )
        assert out is not None and out.refused

    def test_the_surface_ignores_other_tools(self) -> None:
        out = slashed_ref_path_surface({"tool_name": "Write", "tool_input": {}})
        assert out is not None and not out.refused

    def test_it_is_registered_for_pre_tool_use(self) -> None:
        from divineos.core import hook_surfaces
        from divineos.core.hook_router import registered

        hook_surfaces.install()
        assert "slashed_ref_path" in registered("PreToolUse")


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="the rewrite only exists on Windows")
class TestTheRealShell:
    """The provocation, run: the case this guard exists for, through bash."""

    @staticmethod
    def _git_bash() -> str:
        """Git's own bash, found beside git -- NOT a bare ``bash``, which on
        Windows resolves to the WSL stub and runs nothing. Aether's gate checker
        fell into exactly that on 2026-09-23, and so did the first run of this
        test."""
        git = shutil.which("git")
        if git:
            # cmd\git.exe and mingw64\bin\git.exe are both shipped; the bash that
            # performs the rewrite lives at the install root's bin either way.
            here = Path(git)
            for candidate in (
                here.parents[1] / "bin" / "bash.exe",
                here.parents[2] / "bin" / "bash.exe",
            ):
                if candidate.is_file():
                    return str(candidate)
        pytest.skip(
            "Git's bash was not found beside git, so the real shell cannot be provoked here"
        )
        return ""

    def test_the_shape_really_is_rewritten_and_the_remedy_really_fixes_it(self) -> None:
        repo = Path(__file__).resolve().parent.parent
        bash = self._git_bash()
        # The object name git reports for a slashed ref + dot path.
        mangled = subprocess.run(
            [bash, "-c", "git cat-file -e no/such:.gitignore"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        ).stderr
        clean = subprocess.run(
            [bash, "-c", "MSYS_NO_PATHCONV=1 git cat-file -e no/such:.gitignore"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        ).stderr
        assert "no\\such;.gitignore" in mangled
        # With the remedy git receives the argument intact and objects to the
        # made-up ref by its real name -- no backslash, no semicolon.
        assert "no/such" in clean and ";" not in clean and "\\" not in clean
