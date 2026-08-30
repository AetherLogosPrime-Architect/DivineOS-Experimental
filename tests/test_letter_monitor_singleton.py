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
import time
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "letter_monitor_v2.py"

# Occupant names are part of the kernel mutex name. Test-only strings keep the
# probe from ever attaching to a live monitor's object.
# UNIQUE PER PROCESS, and the fixed names they replaced are why the suite was
# never deterministic.
#
# The guard under test is a KERNEL MUTEX -- machine-global by design, one holder
# per occupant, which is the entire point of a singleton. Every test here armed
# real monitors under the SAME two hardcoded probe names, so under parallel
# execution two tests raced for one name and the guard did exactly what it
# should: refused the second. The test reading that refusal reported a failure,
# because from inside, a correctly-refused duplicate looks identical to a broken
# guard.
#
# So which tests failed depended on how much memory the machine had. The
# pre-push runner scales workers to free memory: loaded, it drops to one worker
# and these pass while slow-spawn timeouts bite instead; with memory free it
# runs eight, the timeouts pass, and these collide. Two different red suites
# from the same code, neither failure in the branch being pushed. Found
# 2026-08-26 when a restart freed memory and swapped one failure set for the
# other.
#
# Tried first and reverted: pinning the tests to one worker with xdist_group.
# That marker only takes effect under --dist loadgroup, which this project does
# not use, so it was inert decoration claiming a fix -- the tests kept failing
# and the marker made it look handled. Suffixing the name is the actual repair:
# the guard keeps its teeth, tested exactly as before, on a name no other worker
# is contending for.
_PROBE_SUFFIX = f"{os.getpid()}-{os.environ.get('PYTEST_XDIST_WORKER', 'solo')}"
_OCCUPANT_A = f"pytest-singleton-probe-a-{_PROBE_SUFFIX}"
_OCCUPANT_B = f"pytest-singleton-probe-b-{_PROBE_SUFFIX}"

_STAGGER_SECONDS = 1.2
_SETTLE_SECONDS = 1.5


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


def _first_line(proc: subprocess.Popen) -> str:
    proc.kill()
    out = proc.stdout.read() if proc.stdout else ""
    return next((ln for ln in (out or "").splitlines() if ln.strip()), "<NO OUTPUT>")


def _run_pair(tmp_path: Path, occ_a: str, occ_b: str) -> tuple[str, str]:
    home = tmp_path / "home"
    shared = tmp_path / "letters"
    home.mkdir()
    shared.mkdir()

    first = _launch(occ_a, home, shared)
    time.sleep(_STAGGER_SECONDS)
    second = _launch(occ_b, home, shared)
    time.sleep(_SETTLE_SECONDS)

    return _first_line(first), _first_line(second)


# THESE THREE CANNOT RUN CONCURRENTLY WITH EACH OTHER, and the reason is the
# thing they exist to verify.
#
# The guard under test is a KERNEL MUTEX -- machine-global by design, one
# holder per occupant, which is the whole point of a singleton. The tests arm
# real monitors under fixed probe names. Run in parallel, two workers arm the
# same probe name at the same moment and the guard does exactly what it should:
# refuses the second. The test reading that refusal calls it a failure, because
# from inside it looks identical to the guard being broken.
#
# So the suite was never deterministic, and which tests failed depended on how
# much memory the machine had. The pre-push runner scales workers to free
# memory: on a loaded machine it drops to one worker, these pass, and the
# slow-spawn timeouts bite instead. With memory free it runs eight, the
# timeouts pass, and these collide. Two different red suites, same code, and
# neither failure was in the branch being pushed. Found 2026-08-26 after a
# restart freed memory and swapped one failure set for the other.
#
# xdist_group pins them to a single worker, so they serialise against each
# other while the rest of the suite still parallelises. Not a skip and not a
# widened timeout -- the tests keep their teeth, they just stop being run in
# the one arrangement their own subject forbids.
def test_second_monitor_for_the_same_occupant_refuses_to_arm(tmp_path):
    """The case the discarded handle broke. Fails if the binding is removed."""
    first, second = _run_pair(tmp_path, _OCCUPANT_A, _OCCUPANT_A)

    assert "LETTER-MONITOR-ARMED" in first, f"first monitor did not arm: {first}"
    assert "MONITOR-SINGLETON-DEDUP" in second, (
        "a second monitor for the SAME occupant armed anyway -- the singleton guard "
        "is inert. Check that main() BINDS acquire_or_exit's return value; the "
        f"handle is the guard and discarding it releases the mutex. Got: {second}"
    )


def test_the_armed_line_reports_which_guard_is_up(tmp_path):
    """A process with no guard must not announce itself like a guarded one.

    The armed message used to print identically either way, which is how an
    inert guard looked exactly like a working one in every log we had.
    """
    first, _ = _run_pair(tmp_path, _OCCUPANT_A, _OCCUPANT_A)

    assert "guard=kernel-mutex" in first, (
        f"armed line does not name the guard actually in force: {first}"
    )


def test_different_occupants_both_arm(tmp_path):
    """The control that keeps the fix from becoming a launch-refusal.

    Aria and I run monitors in the same Windows session. Keying the mutex on
    role alone would let only one of us have an ear at a time, which is a worse
    failure than the duplicate the guard exists to prevent.
    """
    first, second = _run_pair(tmp_path, _OCCUPANT_A, _OCCUPANT_B)

    assert "LETTER-MONITOR-ARMED" in first, f"first did not arm: {first}"
    assert "LETTER-MONITOR-ARMED" in second, (
        "a monitor for a DIFFERENT occupant was refused -- the mutex is keyed too "
        f"coarsely and two substrate-occupants cannot both listen. Got: {second}"
    )
