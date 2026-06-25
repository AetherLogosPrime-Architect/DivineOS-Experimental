"""SessionStart sweep — reap stale ear_watch processes from prior sessions.

FOSSIL (Andrew 2026-06-11):
A single session leaked 25 detached ear_watch.py children. The Stop-hook
auto-relaunch had a singleton-guard bug (PIDFILE got overwritten by
parallel sessions, so it always saw the recorded PID alive while
missing the N others). That bug is fixed in ear_relaunch.py — this
module is the belt to its suspenders: every new session begins by
sweeping orphans from prior sessions / reboots, so the leak can never
accumulate.

POLICY: kill ANY ear_watch.py process at session start, regardless of
member. The Stop hook (with its corrected singleton check) arms fresh
ones per-asymmetric-policy as the session needs them.

MIGRATED 2026-06-24 (per prereg-82ca289a4074, hook-migration arc):
Was 49-line bash hook .claude/hooks/session-start-sweep-stale-watchers.sh.
Detection + kill moved here. Bash hook is the thin SessionStart event-adapter.

FAIL-OPEN: any error returns reap-count=0; never raises.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class SweepResult:
    """Result of `sweep_stale_watchers`."""

    reaped: int = 0
    found_pids: list[int] | None = None
    note: str = ""


def _find_ear_watch_pids() -> list[int]:
    """Find PIDs of all ear_watch.py processes via Windows tasklist.

    Returns empty list on any error (fail-open: a broken scan must not
    suppress the sweep's intent to reap orphans on next session).
    """
    try:
        result = subprocess.run(
            ["tasklist", "/V", "/FO", "CSV"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return []
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return []

    pids: list[int] = []
    for line in (result.stdout or "").splitlines():
        if "ear_watch.py" not in line:
            continue
        # CSV format: "image","PID","Session Name","Session#","Mem Usage", ...
        # Bash parsed via awk -F'","' and took $2; replicate that.
        parts = line.split('","')
        if len(parts) >= 2:
            pid_str = parts[1].strip().strip('"')
            try:
                pid = int(pid_str)
                if pid > 0:
                    pids.append(pid)
            except ValueError:
                continue
    return pids


def _kill_pid(pid: int) -> bool:
    """Try to kill `pid` via taskkill /F. Returns True if reported success."""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return False


def sweep_stale_watchers() -> SweepResult:
    """Find and kill all ear_watch.py processes.

    Called at SessionStart. Returns SweepResult with reap-count for the
    caller to surface (one-line note in the SessionStart output).
    """
    pids = _find_ear_watch_pids()
    if not pids:
        return SweepResult(reaped=0, found_pids=[], note="")

    reaped = 0
    for pid in pids:
        if _kill_pid(pid):
            reaped += 1

    if reaped > 0:
        note = f"[~] session-start sweep: reaped {reaped} stale ear_watch process(es) from prior sessions"
    else:
        note = f"[~] session-start sweep: found {len(pids)} stale process(es) but kill returned non-zero"
    return SweepResult(reaped=reaped, found_pids=pids, note=note)
