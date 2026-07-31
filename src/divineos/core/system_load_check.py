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

# 16 GB free memory required before a resource-heavy job can spawn.
# Set by Andrew 2026-07-30. Rationale: a full pytest suite costs ~5 GB
# (Aether ``subprocess_jobs.py`` 2026-07-13 note). 16 GB gives real
# headroom above the just-enough minimum, so the machine has margin
# for other processes plus a safety cushion above the pytest cost.
SAFE_FREE_BYTES: int = 16 * 1024 * 1024 * 1024

# Env-var that skips this check. Use only in genuine emergencies; must
# be named in the commit message per the bypass-is-a-tool-not-a-sin
# discipline (foundational truth #12).
SKIP_ENV_VAR: str = "DIVINEOS_SKIP_LOAD_CHECK"


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

    if free_bytes >= SAFE_FREE_BYTES:
        return (
            True,
            f"[system_load_check] Memory OK: {_fmt_gb(free_bytes)} free "
            f"of {_fmt_gb(total_bytes)} ({used_pct:.0f}% used). "
            f"Proceeding with {job_label}.",
        )

    return (
        False,
        f"[system_load_check] REFUSED: {job_label} needs at least "
        f"{_fmt_gb(SAFE_FREE_BYTES)} free memory but the system only has "
        f"{_fmt_gb(free_bytes)} free ({used_pct:.0f}% used). "
        f"Wait for existing heavy work to finish or free memory before "
        f"retrying. To bypass in a genuine emergency, set "
        f"{SKIP_ENV_VAR}=1 and name the reason in the commit message.",
    )


def main() -> int:
    """CLI entry point. Prints message; exits 0 if safe, 1 if refused.

    Usage from shell:
        python -m divineos.core.system_load_check <job_label>
        if [[ $? -ne 0 ]]; then exit 1; fi
    """
    job_label = sys.argv[1] if len(sys.argv) > 1 else "resource-heavy job"
    safe, message = check_capacity(job_label)
    print(message, file=sys.stderr)
    return 0 if safe else 1


if __name__ == "__main__":
    sys.exit(main())
