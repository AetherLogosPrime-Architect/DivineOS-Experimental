"""Proof-test (pile round seven): the doorbell re-arm command is not on the shared exit list.

The Stop guard prints `bash scripts/letter_doorbell.sh aether` as the way out of its own hold. The
shared exit list (`.claude/hooks/lib/remedy_allowlist.sh`) says its bar is that some gate PRINTS the
command in its own block message, and that no gate may block another gate's prescribed exit. The
re-arm command is printed by a gate and is not on the list, so a gate that consults the list (the
read-gate doorman is one, per the old notes) can hold the re-arm. Pile rows psf-22017b26,
psf-83419786, psf-ce2cc13b, psf-6319169c, psf-ea755cc2.

This test does not change the list. The shared library exits 0 itself when the command IS an exit
and falls through when it is not; the test reads that behaviour in a child shell.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

BASH = bash_executable()
pytestmark = pytest.mark.skipif(BASH is None, reason="no working bash on this machine")

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / ".claude" / "hooks" / "lib" / "remedy_allowlist.sh"
STOP_GUARD = REPO / ".claude" / "hooks" / "letter_doorbell_alive_stop.py"
BELL = "bash scripts/letter_doorbell.sh aether"


def passes_through(command: str) -> bool:
    """True when the shared library treats the command as somebody's prescribed exit."""
    payload = json.dumps({"tool_input": {"command": command}})
    # as_posix: backslashes inside the double quotes would be eaten by bash on Windows.
    script = f'HOOK_NAME=probe; source "{LIB.as_posix()}"; remedy_pass_through "$1"; echo CONTINUED'
    done = subprocess.run(
        [BASH, "-c", script, "_", payload], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return "CONTINUED" not in done.stdout


def test_control_a_listed_exit_passes_through():
    assert passes_through('divineos goal add "x"')


def test_control_ordinary_work_does_not_pass_through():
    assert not passes_through("rm -rf x")


def test_control_a_gate_does_print_the_bell_command_as_its_way_out():
    text = STOP_GUARD.read_text(encoding="utf-8")
    assert "bash scripts/letter_doorbell.sh" in text


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: the re-arm command a gate prints is not on the shared exit list "
    "(psf-22017b26, psf-83419786)",
)
def test_the_bell_rearm_a_gate_prints_is_on_the_exit_list():
    assert passes_through(BELL), (
        f"`{BELL}` is printed by the Stop guard as its way out but the shared exit list "
        "does not carry it, so a gate that consults the list can still hold it"
    )
