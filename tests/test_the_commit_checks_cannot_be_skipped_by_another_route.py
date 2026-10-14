"""The commit checks could be skipped by a route the gate could not see.

2026-10-13. I finished a merge commit with ``git -c core.hooksPath=/dev/null commit`` and
every pre-commit check was skipped. The --no-verify gate said nothing, because it read the
word right after ``git`` as the subcommand and that word was ``-c``. Dad: "fix why you were
even able to skip it in the first place so you cant lol".

The same blind spot hid ``git -C some/folder commit --no-verify`` (a form I type all day),
so both are pinned here, together with the over-fire cases: a gate that blocks ordinary
``git -C folder commit`` teaches me to reach for the escape hatch, which is the failure it
exists to prevent arriving by the other door.

An honest skip is still possible and still counted: the same named reason as --no-verify.
"""

from __future__ import annotations

import pytest

from divineos.core.no_verify_cost import decide


def _denied(command: str) -> bool:
    return decide({"command": command}) is not None


@pytest.mark.parametrize(
    "command",
    [
        "git -c core.hooksPath=/dev/null commit -m x",
        "git -c core.hookspath=/nowhere commit -m x",
        'cd "C:/DIVINE OS/DivineOS-Experimental" && git -c core.hooksPath=/dev/null commit --no-edit',
        "git -ccore.hooksPath=/dev/null commit -m x",
        "git -c core.hooksPath=/dev/null push origin b",
        "git -C C:/w-rest -c core.hooksPath=/dev/null commit -m x",
        "git --config-env=core.hooksPath=HOOKS commit -m x",
        "git config core.hooksPath /dev/null",
        "git config --global core.hooksPath /dev/null",
        "git -C C:/w-rest commit --no-verify -m x",
        "git -C C:/w-rest push --no-verify",
        "git --no-pager -C C:/w-rest commit -n -m x",
    ],
)
def test_every_route_that_turns_the_checks_off_is_stopped(command: str) -> None:
    assert _denied(command), f"the gate went silent on: {command}"


@pytest.mark.parametrize(
    "command",
    [
        "git -C C:/w-rest commit -m x",
        "git -C C:/w-rest add -A && git -C C:/w-rest commit -q -m x",
        "git -c user.name=t commit -m x",
        "git -c core.autocrlf=false commit -m x",
        "git --no-pager log -n 5",
        "git -C C:/w-rest push -n origin b",
        "git config core.hooksPath",
        "git config --get core.hooksPath",
        "git config --unset core.hooksPath",
        "git -C C:/w-rest status",
    ],
)
def test_ordinary_use_of_the_same_options_is_not_stopped(command: str) -> None:
    assert not _denied(command), f"the gate over-fired on: {command}"


def test_an_honest_skip_with_a_named_reason_still_passes() -> None:
    cmd = (
        'DIVINEOS_NO_VERIFY_REASON="the gate is wrong about generated docs" '
        "git -c core.hooksPath=/dev/null commit -m x"
    )
    assert not _denied(cmd)


@pytest.mark.parametrize(
    "command",
    [
        'bash -c "git commit --no-verify -m x"',
        "sh -c 'git -c core.hooksPath=/dev/null commit -m x'",
        'eval "git commit --no-verify -m x"',
        'bash -lc "cd /x && git commit -n -m y"',
        "bash -c \"bash -c 'git commit --no-verify -m x'\"",
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m x",
    ],
)
def test_a_skip_inside_a_quoted_command_or_the_environment_is_stopped(command: str) -> None:
    """Found by TESTING the first fix: `bash -c "git commit --no-verify"` is one quoted token,
    so neither the old gate nor the option-stepping saw a commit in it."""
    assert _denied(command), f"the gate went silent on: {command}"


@pytest.mark.parametrize(
    "command",
    [
        'bash -c "git commit -m x"',
        'bash -c "echo hello"',
        "bash script.sh",
        'grep -c "git commit --no-verify" notes.txt',
        'echo "git commit --no-verify"',
        "GIT_CONFIG_KEY_0=user.name git commit -m x",
    ],
)
def test_talking_about_a_skip_or_running_an_ordinary_shell_is_not_stopped(command: str) -> None:
    assert not _denied(command), f"the gate over-fired on: {command}"


@pytest.mark.parametrize(
    "command",
    [
        "/usr/bin/git commit --no-verify -m x",
        "git.exe commit --no-verify -m x",
        "C:/Program Files/Git/bin/git.exe -c core.hooksPath=/dev/null commit -m x",
        "GIT_CONFIG_PARAMETERS=\"'core.hookspath=/dev/null'\" git commit -m x",
        'env FOO=1 bash -c "git commit --no-verify -m x"',
        'sudo bash -lc "git commit -n -m x"',
    ],
)
def test_a_path_qualified_git_and_the_packed_environment_route_are_stopped(command: str) -> None:
    """Aria's cold read of 656: the gate was anchored to the literal word `git`."""
    assert _denied(command), f"the gate went silent on: {command}"


@pytest.mark.parametrize(
    "command",
    [
        'echo bash -c "git commit --no-verify -m x"',
        'bash run.sh -c "git commit --no-verify -m x"',
        "GIT_CONFIG_PARAMETERS=\"'user.name=t'\" git commit -m x",
        "/usr/bin/git commit -m x",
    ],
)
def test_a_shell_word_that_is_not_running_a_shell_is_not_stopped(command: str) -> None:
    assert not _denied(command), f"the gate over-fired on: {command}"


@pytest.mark.parametrize(
    "command",
    [
        "git merge --no-verify topic",
        "git am --no-verify x.patch",
        "git rebase --no-verify main",
        "git commit --no-verif -m x",
        "git commit --no-v -m x",
        "git commit -nm x",
        "git commit -an -m x",
        "git config alias.c 'commit --no-verify'",
        "git config alias.c 'commit --no-verif'",
        "git -c alias.c='commit --no-verify' c",
    ],
)
def test_the_other_routes_aletheia_found_are_stopped(command: str) -> None:
    """Aletheia's hold on 656: another command that runs the checks, a shortened option
    git still accepts (proven to skip a real hook), and an alias that carries the skip."""
    assert _denied(command), f"the gate went silent on: {command}"


@pytest.mark.parametrize(
    "command",
    [
        "git merge -n topic",
        "git merge topic",
        "git commit -am x",
        "git commit --no-edit",
        "git commit --no-gpg-sign -m x",
        "git config alias.st status",
        "git config --get alias.c",
        "git -c user.name=t status",
    ],
)
def test_the_widened_gate_does_not_over_fire(command: str) -> None:
    assert not _denied(command), f"the gate over-fired on: {command}"


def test_control_the_plain_form_is_still_stopped() -> None:
    # If the option-stepping broke the old path, the tests above could pass for the wrong reason.
    assert _denied("git commit --no-verify -m x")
    assert not _denied("git commit -m x")
