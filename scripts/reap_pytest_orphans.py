"""Find and optionally kill pytest-xdist orphan worker processes.

Andrew 2026-07-01 hit 12GB of orphan pytest-xdist workers. Root cause:
`python -m pytest -n auto` spawns worker subprocesses that inherit
the parent's shape. When the parent process gets killed mid-run
(e.g., by a Bash tool timeout, or manual Stop-Process), the workers
detach on Windows and keep running — each holding ~1.85GB of loaded
test modules + fixtures.

Same failure class Aria hit yesterday (113 orphans on her side).

Called from check_push_readiness.sh before running pytest, so any
detached workers from a prior aborted run get cleaned before the
new run starts. Prevents the race Andrew hit tonight where an
orphan-kill (mine, of prior detached workers) sniped an in-flight
pytest run's live workers, producing a spurious test failure.

Descriptive by default; --kill actually terminates.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


# The pytest-xdist worker command-line signature on Windows. xdist
# workers are launched by execnet as `python -u -c "import sys;
# exec(eval(sys.stdin.readline()))"` — the parent then writes their
# actual work over stdin. That command-line is *distinctive* — no
# other tool I know of spawns Python this way.
_WORKER_SIGNATURE = "import sys;exec(eval(sys.stdin.readline()))"


def _list_worker_processes() -> list[dict]:
    """Return a list of dicts describing xdist worker processes.

    Each dict has: pid, ppid, command, working_set_mb, creation_date.
    Windows-only (uses powershell + WMI). Returns [] on non-Windows.
    """
    if sys.platform != "win32" and "CYGWIN" not in os.environ.get("OSTYPE", "").upper():
        # Non-Windows: use pgrep-style search. Not needed for this
        # specific bug (which is Windows-shaped), so return [] rather
        # than build the Unix path speculatively.
        return []

    # Powershell one-liner returning tab-separated fields.
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        r"""
$sig = '"""
        + _WORKER_SIGNATURE
        + r"""'
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like ('*' + $sig + '*') } |
  ForEach-Object {
    "$($_.ProcessId)`t$($_.ParentProcessId)`t$([math]::Round($_.WorkingSetSize/1MB,1))`t$($_.CreationDate)"
  }
""",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    out = []
    for line in result.stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) != 4:
            continue
        try:
            out.append(
                {
                    "pid": int(parts[0]),
                    "ppid": int(parts[1]),
                    "working_set_mb": float(parts[2]),
                    "creation_date": parts[3],
                }
            )
        except ValueError:
            continue
    return out


def _is_process_alive(pid: int) -> bool:
    """Windows: query WMI for whether the PID exists."""
    if pid <= 0:
        return False
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) "
                f'{{ Write-Output "alive" }} else {{ Write-Output "dead" }}',
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return "alive" in result.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def find_orphans(workers: list[dict]) -> list[dict]:
    """Filter to just the orphans — workers whose parent is dead.

    An orphan xdist worker will typically reparent to PID 1 or become
    parented to a system process. Simpler test: is the recorded
    ppid still alive?
    """
    orphans = []
    for w in workers:
        if not _is_process_alive(w["ppid"]):
            orphans.append(w)
    return orphans


def kill_processes(orphans: list[dict]) -> int:
    """Terminate the given orphan processes. Returns count killed."""
    if not orphans:
        return 0
    pids = ",".join(str(o["pid"]) for o in orphans)
    try:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Stop-Process -Id {pids} -Force -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return len(orphans)
    except (OSError, subprocess.SubprocessError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find and optionally reap pytest-xdist orphan workers."
    )
    parser.add_argument(
        "--kill",
        action="store_true",
        help="Actually terminate detected orphans. Without this, just prints.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only emit output if orphans were found (useful for pre-push hooks).",
    )
    args = parser.parse_args()

    workers = _list_worker_processes()
    orphans = find_orphans(workers)

    if not orphans:
        if not args.quiet:
            print(
                f"[reap_pytest_orphans] no orphans found "
                f"({len(workers)} live workers, all with live parents)"
            )
        return 0

    total_mb = sum(o["working_set_mb"] for o in orphans)
    print(
        f"[reap_pytest_orphans] found {len(orphans)} orphan "
        f"pytest-xdist workers holding ~{total_mb:.0f}MB total"
    )
    for o in orphans:
        print(f"  pid={o['pid']} ppid={o['ppid']}(dead) mem={o['working_set_mb']:.1f}MB")

    if args.kill:
        n = kill_processes(orphans)
        print(f"[reap_pytest_orphans] killed {n} orphan(s)")
    else:
        print("[reap_pytest_orphans] descriptive only. Pass --kill to terminate.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
