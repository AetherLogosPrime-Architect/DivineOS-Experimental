"""A background push must use the wrapper, because its answer is the one that arrives.

Andrew 2026-09-10, correcting a repair of mine: *"so the root cause would be
fixing the message so it tells you what you need to know on all sides"*.

## What this is NOT, and finding that out was most of the work

It is not a reporter. A reporter for exactly this already exists, wired, and
correct — verify-push-landed.sh has reported the remote's real state since
2026-06-04. Fed a branch that is not on origin it says so plainly. I nearly
built a second one beside it.

The reason I never saw it is that every push in the session that produced this
ran in the BACKGROUND, and on that path its output does not arrive. Measured
against that session's own background logs, where it appears zero times. What
arrives instead is a completion notice carrying an exit code — a true statement
about the command and a silent one about the remote.

So the gap was never a missing message. It was a message that does not travel
on the path I actually take, and the wrapper is the one thing that does travel,
because it puts its verdict on the last line precisely so a truncated tail
still carries it.

## Why it refuses rather than reminds

Six pushes in one session went without the wrapper, and not one of them was a
decision against it — it never entered the frame. That is what "requires
remembering at the moment of the reach" costs in practice, and truth #11 says
the answer is to take the option away rather than to write a better note.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "hooks"
    / "push-message-carries-the-destination.sh"
)


def _bash() -> str:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        shutil.which("bash"),
    ):
        if candidate and Path(candidate).is_file() and "System32" not in candidate:
            return candidate
    pytest.skip("no usable bash on this machine — could-not-look, not a pass")


def _run(command: str, background: bool | None = None) -> subprocess.CompletedProcess[str]:
    tool_input: dict[str, object] = {"command": command}
    if background is not None:
        tool_input["run_in_background"] = background
    payload = json.dumps({"tool_name": "Bash", "tool_input": tool_input})
    return subprocess.run(
        [_bash(), str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def test_a_background_push_is_refused_and_told_why() -> None:
    """The live case: this is how every push in the session went."""
    result = _run("git push origin some-branch", background=True)
    assert result.returncode == 2
    assert "does not include the destination" in result.stderr
    assert "divineos_push.sh" in result.stderr


def test_the_refusal_says_the_exit_code_is_about_the_command() -> None:
    """The reason has to travel with the refusal.

    A doorman that says only "use the other command" teaches obedience. The
    thing worth carrying is WHY the exit code cannot answer the question, which
    is that it is about a different subject.
    """
    stderr = _run("git push", background=True).stderr
    assert "EXIT CODE" in stderr
    assert "says nothing about the remote" in stderr


def test_a_foreground_push_is_left_alone() -> None:
    """There the existing reporter's output does arrive.

    Refusing it too would be ceremony over a channel that already works, and
    ceremony is what teaches me gates are ceremony.
    """
    assert _run("git push origin some-branch").returncode == 0
    assert _run("git push origin some-branch", background=False).returncode == 0


def test_the_wrapper_itself_passes() -> None:
    """A gate that refuses its own prescribed remedy is a locked box."""
    assert _run("bash scripts/divineos_push.sh origin some-branch", background=True).returncode == 0


def test_it_does_not_fire_on_everything_else() -> None:
    """Control. Without it, every assertion above survives a hook that refuses
    any command at all — and the foreground test would be the only guard left."""
    for benign in ("git status", "pytest tests/ -q", "ls"):
        assert _run(benign, background=True).returncode == 0, benign

    # And the mirror: it must still be firing on the thing it is for.
    assert _run("git push", background=True).returncode == 2
