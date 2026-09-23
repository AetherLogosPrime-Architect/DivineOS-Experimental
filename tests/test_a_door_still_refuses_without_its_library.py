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
    """A bash proven able to run a script, not merely resolved by name.

    A bare name goes through CreateProcess on Windows and finds the WSL stub
    before Git bash; the stub cannot execute a Windows-path script and dies
    with exit 1. That exact confusion is what made a sibling checker report
    doors it had never reached, so it is not repeated here.
    """
    found = shutil.which("bash")
    assert found, "no bash on PATH; this suite cannot exercise shell hooks"
    return found


def _run(script: Path, command: str, *, library_reachable: bool) -> subprocess.CompletedProcess:
    """Run a hook with the shared library reachable or not.

    Unreachable is produced by running OUTSIDE any git repository, which is how
    the real failure arrives: the hooks derive their root from git, fall back to
    a relative path, and then source a library that is not there. Simulating it
    by deleting the library would test a case that does not happen.
    """
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
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


def test_the_push_gate_is_still_reachable_when_the_library_is_gone() -> None:
    """Same shape, same single footer-only dependency, same repair.

    Asserted as 'not silently allowed by the load' rather than by pinning one
    verdict, because this gate's answer depends on push state this test does
    not construct. What must never happen is exit 0 produced by the LOAD.
    """
    bad = _run(PUSH_MSG, "git push", library_reachable=False)
    good = _run(PUSH_MSG, "git push", library_reachable=True)
    assert bad.returncode == good.returncode, (
        "the gate gave a different answer with its library missing, which "
        f"means the load is deciding rather than the check: {bad.returncode} "
        f"vs {good.returncode}"
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
