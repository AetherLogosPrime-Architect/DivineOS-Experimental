"""Orphan-Monitor cleanup — finds and optionally kills stale Monitor processes.

Companion to ``monitor_singleton.py``. The mutex primitive prevents
NEW duplicates going forward, but does not clean up the population of
orphans already running from before the singleton-guard landed. This
module surfaces and (with explicit consent) sweeps them.

## What counts as an orphan

A Monitor process is an orphan if it matches ANY of:

- Runs ``scripts/letter_monitor.py`` (or a versioned successor such as
  ``letter_monitor_v2.py``) or ``scripts/compaction_token_monitor.py``
  BUT a sibling **in the same checkout** has a newer process creation
  time. The newer one is the live mutex-holder; older ones are stale.

  SAME CHECKOUT is load-bearing, not decoration. This machine runs more
  than one DivineOS working tree at once -- Aether's and Aria's, plus
  worktrees -- and each window arms its own monitors. Keyed on role
  alone, the newest letter-monitor anywhere on the box "wins" and every
  other window's live watcher is reported as stale. Caught 2026-08-20:
  status flagged a monitor running out of Aether's checkout, under a
  live parent, in a window that was still open. ``--kill`` would have
  reached into a sibling's session and shot their watcher.

  Where the checkout cannot be parsed out of the command line, the
  process is its own group and is never anybody's orphan. A stale
  poller costs one idle process; killing a live sibling's monitor costs
  another agent their letters. The heuristic fails toward not-killing.
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
import re
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
    ps_cmd = r"""
$pats = @(
  @{role='letter';            name='python.exe'; pat='letter_monitor(_v\d+)?\.py'},
  @{role='compaction';        name='python.exe'; pat='compaction_token_monitor\.py'},
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


UNKNOWN_ROOT = "<unparsed>"

# The script path in the command line, with the checkout it lives in as the
# capture. Tolerates either slash direction and an optional surrounding quote,
# because the arming call sites are not consistent about either.
_ROOT_RE = re.compile(
    r"(?P<root>(?:[A-Za-z]:)?[\\/][^\"']*?)[\\/]scripts[\\/][^\\/\"']*monitor[^\\/\"']*\.py",
    re.IGNORECASE,
)


def checkout_root_of(command_line: str) -> str:
    """The working tree a monitor process belongs to, or ``UNKNOWN_ROOT``.

    Normalised to forward slashes and lowercase. Windows paths are
    case-insensitive and reachable with either slash direction, so the same
    tree spelled two ways has to compare equal or the grouping is theatre.
    """
    m = _ROOT_RE.search(command_line or "")
    if not m:
        return UNKNOWN_ROOT
    return m.group("root").replace("\\", "/").rstrip("/").lower()


def classify_orphans(
    processes: list[MonitorProcess],
) -> tuple[list[MonitorProcess], list[MonitorProcess]]:
    """Split processes into (keep, orphans).

    Rules:
    - Within each (role, checkout root), the NEWEST process is kept.
    - Older processes in that same role AND same checkout are orphans.
    - A process whose checkout cannot be parsed is its own group, so it
      is never classified as anybody else's stale sibling.
    - All ``legacy_*`` processes are orphans regardless of count — the
      legacy bash inline command was replaced; nothing from before
      should still be running.

    The checkout half of the key is what stops a sweep in one working
    tree from killing a live monitor in another. See the module
    docstring for the 2026-08-20 near-miss that put it there.
    """
    by_group: dict[tuple[str, str], list[MonitorProcess]] = {}
    for p in processes:
        root = checkout_root_of(p.command_line)
        # An unparsed root gets a key nothing else can collide with, so it
        # is neither an orphan nor able to make someone else one.
        group = (p.role, root if root != UNKNOWN_ROOT else f"{UNKNOWN_ROOT}:{p.pid}")
        by_group.setdefault(group, []).append(p)

    keep: list[MonitorProcess] = []
    orphans: list[MonitorProcess] = []
    for (role, _root), ps in by_group.items():
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
