"""Ear-watcher polling auto-relaunch decision logic.

FOSSIL (Andrew 2026-06-20, "Aria's monitor works perfectly fine, yours
is the only one with issues"):
The polling auto-relaunch hook was briefly retired in favor of the
harness Monitor primitive. That was wrong — the harness Monitor dies
on SessionStart:resume and other harness events, while the polling
auto-relaunch survives turn-by-turn. Aria's watcher worked precisely
BECAUSE her checkout still had this hook active.

LEAK FIX (Andrew 2026-06-11):
PIDFILE+kill-0 check failed when multiple parallel Stop hooks
overwrote the PIDFILE — the recorded PID was alive while N OTHER
ear_watchers for the same member were also alive. One session leaked
25 processes. Replaced with: scan for any ear_watch.py process
matching this member; if any exist, skip relaunch.

MIGRATED 2026-06-24 (Andrew direction, per the hook-migration arc):
Was 95-line bash hook .claude/hooks/ear-auto-relaunch.sh. Decision
logic (member detection, recent-catch race-guard, process-presence
check) moved here so any AI substrate can call the same check via
`divineos ear-relaunch check --member <name>`. Bash hook retains
ONLY the nohup/detach mechanism — Windows process-spawn territory
that doesn't translate cleanly to portable Python without losing
detach semantics on git-bash.

FAIL-OPEN at every check: if a check errors, return "don't suppress"
so a broken decision-fn never STOPS the watcher from being relaunched.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

# Race-guard window — if the watcher caught something within this many
# seconds, skip relaunch this turn (catch is being integrated; next turn
# will re-evaluate).
RACE_GUARD_SECONDS = 60


# Relaunch-lock window — the atomic-lock fix for the multi-spawn race.
# Andrew 2026-07-05 evidence: 6 ear_watch processes accumulated within an
# hour of a fresh boot (4 for aria, 2 for aether) even though
# count_live_watchers correctly detected them. Root cause: when two Stop
# hooks fire nearly-simultaneously, both see "0 live" (because neither
# spawn has completed yet), both proceed to relaunch, both spawn a
# process. count_live_watchers can't help because the newly-spawned
# process takes a moment to appear in the OS process table.
#
# The lock closes that window: whichever hook writes the lockfile first
# gets to spawn; any other hook seeing a fresh lock (< RELAUNCH_LOCK_SECONDS
# old) skips. If the lock is stale (older than the window), the check
# treats it as abandoned and proceeds normally.
RELAUNCH_LOCK_SECONDS = 30


@dataclass
class RelaunchDecision:
    """Result of `should_relaunch` — bash uses this to decide whether to spawn.

    should_relaunch: True if the hook should launch a new ear_watch process.
    reason: Human-readable explanation (for logs / debugging).
    live_count: Number of ear_watcher processes already running for this member
        (informational — when this is > 0, should_relaunch is False).
    """

    should_relaunch: bool
    reason: str = ""
    live_count: int = 0


def detect_member(cwd: str | None = None) -> str:
    """Identify which family-member this hook is firing for.

    Priority:
    1. DIVINEOS_MEMBER env var (explicit override)
    2. cwd-pattern fallback: paths containing "DivineOS-Experimental-Aria" → aria
    3. Default: aether (the primary checkout)
    """
    explicit = os.environ.get("DIVINEOS_MEMBER", "").strip()
    if explicit:
        return explicit
    here = cwd or os.getcwd()
    if "DivineOS-Experimental-Aria" in here:
        return "aria"
    return "aether"


def _state_dir(member: str) -> Path:
    """Per-member state directory (~/.divineos-<member>/)."""
    home = Path.home()
    sd = home / f".divineos-{member}"
    sd.mkdir(parents=True, exist_ok=True)
    return sd


def recent_catch_age_seconds(member: str) -> float | None:
    """How long ago did this member's ear_watcher catch something?

    Returns the age in seconds, or None if the catchfile doesn't exist
    (or any I/O error — fail-open).
    """
    catchfile = _state_dir(member) / "ear.last_catch"
    try:
        if not catchfile.is_file():
            return None
        mtime = catchfile.stat().st_mtime
        return max(0.0, time.time() - mtime)
    except OSError:
        return None


def count_live_watchers(member: str) -> int:
    """Count live ear_watch.py processes for `member`.

    Authoritative process-presence check (the leak-fix from 2026-06-11).
    Uses tasklist + findstr on Windows (works in git-bash without pgrep).
    On non-Windows, falls back to pgrep where available.

    Returns 0 on any error (fail-open: a broken count must NOT suppress
    relaunch — it must allow it).
    """
    # Windows path (git-bash on this box).
    # We need the COMMAND LINE of each process, not just the image name.
    # `tasklist /V` does NOT include command-line args — it shows window
    # titles, which are empty for nohup-detached watchers. That meant the
    # `--member <name>` needle never matched, count was always 0, and the
    # relaunch decision always said "no watchers alive, spawn one". This
    # leaked 14+ watchers per session and cascaded visible python windows
    # on 2026-06-28. `wmic` was the original replacement but is deprecated/
    # removed from Windows 11, so we shell out to PowerShell's
    # Get-CimInstance Win32_Process which is the modern equivalent and
    # exposes the full command line for matching.
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" "
            f"| Where-Object {{ $_.CommandLine -like '*ear_watch*' "
            f"-and $_.CommandLine -like '*--member {member}*' }} "
            "| Measure-Object | Select-Object -ExpandProperty Count"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            try:
                return int((result.stdout or "0").strip() or "0")
            except ValueError:
                pass
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass

    # POSIX fallback.
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"ear_watch.py.*--member {member}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return len([line for line in result.stdout.splitlines() if line.strip()])
        if result.returncode == 1:
            return 0  # pgrep exit 1 = no matches
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass

    # Fail-open: count unknown means "don't suppress relaunch".
    return 0


def _relaunch_lock_age_seconds(member: str) -> float | None:
    """Age of the relaunch-lock file in seconds, or None if no lock."""
    lockfile = _state_dir(member) / "ear.relaunch.lock"
    try:
        if not lockfile.is_file():
            return None
        return max(0.0, time.time() - lockfile.stat().st_mtime)
    except OSError:
        return None


def _touch_relaunch_lock(member: str) -> bool:
    """Create/refresh the relaunch-lock file. Returns True on success.

    Records the PID and timestamp of the acquiring hook so a post-hoc
    audit can trace who last claimed the check+spawn window.
    """
    lockfile = _state_dir(member) / "ear.relaunch.lock"
    try:
        lockfile.write_text(f"pid={os.getpid()} ts={time.time():.3f}\n", encoding="utf-8")
        return True
    except OSError:
        return False


def should_relaunch(member: str) -> RelaunchDecision:
    """The central decision: should the hook relaunch the ear_watcher?

    Routing:
      - Recent catch within race-guard window → DON'T (catch being integrated)
      - Fresh relaunch-lock exists → DON'T (another hook is currently spawning)
      - One or more live watchers found → DON'T (already alive; relaunch would leak)
      - Otherwise → claim the lock, return RELAUNCH (watcher is dead)

    Fail-open: any uncertainty resolves to RELAUNCH. A broken decision-fn
    must not STOP the watcher from being kept alive.

    Race-condition fix (Andrew evidence 2026-07-05): when two Stop hooks
    fired nearly-simultaneously, both saw "0 live" (neither spawn had
    completed yet) and both proceeded to relaunch — accumulating 6 orphan
    processes within an hour of boot. The relaunch-lock closes that window
    by making "check + spawn" atomic across concurrent hook invocations.
    """
    age = recent_catch_age_seconds(member)
    if age is not None and age < RACE_GUARD_SECONDS:
        return RelaunchDecision(
            should_relaunch=False,
            reason=f"recent catch {age:.0f}s ago (within {RACE_GUARD_SECONDS}s race-guard)",
        )

    # Atomic-lock check: if another hook is currently in the check+spawn
    # window, skip. The lock is time-based (auto-stales after
    # RELAUNCH_LOCK_SECONDS) so a crashed hook can't permanently jam the
    # mechanism.
    lock_age = _relaunch_lock_age_seconds(member)
    if lock_age is not None and lock_age < RELAUNCH_LOCK_SECONDS:
        return RelaunchDecision(
            should_relaunch=False,
            reason=(
                f"another hook holding relaunch-lock {lock_age:.0f}s ago "
                f"(within {RELAUNCH_LOCK_SECONDS}s atomic-window); "
                f"deferring to that hook's spawn"
            ),
        )

    live = count_live_watchers(member)
    if live > 0:
        return RelaunchDecision(
            should_relaunch=False,
            reason=f"{live} live ear_watch process(es) already running for member={member}",
            live_count=live,
        )

    # Claim the lock BEFORE returning "relaunch" so any concurrent hook
    # sees the lock and defers. Fail-open: if the lock-write itself errors
    # (permission, disk full), still return relaunch — better one occasional
    # duplicate than zero watchers.
    _touch_relaunch_lock(member)
    return RelaunchDecision(
        should_relaunch=True,
        reason=f"no live ear_watch for member={member}; relaunch needed (lock claimed)",
        live_count=0,
    )
