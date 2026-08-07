"""System-load pre-flight check for resource-heavy jobs.

Root fix for the class of failure that crashed Andrew's machine 2026-07-30
(and nearly crashed it 2026-07-13). Class: multiple concurrent pytest suites
firing from parallel background pushes eating CPU/memory until the machine
crashes.

Aether's ``subprocess_jobs.py`` (2026-07-13) covers ORPHAN pytest processes
after a parent crash — the Windows Job Object kills children when parent
dies. This module covers the class-neighbor: PREVENTING the crash-cause
by refusing to spawn a new resource-heavy job when the system is already
too loaded to safely accept one.

Design (Andrew 2026-07-30):

- Check current system memory via ``psutil.virtual_memory()``.
- If less than SAFE_FREE_BYTES bytes are free, refuse loudly with the
  concrete numbers. Do not spawn pytest.
- Otherwise proceed silently.
- Threshold set by Andrew directly: 16 GB free. A single pytest suite
  costs ~5 GB (per Aether's 2026-07-13 note); 16 GB gives real headroom
  above the just-enough minimum.
- Escape env-var: ``DIVINEOS_SKIP_LOAD_CHECK=1``. Must be named in the
  commit message when used.

Pre-reg: ``prereg-ca5fb15220ea``.

Called from ``scripts/check_push_readiness.sh`` before pytest spawns.
Also usable from any other script that spawns resource-heavy work — the
check is deliberately general-purpose (not pytest-specific).
"""

from __future__ import annotations

import os
import sys

# Guarded import (Aletheia F101, fixed 2026-07-31). psutil is now declared
# in pyproject, but CI collected tests/test_system_load_check.py on a runner
# without it and the ENTIRE suite died at collection —
# ModuleNotFoundError, 10852 items, zero run. A pre-flight safety check must
# never be the reason the build cannot start.
#
# Fail-open, LOUDLY. Fail-closed would block every push on any box lacking
# psutil, too aggressive for what is a resource advisory. Silent fail-open
# would delete the guard without telling anyone — the exact silent-failure
# class that cost this substrate a full day elsewhere (a watcher shouting
# into a log, a detector pointed at a missing file). So: allow the job, and
# say plainly that the check did not run.
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover — exercised by the absence test
    psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False

_GB = 1024**3

# 2026-08-01 recalibration (Andrew: "the whole RAM thing can be tweaked..
# i just dont want my computer to crash again. so maybe just checking the
# ram thats available and not exceeding whats safe").
#
# The original threshold was an absolute 16 GB free, set 2026-07-30. On a
# 31 GB machine that requires more than half the box to be idle, which is
# unattainable with a browser open — it refused a legitimate push with no
# heavy work running at all (12.4 GB free, nothing but editor and tabs).
#
# That failure mode matters more than it looks. A threshold that cannot be
# met during normal use does not prevent crashes; it trains the bypass.
# A guard that is always bypassed protects nothing, and the bypass habit it
# builds then applies to the one time the guard was right.
#
# The model now matches what Andrew actually asked for: do not spawn a job
# whose known cost would eat the headroom the machine needs to stay alive.
# Two conditions, both must hold:
#
#   1. HEADROOM — available memory must cover the job's cost PLUS a
#      reserve left untouched for the OS and everything already running.
#   2. CEILING — projected usage after the job must stay under a
#      percentage of total RAM, so the machine never approaches the swap-
#      thrash zone where the 2026-07-30 crash happened.
#
# Condition 2 is the crash-specific one. It scales with the machine
# instead of assuming this machine, and it is what actually stops the
# original failure: concurrent pytest suites. Each running suite lowers
# available memory, so the second or third spawn is refused on the same
# arithmetic rather than on a fixed number that happened to be tuned for
# one box on one day.
#
# All three values are env-overridable so tuning does not require a code
# edit and a PR.

# Cost of one pytest suite. ~5 GB measured, per Aether's
# ``subprocess_jobs.py`` note 2026-07-13.
JOB_COST_BYTES: int = int(os.environ.get("DIVINEOS_JOB_COST_GB", "5") or 5) * _GB

