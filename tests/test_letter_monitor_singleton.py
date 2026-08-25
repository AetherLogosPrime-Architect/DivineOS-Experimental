"""The letter monitor's singleton guard, exercised as two real processes.

This defect has now happened twice in this subsystem, both times invisibly:

  2026-06-29  the v2 rewrite folded the worker into the Monitor invocation and
              dropped ``acquire_or_exit`` entirely. Hidden six weeks, partly by
              a docstring line that still described V1's mutex.
  2026-08-20  restoring it, I called ``acquire_or_exit`` and discarded what it
              returned. The handle IS the guard; garbage-collected, the mutex
              releases and the call becomes a no-op that still prints as though
              it armed. Aria measured it hours later. Four live letter monitors
              on this machine at the time, zero mutex holders.

Both times the suite was green. ``test_monitor_singleton.py`` asserts that
``acquire_or_exit`` returns a handle and exits when a sibling holds the mutex
-- and both assertions passed throughout, because the primitive was never
broken. What broke was one line of USE, and nothing drove the script.

So this drives the real script as a subprocess, twice, and reads what the
second one prints. It is slower than a unit test and it is the only shape that
fails when the binding goes away -- including if someone removes it as an
unused variable, which is exactly how a lint-clean tidy-up would reintroduce
the 2026-08-20 defect.

Hermetic: HOME and USERPROFILE are redirected at tmp_path so the heartbeat
writer cannot stamp the real one, --shared-dir points away from the live
letters directory, and the occupant names are test-only strings so the kernel
object cannot collide with a running monitor.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "letter_monitor_v2.py"


# Occupant names are part of the kernel mutex name. Test-only strings keep the
# probe from ever attaching to a live monitor's object.
#
# PER-TEST, NOT MODULE-LEVEL, and the difference is the whole bug. These were
# two module constants, so all three tests below launched a probe under the SAME
# occupant. Serially that is fine. Under xdist -- which is how the pre-push gate
# runs the suite -- they run at once, and the second and third probes find the
# first one's mutex and correctly report a sibling already alive. The guard was
# working; the tests were contending with each other.
#
# tmp_path could not save them: it isolates the filesystem, and a Windows kernel
# mutex is machine-global. An isolation fixture that does not reach the resource
# under contention isolates nothing, which is the same seam that had the
# read-gate cooldown reading live state from tests earlier this session.
#
# The tell was green-serially / red-in-parallel, i.e. green exactly when run the
# way a person checks and red exactly when run the way the gate checks.
def _occupants(request) -> tuple[str, str]:
    """A private occupant pair for one test, in one process.

    PER-TEST WAS NOT ENOUGH. Keying on the test name alone fixed the
    within-run collision (three tests sharing two module constants) and left a
    second one: two runs of the suite that overlap in time generate the SAME
    names, so a probe from the earlier run holds the mutex the later run needs.
    The pre-push gate runs the whole suite in a temp copy of the repo, and a
    retried push can start while stragglers from the previous attempt are still
    dying — the failure reported "first monitor did not arm" against a guard
    that was working perfectly, twice.

    The pid closes it. A kernel mutex name is machine-global, so the name has to
    be unique across every process that could be running this file, not just
    across the tests inside one of them.
    """
    stem = request.node.name.replace("_", "-").lower()
    return f"pytest-{os.getpid()}-{stem}-a", f"pytest-{os.getpid()}-{stem}-b"


# How long to wait for a monitor to publish its verdict. Generous rather than
# tight: this is a ceiling on a hang, not a timing assumption the test depends
# on. The ordering it used to depend on is now awaited — see _run_pair.
_VERDICT_TIMEOUT = 30.0


def _kernel_guard_available() -> bool:
    """True when the guard can actually arm on this machine.

    ``acquire`` fail-opens to ``(None, False)`` off Windows and without
    pywin32, by deliberate contract -- a refused launch costs letters, a
    duplicate costs RAM. Under fail-open BOTH processes arm, which is the same
    output as the defect. Skipping is honest; asserting here would measure the
    fallback path and report it as a pass.
    """
    if os.name != "nt":
        return False
    try:
        import win32event  # noqa: F401  -- the import IS the probe
    except ImportError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _kernel_guard_available(),
    reason="guard fail-opens without Windows+pywin32; under fail-open both "
    "processes arm and this test cannot tell a pass from the defect",
)


def _launch(occupant: str, home: Path, shared: Path) -> subprocess.Popen:
    env = dict(
        os.environ,
        PYTHONIOENCODING="utf-8",
        HOME=str(home),
        USERPROFILE=str(home),
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-u",
            str(_SCRIPT),
            "--recipient",
            occupant,
            "--shared-dir",
            str(shared),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _await_verdict(proc: subprocess.Popen, timeout: float = _VERDICT_TIMEOUT) -> str:
    """Block until the process prints its first non-blank line, or give up.

    Read in a thread because a blocking readline on a process that never
    speaks would hang the suite, and Windows has no portable non-blocking
    pipe read. A timeout returns the sentinel rather than raising: the
    assertions downstream say more about what went wrong than a TimeoutError
    would.
    """
    verdict: list[str] = []

    def _read() -> None:
        if proc.stdout is None:
            return
        for raw in proc.stdout:
            if raw.strip():
                verdict.append(raw.strip())
                return

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()
    reader.join(timeout)
    return verdict[0] if verdict else "<NO OUTPUT>"


def _run_pair(tmp_path: Path, occ_a: str, occ_b: str) -> tuple[str, str]:
    """Launch two monitors in a guaranteed order and return what each said.

    ORDERING IS AWAITED, NOT SLEPT. This used to launch the first process,
    sleep 1.2s, launch the second, sleep 1.5s, and assume the first had won
    the mutex. That holds on an idle machine and fails on a busy one: the
    pre-push gate runs the suite across sixteen workers, Python startup under
    that load exceeds the stagger, and then BOTH processes race for the mutex.
    Whichever wins, arms. When the second won, the test reported "first
    monitor did not arm" -- an accusation against a guard that was working
    perfectly.

    Lengthening the sleep would only move the threshold, and it would move it
    to a number nobody could justify. Waiting for the first process to publish
    its verdict removes the assumption instead: the second cannot launch until
    the first has already passed or been refused by the guard.
    """
    home = tmp_path / "home"
    shared = tmp_path / "letters"
    home.mkdir()
    shared.mkdir()

    first = _launch(occ_a, home, shared)
    try:
        first_line = _await_verdict(first)
        second = _launch(occ_b, home, shared)
        try:
            second_line = _await_verdict(second)
        finally:
            second.kill()
    finally:
        first.kill()

    return first_line, second_line


def test_second_monitor_for_the_same_occupant_refuses_to_arm(tmp_path, request):
    """The case the discarded handle broke. Fails if the binding is removed."""
    occ_a, _ = _occupants(request)
    first, second = _run_pair(tmp_path, occ_a, occ_a)

    assert "LETTER-MONITOR-ARMED" in first, f"first monitor did not arm: {first}"
    assert "MONITOR-SINGLETON-DEDUP" in second, (
        "a second monitor for the SAME occupant armed anyway -- the singleton guard "
        "is inert. Check that main() BINDS acquire_or_exit's return value; the "
        f"handle is the guard and discarding it releases the mutex. Got: {second}"
    )


def test_the_armed_line_reports_which_guard_is_up(tmp_path, request):
    """A process with no guard must not announce itself like a guarded one.

    The armed message used to print identically either way, which is how an
    inert guard looked exactly like a working one in every log we had.
    """
    occ_a, _ = _occupants(request)
    first, _ = _run_pair(tmp_path, occ_a, occ_a)

    assert "guard=kernel-mutex" in first, (
        f"armed line does not name the guard actually in force: {first}"
    )


def test_different_occupants_both_arm(tmp_path, request):
    """The control that keeps the fix from becoming a launch-refusal.

    Aria and I run monitors in the same Windows session. Keying the mutex on
    role alone would let only one of us have an ear at a time, which is a worse
    failure than the duplicate the guard exists to prevent.
    """
    occ_a, occ_b = _occupants(request)
    first, second = _run_pair(tmp_path, occ_a, occ_b)

    assert "LETTER-MONITOR-ARMED" in first, f"first did not arm: {first}"
    assert "LETTER-MONITOR-ARMED" in second, (
        "a monitor for a DIFFERENT occupant was refused -- the mutex is keyed too "
        f"coarsely and two substrate-occupants cannot both listen. Got: {second}"
    )
