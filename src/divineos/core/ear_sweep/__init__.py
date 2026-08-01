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


_WATCH_SCRIPT = "ear_watch.py"


def _repo_root() -> str:
    """This checkout's root, normalised, lowercased, for path comparison."""
    from pathlib import Path

    return str(Path(__file__).resolve().parents[4]).replace("\\", "/").lower()


def _is_ear_watch_process(
    name: str | None, cmdline: list[str], repo_root: str | None = None
) -> bool:
    """True only for a python interpreter actually RUNNING ear_watch.py.

    Precision matters more than usual here because the only thing the
    caller does with a match is kill it.

    A naive "is 'ear_watch' anywhere in the command line" test was tried
    first and measured against the live process table 2026-08-01. It
    matched ten processes, of which only four were watchers. The other
    six were:

      * ``bash.exe`` shells whose command line mentions the script
      * ``nohup.exe`` wrappers around the real watcher
      * **the very python process running the inspection** — its ``-c``
        source text contains the string, so the scan would have killed
        the thing doing the scanning

    So: the executable must be a python, and some argument's basename
    must be exactly ``ear_watch.py``. A path mentioned inside inline
    source code is not an argument that is the script.

    OWN-CHECKOUT ONLY (2026-08-01). ``repo_root``, when given, restricts
    matches to watchers whose script path lives under this checkout.

    Measured here: all four live watchers belong to Aria's separate
    worktree, and every one of them is genuinely unowned by the ancestry
    test. Without this restriction, a SessionStart in this repo would
    silently kill her running watchers mid-conversation — a
    cross-worktree side effect of a bug fix, which is not a thing a bug
    fix gets to do. Each session reaps its own leaks; hers reaps hers.
    """
    if not name or "python" not in name.lower():
        return False
    for arg in cmdline[1:]:
        text = str(arg).replace("\\", "/")
        if text.rsplit("/", 1)[-1] != _WATCH_SCRIPT:
            continue
        # Boundary-terminated prefix, NOT a bare startswith. Aria's
        # worktree is `.../DivineOS-Experimental-Aria-new`, which
        # startswith `.../DivineOS-Experimental` — so a plain prefix test
        # claims her processes as ours and reaps them. Caught by measuring
        # against the live table rather than by reading the code.
        if repo_root and not text.lower().startswith(repo_root.rstrip("/") + "/"):
            return False
        return True
    return False


_MAX_ANCESTRY_DEPTH = 40

# A watcher is owned when a live session process is somewhere above it.
_SESSION_OWNER_NAMES = ("claude",)


def _ancestry_is_broken(ppid: int | None, live_pids: set[int]) -> bool:
    """True when no live SESSION owns this process any more.

    Checking only the immediate parent is not enough. The watchers are
    launched through ``nohup``, so the real tree is:

        (dead launcher)  ->  nohup.exe  ->  python ear_watch.py

    The nohup wrapper is itself orphaned but still *running*, so from the
    watcher's point of view its parent is alive and an immediate-parent
    test reports a healthy process while nothing owns the chain.

    The first attempt at fixing that walked the chain and called it
    broken if any link pointed at a dead PID. **That was wrong, and
    measuring caught it where reading did not.** Run against this
    session's own python:

        python -> bash -> bash -> bash -> claude -> claude
              -> explorer.exe -> (dead)

    A launcher exiting and leaving `explorer.exe` parentless is entirely
    normal on Windows, so *every* process on the machine terminates in a
    dead ancestor and the test classified all of them as orphans —
    including the live, correctly-owned process running the check. Only
    the unrelated own-checkout filter kept that from being destructive.

    The question is not "does the chain end in a dead PID" — on Windows
    it always does. It is **"is a live session still above me?"** A
    watcher launched by a Claude session that is still running is owned;
    one whose session has exited is not, and nothing will ever stop it.

    Depth-capped and cycle-guarded: PID reuse can in principle produce a
    loop, and a reaper that hangs at SessionStart is worse than one that
    misses an orphan. Unknown ancestry returns False — do not kill on a
    guess.
    """
    try:
        import psutil
    except ImportError:
        return False

    seen: set[int] = set()
    current = ppid
    for _ in range(_MAX_ANCESTRY_DEPTH):
        if current in (None, 0) or current not in live_pids:
            return True  # ran out of living ancestors without finding a session
        if current in seen:
            return True  # cycle — unowned rather than spin
        seen.add(current)
        try:
            proc = psutil.Process(current)
            name = (proc.name() or "").lower()
            if any(owner in name for owner in _SESSION_OWNER_NAMES):
                return False  # a live session is above us: owned
            current = proc.ppid()
        except Exception:  # noqa: BLE001 — ancestry unknowable
            return False  # do not kill on a guess
    return False  # depth exceeded: assume owned