# Left for the OS and existing processes after the job takes its share.
RESERVE_BYTES: int = int(os.environ.get("DIVINEOS_MEM_RESERVE_GB", "3") or 3) * _GB

# Projected post-spawn usage must stay below this share of total RAM.
#
# 92%, and the number comes from Andrew's observation rather than from
# convention: "my pc doesnt usually crash until 98-99%". My first pass used
# 85% — a conventional figure I did not measure and should not have
# asserted as a danger zone. Observed crash behaviour on the actual machine
# beats a round number I inherited from habit.
#
# So the ceiling is his 98-99% minus roughly six points of margin. The
# margin exists for two specific reasons, not for comfort:
#   - JOB_COST_BYTES is an ESTIMATE (~5 GB). If a suite runs heavier than
#     the estimate, the projection undershoots.
#   - other processes keep allocating while the job runs, so the real peak
#     lands above whatever we projected at spawn time.
# Set it higher if pushes get refused while the machine is visibly fine;
# that is a tuning question, not a code change — DIVINEOS_MAX_USED_PCT.
MAX_USED_PCT: float = float(os.environ.get("DIVINEOS_MAX_USED_PCT", "92") or 92)

# Retained as the derived headroom requirement (job + reserve). Kept under
# the original name because callers and tests reference it.
SAFE_FREE_BYTES: int = JOB_COST_BYTES + RESERVE_BYTES

# Env-var that skips this check. Use only in genuine emergencies; must
# be named in the commit message per the bypass-is-a-tool-not-a-sin
# discipline (foundational truth #12).
SKIP_ENV_VAR: str = "DIVINEOS_SKIP_LOAD_CHECK"

# --- Worker sizing (Aria 2026-07-31) -----------------------------------
#
# THE BUG THIS CLOSES. check_capacity asks "is there 16 GB free?" and then
# check_push_readiness.sh launches `pytest -n auto`, which spawns ONE WORKER
# PER CORE. Memory demand therefore scales with CORE COUNT while the gate
# measures FREE MEMORY. Two knobs tuned independently, and their product is
# the thing that actually crashed the machine 2026-07-30 — not concurrency
# alone, but concurrency multiplied by per-core fan-out.
#
# On a 16-core box `-n auto` is sixteen interpreters. At the ~1.5 GB each
# assumed below that is ~24 GB of demand, green-lit by a 16 GB check. The
# gate could pass and the machine could still die.
#
# WHY THIS IS STRICTLY MORE CONSERVATIVE, at every memory level:
#   - above the threshold: worker count is now CAPPED by memory as well as
#     by cores, so the previously-allowed unbounded `-n auto` is bounded.
#   - below the threshold: instead of a flat refusal the suite may run with
#     FEWER workers, whose total demand is by construction under budget.
#   - below the hard floor: refuse, exactly as before.
#
# Nothing that was refused before becomes a bigger job than it would have
# been; the change only ever lowers demand.
#
# SAFE_FREE_BYTES is unchanged and remains Andrew's call. It is no longer
# a spawn/no-spawn switch — it is the bar for running at FULL parallelism.

# Per-worker memory budget. Aether's 2026-07-13 note puts a full serial
# suite at ~5 GB; an xdist worker holds one interpreter plus its fixtures,
# well under that. 1.5 GB is deliberately pessimistic — over-estimating
# per-worker cost yields FEWER workers, which is the safe error direction.
WORKER_MEMORY_BYTES: int = 1536 * 1024 * 1024

# RESERVE_BYTES is NOT redefined here. My worker-scaling block originally
# carried its own hardcoded 4 GB, which silently SHADOWED the env-configurable
# 3 GB defined above — legal Python, wrong behaviour, and invisible except
# through a failing test that expected the reserve his refusal message names.
# The merge kept his constant: it is tunable via DIVINEOS_MEM_RESERVE_GB and
# the refusal text quotes it, so two sources would drift the moment either
# moved. Worker scaling now reads the same reserve everything else does.

