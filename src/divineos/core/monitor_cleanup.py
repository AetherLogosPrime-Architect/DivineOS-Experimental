"""Orphan-Monitor cleanup — finds and optionally kills stale Monitor processes.

Companion to ``monitor_singleton.py``. The mutex primitive prevents
NEW duplicates going forward, but does not clean up the population of
orphans already running from before the singleton-guard landed. This
module surfaces and (with explicit consent) sweeps them.

## What counts as an orphan

A Monitor process is an orphan if it matches ANY of:

- Runs a letter-monitor script BUT a sibling with the same script-name
  has a newer process creation time. The newer one is the live
  mutex-holder; older ones are stale.
- Runs the LEGACY bash inline command (matches ``aria-to-aether-``
  with name=bash.exe) — these predate the mutex design and the
  singleton-guard cannot retroactively catch them.

This is descriptive by default. ``--kill`` is required to actually
terminate processes; without it, the tool just prints what it would
have done. Andrew 2026-06-13 explicitly chose this shape: destruction
needs operator consent at the invocation, not at install time.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass
class MonitorProcess:
    """One Monitor process found on the system."""

    pid: int
    name: str  # "python.exe" / "bash.exe"
    role: str  # "letter" / "compaction" / "legacy_letter_bash" / "legacy_compaction_bash"
    creation_date: str  # ISO-ish string; ordering is what matters
    command_line: str


def _scan_processes() -> list[MonitorProcess]:
    """Scan all live processes for Monitor-shaped command lines.

    Returns one MonitorProcess per match. Empty list on non-Windows
    or if the PowerShell scan fails — cleanup is Windows-specific.
    """
    if os.name != "nt":
        return []

    # PowerShell delimits fields with TAB so we don't have to parse
    # quoted CSV. Each row: pid<TAB>name<TAB>creation<TAB>cmdline
    #
    # KEY ON THE ROLE-SHAPE, NOT ON A SCRIPT FILENAME (2026-08-20).
    #
    # monitor_singleton keys its mutex on the ROLE, which its docstring
    # calls role-stable precisely so a rename cannot break sibling
    # detection. This scan keyed on the script FILENAME, which is not
    # stable -- so a rename left the singleton working and the sweep
    # blind, with no symptom on either side.
    #
    # That is what had happened. `letter_monitor\.py` required a literal
    # `.py` immediately after the name, and the live script is
    # `letter_monitor_v2.py`. Measured against the running process's
    # command line: the old pattern returned False, `letter_monitor.*\.py`
    # returned True, and two letter monitors were live at the time that
    # the sweep could not see. The role whose orphans this exists to
    # catch was the one role it could not match.
    #
    # The `compaction` pattern is removed rather than repaired:
    # scripts/compaction_token_monitor.py is deleted on this branch and
    # nothing here spawns it, so the entry could match nothing, forever,
    # and report nothing wrong -- a check that cannot fire is
    # indistinguishable from a check that fires and finds all clean.
    # Aletheia F118, 2026-08-20. The role name survives in MonitorProcess
    # and in the CLI's _ROLES; if a compaction monitor is reintroduced,
    # add a pattern keyed on its role-shape and not on its filename.
    ps_cmd = r"""
$pats = @(
  @{role='letter';            name='python.exe'; pat='letter_monitor.*\.py'},
  @{role='legacy_letter_bash';name='bash.exe';   pat='aria-to-aether-'}
)
$rows = @()
foreach ($p in $pats) {
  $matches = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq $p.name -and $_.CommandLine -match $p.pat }
  foreach ($m in $matches) {
    $rows += "$($m.ProcessId)`t$($m.Name)`t$($p.role)`t$($m.CreationDate)`t$($m.CommandLine)"
  }
}
$rows -join "`n"
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:  # noqa: BLE001 — PowerShell probe must never raise; cleanup is best-effort
        return []

    out: list[MonitorProcess] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 4)
        if len(parts) < 5:
            continue
        pid_s, name, role, created, cmdline = parts
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        out.append(
            MonitorProcess(
                pid=pid,
                name=name,
                role=role,
                creation_date=created,
                command_line=cmdline,
            )
        )
    return out


def classify_orphans(
    processes: list[MonitorProcess],
) -> tuple[list[MonitorProcess], list[MonitorProcess]]:
    """Split processes into (keep, orphans).

    Rules:
    - Within each role, the NEWEST process (max creation_date) is kept.
    - All older processes in that role are orphans.
    - All ``legacy_*`` processes are orphans regardless of count — the
      legacy bash inline command was replaced; nothing from before
      should still be running.
    """
    by_role: dict[str, list[MonitorProcess]] = {}
    for p in processes:
        by_role.setdefault(p.role, []).append(p)

    keep: list[MonitorProcess] = []
    orphans: list[MonitorProcess] = []
    for role, ps in by_role.items():
        if role.startswith("legacy_"):
            orphans.extend(ps)
            continue
        ps_sorted = sorted(ps, key=lambda p: p.creation_date, reverse=True)
        keep.append(ps_sorted[0])
        orphans.extend(ps_sorted[1:])
    return keep, orphans


def kill_pid(pid: int) -> bool:
    """Best-effort kill the given PID via taskkill /F.

    Returns True on success, False on failure (process gone, access
    denied, etc.). Failure is not fatal — the next sweep will catch
    survivors.
    """
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:  # noqa: BLE001 — kill is best-effort; next sweep catches survivors
        return False