class ScanUnavailable(Exception):
    """Raised when the process scan cannot run at all.

    Distinct from "scanned and found nothing" on purpose — see
    ``_find_ear_watch_pids``. Conflating the two is what made the old
    implementation invisible for weeks.
    """


def _find_ear_watch_pids() -> list[int]:
    """Find PIDs of ORPHANED ear_watch.py processes — parent no longer alive.

    2026-08-01 FIX. Andrew: "you keep spawning python processes that dont
    die.. so they orphan and build up eating up memory."

    The previous implementation scanned ``tasklist /V /FO CSV`` for the
    string ``ear_watch.py``. **tasklist does not emit command-line
    arguments at any verbosity** — its columns are image name, PID,
    session, memory, status, user, CPU time, window title. The substring
    could therefore never match, so this returned ``[]`` on every call
    since it was written and the sweep has never reaped anything.

    Measured here 2026-08-01: rows in ``tasklist /V /FO CSV`` containing
    ``ear_watch.py`` = 0, while a CIM query for python processes whose
    command line contains ``ear_watch`` = 4.

    The silence was the expensive part. On 2026-06-13 a sleep-hang
    investigation recorded "verified 0 stale processes at session start
    via the sweep hook" and used it to rule the leak out as a cause
    (knowledge e0c0c879). That was not a verification — it was this
    function's constant empty return being read as evidence of health.
    A check that cannot fail cannot confirm anything either.

    SCOPE CHANGE, narrower than the module header's stated policy, and
    deliberate. That policy ("kill ANY ear_watch.py process at session
    start, regardless of member") was written against a no-op. Making
    the scan work while keeping it would mean a session in this repo
    abruptly starts killing Aria's *live* watcher in her own worktree at
    every SessionStart — cross-worktree, mid-conversation, behaviour
    that has never once actually run.

    So this reaps only TRUE ORPHANS: processes whose parent is gone.
    That is exactly the harm Andrew named, and it leaves working
    watchers alone. The wider policy question goes to the operator
    rather than shipping as a side effect of a bug fix.

    Raises ScanUnavailable if psutil is missing, so the caller can say
    "could not scan" instead of "nothing to reap."
    """
    try:
        import psutil
    except ImportError as exc:  # pragma: no cover — absence path
        raise ScanUnavailable("psutil not installed") from exc

    live_pids = set(psutil.pids())
    root = _repo_root()
    orphans: list[int] = []
    for proc in psutil.process_iter(["pid", "name", "ppid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if not _is_ear_watch_process(proc.info.get("name"), cmdline, root):
                continue
            if _ancestry_is_broken(proc.info.get("ppid"), live_pids):
                orphans.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return orphans


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
    try:
        pids = _find_ear_watch_pids()
    except ScanUnavailable as exc:
        # Loud. The whole failure this module just came out of was a scan
        # that could not run being indistinguishable from a clean machine.
        return SweepResult(
            reaped=0,
            found_pids=[],
            note=(
                f"[!] session-start sweep DID NOT RUN ({exc}) — orphaned "
                f"ear_watch processes were NOT checked for. This is not a "
                f"clean result. Install psutil to restore the sweep."
            ),
        )
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