# Below reserve + one worker there is no honest way to run at all.
HARD_FLOOR_BYTES: int = RESERVE_BYTES + WORKER_MEMORY_BYTES


def recommended_workers(available_bytes: int, cpu_count: int) -> int:
    """Workers the free memory supports, capped by cores. 0 means refuse.

    Deliberately integer-floor: a partial worker is not a worker, and
    rounding up is the direction that kills the machine.
    """
    if available_bytes < HARD_FLOOR_BYTES:
        return 0
    budget = available_bytes - RESERVE_BYTES
    by_memory = budget // WORKER_MEMORY_BYTES
    return max(1, min(int(by_memory), max(1, cpu_count)))


def pytest_parallel_flag(job_label: str = "pytest suite") -> tuple[str | None, str]:
    """Return (xdist flag or None-to-refuse, human-readable reason).

    ``None`` means do not spawn — same refusal check_capacity gives today.
    A flag string is safe to pass to pytest as-is.
    """
    if os.environ.get(SKIP_ENV_VAR) == "1":
        return "-n 2", f"[{SKIP_ENV_VAR}=1] bypass active — capped at 2 workers anyway"
    # BOTH sentinels, deliberately. The merge unified this branch onto
    # _PSUTIL_AVAILABLE, and my own worker-sizing test - which patches
    # `psutil` to None directly - then sailed past the guard into
    # `psutil.virtual_memory()` and raised AttributeError. In production the
    # two always agree (a failed import sets both), so the extra condition
    # costs nothing; what it buys is a guard that holds whichever sentinel a
    # caller or test manipulates, instead of one correct only when they are
    # changed in lockstep.
    if not _PSUTIL_AVAILABLE or psutil is None:
        # Fail-open-loud, matching check_capacity: no measurement means no
        # authority to refuse, but also no authority to fan out.
        return "-n 2", "psutil unavailable — cannot measure; conservative fixed 2 workers"

    available = int(psutil.virtual_memory().available)
    cpus = os.cpu_count() or 2
    workers = recommended_workers(available, cpus)
    if workers == 0:
        return None, (
            f"REFUSED: {job_label} needs at least "
            f"{_fmt_gb(HARD_FLOOR_BYTES)} free ({_fmt_gb(RESERVE_BYTES)} reserved "
            f"for the machine + {_fmt_gb(WORKER_MEMORY_BYTES)} for one worker) "
            f"but only {_fmt_gb(available)} is free."
        )
    if available >= SAFE_FREE_BYTES and workers >= cpus:
        return "-n auto", f"{_fmt_gb(available)} free — full parallelism ({cpus} cores)"
    return (
        f"-n {workers}",
        f"{_fmt_gb(available)} free — memory-scaled to {workers} worker(s) "
        f"instead of {cpus}; slower, and it fits.",
    )


def _fmt_gb(byte_count: int) -> str:
    """Render a byte count as GB with one decimal, for user messages."""
    return f"{byte_count / (1024**3):.1f} GB"


