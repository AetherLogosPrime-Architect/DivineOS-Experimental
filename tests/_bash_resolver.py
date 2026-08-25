"""Where to find a bash that actually runs. One home, unshadowable.

NOT in conftest.py, and that is the point: tests/_archive/conftest.py
shadows the live conftest by name on the import path, so
 resolved to the ARCHIVE copy and the import
failed only when the full suite was collected. Passed in isolation,
broke in the suite -- two files with one name, resolution decided by
path order. Same shape as everything else found tonight.
"""

from __future__ import annotations

import shutil


# Where Git Bash actually lives on this box, in the order worth trying. The
# bare name "bash" resolves to the WSL relay stub here, which fails with
# "execvpe(/bin/bash) failed" and exit 1 -- see bash_executable() below.
_GIT_BASH_DIRS = (
    r"C:\Program Files\Git\bin",
    r"C:\Program Files\Git\usr\bin",
)


def bash_executable() -> str | None:
    """A bash that actually runs, or None. THE one place tests ask this.

    WHY THIS EXISTS, and it is two findings meeting.

    Aria measured it 2026-08-25 from her side: three of her parity helpers
    invoked a hook as ``["bash", str(hook)]``, which from Python on this
    machine resolves to a WSL relay stub. It exits 1 having produced nothing.
    Her helper read that empty output as *the hook chose to stay silent* and
    compared it to an adapter that was also silent. Green. Could-not-run
    reported as nothing-to-say, inside the harness written to verify the
    declared-state design we built this session for exactly that class.

    From my side the same shape had already been GUARDED rather than missed --
    three test files probe with ``bash -c "echo ok"`` and skip when it fails,
    with a reason naming the relay stub explicitly. Honest, and better than a
    false green by a wide margin.

    And still zero coverage. Measured: four tests skipped on every run of this
    box, for as long as the guard has existed. An honest skip is not a passing
    test -- it is an absence that announces itself, which is the correct
    failure mode and not a substitute for the check.

    The fix was ALREADY IN THE HOUSE, five times. Five other test files reach
    for the Git Bash directory explicitly, each carrying its own copy of the
    same literal paths. The knowledge existed five times over and none of the
    three skipping files had it. Sixth time in one night the answer was
    already here and unfound.

    One place now. Returns None only when there is genuinely no working bash,
    which is a real skip rather than a resolution failure wearing one.
    """
    for directory in _GIT_BASH_DIRS:
        found = shutil.which("bash", path=directory)
        if found:
            return found
    # PATH last, and only if it actually RUNS. The relay stub is on PATH and
    # answers `which`, so presence is not evidence -- it has to execute.
    on_path = shutil.which("bash")
    if not on_path:
        return None
    try:
        import subprocess

        probe = subprocess.run(
            [on_path, "-c", "echo ok"], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return on_path if probe.returncode == 0 and probe.stdout.strip() == "ok" else None
