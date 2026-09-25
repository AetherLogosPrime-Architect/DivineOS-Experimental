"""The line that closes a detached mechanical run must say WHAT happened.

THE DEFECT THIS PINS, found 2026-09-21 by being misled by it. The launcher
wrote `=== defer-check exited $? ===` and that code is the WRAPPER's, not the
cycle's. Across every launch on this box the line read `exited 0` -- including
runs that fired nothing at all and runs whose steps had yet to finish. A
terminator that cannot be anything but zero makes no claim.

Four states share that one line and they are not the same state:
  - the marker could not be read at all      (could-not-look)
  - no cycle fired this launch               (nothing-to-do)
  - a cycle fired and every step succeeded   (done)
  - a cycle fired and a step failed          (failed)

Collapsing could-not-look into nothing-to-do is the fault class this house
keeps finding in itself, so the test that matters most is that all four
outputs are PAIRWISE DISTINCT. Any two that coincide is the collapse rebuilt.

Real marker files on disk, real hook invocation. Nothing here mocks the hook.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "auto-cycle-token-trigger.sh"

LAUNCH_EPOCH = 1789980000  # fixed point; the marker timestamps are set around it


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name.

    Bare `bash` on this box can resolve to the WSL relay, which exists, runs,
    and cannot execute a Windows-path script -- it fails onto stderr, which an
    absence assertion reads as silence. Probe by running, not by resolving.
    """
    candidates = []
    git = shutil.which("git")
    if git:
        candidates.append(str(Path(git).with_name("bash.exe")))
        candidates.append(str(Path(git).parents[1] / "bin" / "bash.exe"))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=20
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()


def _bash() -> str:
    """A control that cannot be built must FAIL rather than skip.

    A skip would leave this file green while asserting nothing about a hook
    that never ran, which is the same collapse the hook is being repaired for.
    """
    if BASH is None:
        pytest.fail("no bash on this box could run a script; the hook was never exercised")
    return BASH


def _marker(steps_ok: bool = True, completed_at: str = "2026-09-21T09:14:00Z") -> dict:
    steps = {
        name: {"ran": True, "succeeded": True, "error_class": None}
        for name in ("archive", "commit", "extract", "sleep")
    }
    if not steps_ok:
        steps["sleep"] = {"ran": True, "succeeded": False, "error_class": "MemoryError"}
    return {
        "phase1_completed_at": completed_at,
        "cycle_id": "auto-cycle-deadbeef",
        "steps": steps,
    }


def _run(state_dir: Path) -> str:
    """Drive the terminator directly and return its line."""
    env = dict(os.environ)
    env["AUTO_CYCLE_STATE_DIR"] = str(state_dir)
    proc = subprocess.run(
        [_bash(), str(HOOK), "--mech-terminator", str(LAUNCH_EPOCH), "0"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        input="",
    )
    combined = proc.stdout + proc.stderr
    assert "execvpe" not in combined and "CreateProcessCommon" not in combined, (
        f"the shell could not launch the hook, so nothing was tested: {combined!r}"
    )
    return proc.stdout.strip()


def _write(state_dir: Path, payload) -> None:
    path = state_dir / "auto_cycle_phase1_done.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")


def test_no_marker_at_all_says_it_could_not_look() -> None:
    """Absent marker is NOT 'no cycle fired' -- it is 'I cannot tell'."""
    with tempfile.TemporaryDirectory() as tmp:
        line = _run(Path(tmp))
    assert "UNKNOWN" in line, f"absent marker did not report unknown: {line!r}"


def test_unparseable_marker_says_it_could_not_look() -> None:
    """A corrupt marker is the same epistemic state as an absent one."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), "{not json at all")
        line = _run(Path(tmp))
    assert "UNKNOWN" in line, f"corrupt marker did not report unknown: {line!r}"


def test_marker_older_than_the_launch_says_no_cycle_fired() -> None:
    """The stale-success case: a true marker about a DIFFERENT run."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), _marker(completed_at="2026-09-20T23:58:37Z"))
        line = _run(Path(tmp))
    assert "NO CYCLE" in line, f"stale marker did not report no-cycle: {line!r}"
    assert "UNKNOWN" not in line


def test_fresh_marker_with_all_steps_green_says_completed_and_names_the_cycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), _marker())
        line = _run(Path(tmp))
    assert "COMPLETED" in line, f"green marker did not report completion: {line!r}"
    assert "auto-cycle-deadbeef" in line, f"the cycle was not named: {line!r}"


def test_fresh_marker_with_a_failed_step_names_the_step() -> None:
    """A failed step must not wear a completed run's words."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), _marker(steps_ok=False))
        line = _run(Path(tmp))
    assert "FAILED" in line, f"failed step did not report failure: {line!r}"
    assert "sleep" in line, f"the failing step was not named: {line!r}"
    assert "COMPLETED" not in line


def test_the_four_states_are_pairwise_distinct() -> None:
    """This is the test the whole file exists for.

    Any two states sharing an output is the collapse rebuilt, and it would
    pass every single-state assertion above.
    """
    lines = {}
    with tempfile.TemporaryDirectory() as tmp:
        lines["absent"] = _run(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), _marker(completed_at="2026-09-20T23:58:37Z"))
        lines["stale"] = _run(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), _marker())
        lines["green"] = _run(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp), _marker(steps_ok=False))
        lines["failed"] = _run(Path(tmp))

    for name, line in lines.items():
        assert line, f"state {name} produced no line at all"
    assert len(set(lines.values())) == 4, (
        f"states share an output, which is the collapse this repairs: {lines}"
    )