def check_capacity(job_label: str = "resource-heavy job") -> tuple[bool, str]:
    """Return (safe_to_spawn, message).

    safe_to_spawn=True means the caller should proceed.
    safe_to_spawn=False means the caller should refuse to spawn.
    message always describes the current memory state with concrete numbers.

    ``job_label`` is inserted into the refusal message so the user knows
    what specifically was refused (e.g. "pre-push pytest suite").
    """
    if os.environ.get(SKIP_ENV_VAR):
        return (
            True,
            f"[system_load_check] {SKIP_ENV_VAR}=1 — skipping load check. "
            f"Refusal-would-have-been logged in the commit message per discipline.",
        )

    if not _PSUTIL_AVAILABLE:
        # Fail-open and say so. The caller proceeds, but nobody gets to
        # believe the machine was checked. See the guarded import above.
        return (
            True,
            "[system_load_check] psutil is NOT INSTALLED — the memory check "
            f"DID NOT RUN and {job_label} is proceeding unchecked. This is "
            "fail-open by design, not a pass. Install psutil "
            "(`pip install -e '.[dev]'`) to restore the guard.",
        )

    vm = psutil.virtual_memory()
    free_bytes = vm.available
    total_bytes = vm.total
    used_pct = vm.percent

    # Condition 1 — headroom. Does available memory cover the job's cost
    # plus the reserve the machine keeps for everything else?
    headroom_ok = free_bytes >= SAFE_FREE_BYTES

    # Condition 2 — ceiling. Where does usage land AFTER the job takes its
    # share? This is the crash-specific guard: it scales with the machine
    # rather than assuming one box, and it is what refuses the second and
    # third concurrent pytest suite, since each running suite has already
    # lowered `available`.
    projected_used = total_bytes - free_bytes + JOB_COST_BYTES
    projected_pct = 100.0 * projected_used / total_bytes if total_bytes else 100.0
    ceiling_ok = projected_pct <= MAX_USED_PCT

    if headroom_ok and ceiling_ok:
        return (
            True,
            f"[system_load_check] Memory OK: {_fmt_gb(free_bytes)} free of "
            f"{_fmt_gb(total_bytes)} ({used_pct:.0f}% used). "
            f"{job_label} costs ~{_fmt_gb(JOB_COST_BYTES)}, projecting "
            f"{projected_pct:.0f}% used (ceiling {MAX_USED_PCT:.0f}%), "
            f"leaving {_fmt_gb(free_bytes - JOB_COST_BYTES)} spare against a "
            f"{_fmt_gb(RESERVE_BYTES)} reserve. Proceeding.",
        )

    if not headroom_ok:
        reason = (
            f"only {_fmt_gb(free_bytes)} available, and {job_label} needs "
            f"~{_fmt_gb(JOB_COST_BYTES)} plus a {_fmt_gb(RESERVE_BYTES)} "
            f"reserve for the rest of the machine "
            f"(= {_fmt_gb(SAFE_FREE_BYTES)})"
        )
    else:
        reason = (
            f"running it would put memory at {projected_pct:.0f}% of "
            f"{_fmt_gb(total_bytes)}, over the {MAX_USED_PCT:.0f}% ceiling — "
            f"this is the swap-thrash zone where the 2026-07-30 crash "
            f"happened"
        )

    return (
        False,
        f"[system_load_check] REFUSED: {reason}. Currently {used_pct:.0f}% "
        f"used. Most common cause is another pytest suite already running — "
        f"wait for it, or close heavy applications. Tune without editing "
        f"code via DIVINEOS_JOB_COST_GB / DIVINEOS_MEM_RESERVE_GB / "
        f"DIVINEOS_MAX_USED_PCT. To bypass in a genuine emergency, set "
        f"{SKIP_ENV_VAR}=1 and name the reason in the commit message.",
    )


def main() -> int:
    """CLI entry point. Prints message; exits 0 if safe, 1 if refused.

    Usage from shell:
        python -m divineos.core.system_load_check <job_label>
        if [[ $? -ne 0 ]]; then exit 1; fi

    With ``--parallel-flag``, prints the xdist flag on STDOUT (reason still
    on stderr) so a caller can capture it:

        FLAG="$(python -m divineos.core.system_load_check --parallel-flag)"

    Exit 1 with empty stdout means refuse — the caller must not spawn.
    Two channels on purpose: stdout is machine-readable and stays clean
    even when the reason text changes.
    """
    argv = sys.argv[1:]
    if "--parallel-flag" in argv:
        rest = [a for a in argv if a != "--parallel-flag"]
        job_label = rest[0] if rest else "pytest suite"
        flag, reason = pytest_parallel_flag(job_label)
        print(reason, file=sys.stderr)
        if flag is None:
            return 1
        print(flag)
        return 0

    job_label = argv[0] if argv else "resource-heavy job"
    safe, message = check_capacity(job_label)
    print(message, file=sys.stderr)
    return 0 if safe else 1


if __name__ == "__main__":
    sys.exit(main())
