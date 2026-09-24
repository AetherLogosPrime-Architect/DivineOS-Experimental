"""Two refusing gates open when the shared hook library cannot be loaded.

Both begin by sourcing the shared library with a trailing `|| exit 0`, and exit
0 is ALLOW. So a gate whose entire job is to refuse permits everything instead
-- silently, with nothing anywhere reporting that the check did not run.

MEASURED BEFORE THIS WAS WRITTEN, from two places. With the library reachable
the blanket-staging doorman exits 2 and prints its refusal. Run from a
directory where the library cannot be found, the same command comes back exit 0
with nothing on stderr at all. Same door, same input, opposite answer, and the
failing case is the quiet one.

NOT A NEW OBSERVATION, which is the actual finding. Aletheia named the class on
2026-07-26: "Three silent fail-open paths before the gate ever runs. If the
library moves, if the venv resolution breaks, if the repo root is not found --
the gate exits clean and nothing reports that enforcement did not happen." Two
months on, both gates still do it -- not because anyone disagreed, but because
the detector that finds them files new instances into a baseline, and a
baseline entry is a decision nobody has to make again.

WHY THESE TWO ARE SAFE TO CLOSE, checked rather than assumed. The detector
deliberately does not decide whether a given gate SHOULD fail closed: for some,
refusing when the library is missing would wedge the session including the edit
that repairs the library. So I read what these two actually take from it. Each
calls exactly one function, on the way out, to print a footer. THE REFUSAL DOES
NOT DEPEND ON THE LIBRARY. The load can fail and the door can still say no.

That trade is already written down one level below, inside the footer helper
itself: the refusal is the thing that must survive, the footer is the part
allowed to go missing. The call sites had inverted it. This removes a
contradiction rather than adding a rule.

BOTH DIRECTIONS ARE PINNED AND THAT IS THE POINT. This moves a gate from
fail-open to fail-CLOSED, and a wrong fail-closed is worse than the bug being
fixed -- it wedges the session and wears the same green tick. So every case
below has its opposite: with the library gone, the bad command must be REFUSED
and an innocent command must still be ALLOWED. A test asserting only the first
would pass against a door that refuses everything.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS = REPO_ROOT / ".claude" / "hooks"

BLANKET = HOOKS / "blanket-staging-doorman.sh"
PUSH_MSG = HOOKS / "push-message-carries-the-destination.sh"

BASELINE = REPO_ROOT / "scripts" / "refusal_behind_failsoft_baseline.txt"

BLOCK = 2  # the only code the harness treats as a refusal


def _bash() -> str:
    """A bash PROVEN able to run a script, by running one.

    THE FIRST VERSION CLAIMED THIS AND DID NOT DO IT. Its docstring said
    "proven able to run a script, not merely resolved by name" and its body was
    a name lookup -- the exact gap between a claim and its evidence that this
    whole branch is about, written by me hours after naming it.

    Aria measured why it mattered rather than leaving it as tidiness. The
    lookup happens to return Git bash when pytest runs from Git Bash, because
    Git's directories come first on PATH there. Put the system directory first
    -- the ordinary order outside that shell -- and the same call returns the
    WSL stub, which cannot execute a Windows-path script. Most assertions below
    would then fail loudly, which is fine. But any assertion comparing two runs
    would compare stub-failure with stub-failure and PASS.

    So the proof is made real: run something with a known answer and require
    that answer back. A shell that cannot run this cannot run a hook either.
    """
    found = shutil.which("bash")
    assert found, "no bash on PATH; this suite cannot exercise shell hooks"
    probe = subprocess.run([found, "-c", "exit 7"], capture_output=True)
    assert probe.returncode == 7, (
        f"{found} did not run a trivial script correctly (wanted 7, got "
        f"{probe.returncode}). It is resolvable by name and cannot execute, "
        "which is the WSL-stub shape; every comparison below would pass by "
        "matching one failure against another"
    )
    return found


def _run(
    script: Path,
    command: str,
    *,
    library_reachable: bool,
    background: bool = False,
) -> subprocess.CompletedProcess:
    """Run a hook with the shared library reachable or not.

    Unreachable is produced by running OUTSIDE any git repository, which is how
    the real failure arrives: the hooks derive their root from git, fall back to
    a relative path, and then source a library that is not there. Simulating it
    by deleting the library would test a case that does not happen.
    """
    tool_input: dict = {"command": command}
    if background:
        # The push gate answers 0 for any FOREGROUND push long before it
        # reaches the load. A payload without this never gets near the line
        # under test, which is how the first version of that test came to pass
        # against the unfixed gate. Aria measured it.
        tool_input["run_in_background"] = True
    payload = json.dumps({"tool_name": "Bash", "tool_input": tool_input})
    cwd = REPO_ROOT if library_reachable else Path(os.environ.get("TEMP", "/tmp"))
    return subprocess.run(
        [_bash(), str(script)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
    )


# --- the blanket-staging doorman ------------------------------------------


def test_blanket_stage_is_refused_when_the_library_is_there() -> None:
    """CONTROL. If this fails the door is broken outright and nothing below
    says anything about the library."""
    assert _run(BLANKET, "git add -A", library_reachable=True).returncode == BLOCK


def test_blanket_stage_is_still_refused_when_the_library_is_gone() -> None:
    result = _run(BLANKET, "git add -A", library_reachable=False)
    assert result.returncode == BLOCK, (
        "the door permitted a whole-tree stage because it could not load a "
        "library it only uses to print a footer. Exit 0 is allow, and nothing "
        f"was printed to say the check never ran:\n{result.stderr[:400]}"
    )


def test_an_innocent_command_is_still_allowed_when_the_library_is_gone() -> None:
    """THE OTHER DIRECTION, and the one a careless fix breaks.

    A door that starts refusing everything once its library vanishes is worse
    than the bug being repaired: it wedges the session, including the edit that
    would repair the library.
    """
    result = _run(BLANKET, "git add src/one_file.py", library_reachable=False)
    assert result.returncode == 0, (
        "a named-path stage is exactly the deciding-what-belongs this door "
        f"exists to force, and it was refused:\n{result.stderr[:400]}"
    )


# --- the push-destination gate --------------------------------------------


def test_the_push_gate_refuses_a_background_push_with_the_library_reachable() -> None:
    """CONTROL. The case the gate exists to stop, with nothing broken."""
    result = _run(PUSH_MSG, "git push", library_reachable=True, background=True)
    assert result.returncode == BLOCK, (
        "the gate did not refuse a background push even with its library "
        f"present, so nothing below says anything about the load:\n{result.stderr[:400]}"
    )


def test_the_push_gate_still_refuses_when_the_library_is_gone() -> None:
    """THE CLAIM -- and the first version of this test could not fail.

    It sent a foreground push and asserted only that the two runs AGREED. That
    gate returns 0 for any foreground push long before it reaches the load, so
    the assertion compared 0 with 0 and passed against the unfixed code. The
    docstring said it pinned "never exit 0 produced by the LOAD"; the payload
    never got near the load.

    Aria found it and measured both sides: foreground push with the library
    gone is exit 0 on main AND on this branch. Background push with the library
    gone is exit 0 on main -- the bug, a background push waved through -- and
    exit 2 here.

    So the payload now reaches the refusal, and the assertion is a verdict
    rather than an agreement. Two runs that agree can agree on nothing.
    """
    result = _run(PUSH_MSG, "git push", library_reachable=False, background=True)
    assert result.returncode == BLOCK, (
        "a background push was permitted because the gate could not load a "
        "library it only uses to print a footer. This is the exact case the "
        f"gate exists to catch:\n{result.stderr[:400]}"
    )


def test_an_innocent_command_still_passes_the_push_gate_without_its_library() -> None:
    """The other direction for this gate too: it must not refuse everything."""
    result = _run(PUSH_MSG, "ls -la", library_reachable=False, background=True)
    assert result.returncode == 0, (
        "the push gate refused a command that is not a push at all, which "
        f"means the repair turned it into a wall:\n{result.stderr[:400]}"
    )


# --- the suppression list -------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["blanket-staging-doorman.sh", "push-message-carries-the-destination.sh"],
)
def test_the_repaired_door_is_off_the_baseline(name: str) -> None:
    """THE HALF THAT IS NOT CODE, and without it the repair does not hold.

    Aria's sentence, and the rule for this change: if the file is reordered and
    the baseline entry left, the next regression walks straight back in under a
    name that already says "fine". A suppression list nobody ever subtracts
    from is a to-do list that reads as a clean bill.
    """
    listed = BASELINE.read_text(encoding="utf-8").splitlines()
    assert name not in listed, (
        f"{name} was repaired and its name is still on the suppression list, "
        "so the detector will stay quiet about it for good"
    )
