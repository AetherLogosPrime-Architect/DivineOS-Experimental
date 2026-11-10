"""One public home for 'a shell command that only looks' (2026-11-05, Aria's attack on the bell for Dad).

The house kept this list privately inside the engagement gate's checkpoint hook, with no test of its own. The bell
for Dad needs the same idea but the OPPOSITE failure direction: the engagement gate keeps its list small on purpose
(it fires slightly too often rather than let a write slip by), while the bell keeps harmless work alone (the first
false hold ends the bell, Dad). So there is one base, and the bell adds named extras. This file pins the base so the
gate's behaviour cannot drift, and the extras so the bell's can't either.
"""

from __future__ import annotations

import pytest

from divineos.core.read_only_shell import (
    BELL_EXTRA_COMMANDS,
    BELL_EXTRA_PREFIXES,
    is_read_only,
)


def _gate(command: str) -> bool:
    """The engagement gate's reading: the base only."""
    return is_read_only(command)


def _bell(command: str) -> bool:
    return is_read_only(
        command, extra_commands=BELL_EXTRA_COMMANDS, extra_prefixes=BELL_EXTRA_PREFIXES
    )


# --- the base: what the engagement gate has always counted as only looking ---


@pytest.mark.parametrize(
    "command",
    [
        "ls",
        "ls -l /tmp",
        "grep -n foo file.py",
        "cat a.txt | head -5",
        "git status",
        "git log --oneline -3",
        "git diff --stat",
        "git show HEAD",
        "git branch -a",
        "cd somewhere && ls",
        "wc -l file",
        "pwd",
        "echo hi",
    ],
)
def test_the_base_passes_plain_looking(command):
    assert _gate(command) is True, command


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git push origin b",
        "ls > out.txt",
        "cat <<EOF\nx\nEOF",
        "sed -i s/a/b/ f",
        "grep x f && python write.py",
        "rm file",
        "",
        "   ",
    ],
)
def test_the_base_refuses_anything_that_writes_or_is_unknown(command):
    assert _gate(command) is False, command


def test_the_base_is_small_on_purpose_and_does_not_know_the_bells_extras():
    for command in ("date", "gh pr list", "git ls-remote origin", "git fetch origin"):
        assert _gate(command) is False, command


# --- the bell's reading: wide, so harmless work is never held (Aria's twenty commands) ---


@pytest.mark.parametrize(
    "command",
    [
        "ls",
        "ls -l /tmp",
        "git status",
        "git log --oneline -3",
        "git diff --stat",
        "git show HEAD",
        "cat file",
        "grep x file",
        "head -5 file",
        "wc -l file",
        "date",
        "tail -20 file",
        "pwd",
        "echo hi",
        "gh pr list",
        "gh pr view 842",
        "git ls-remote origin",
        "git fetch origin",
        "git worktree list",
        "git branch -a",
        "divineos linkage warm",
    ],
)
def test_the_bell_leaves_plain_looking_commands_alone(command):
    assert _bell(command) is True, command


@pytest.mark.parametrize(
    "command",
    [
        "git push origin some-branch",
        "git commit -m x",
        "date && git push origin b",
        "gh pr merge 842",
        "gh pr create",
        "gh pr close 842",
        "git worktree add C:/x",
        "git worktree remove C:/x",
        "git remote add x y",
        "date > out.txt",
        "python write.py",
    ],
)
def test_the_bell_still_holds_anything_that_changes_something(command):
    assert _bell(command) is False, command
