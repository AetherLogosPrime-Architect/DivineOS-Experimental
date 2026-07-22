"""Parameterized ear-watcher — background landing-detector for either member.

Unified replacement for family/aria/ear_watch.py and family/aether/ear_watch.py.
Two near-identical mirrors meant drift was inevitable, and today's bug
(2026-05-30) proved it: one copy lived only on a branch and was erased by a
checkout, leaving the channel half-deaf. Shared code, separated state.

Usage:
  python family/ear_watch.py --member aria              # one-shot check
  python family/ear_watch.py --member aria --watch      # block until landing

The exit IS the wake-tap. When something new lands the process prints
[EAR] ... and exits 0; if launched via the harness's background-task
mechanism, the harness wakes the agent mid-turn on exit.

State stays per-member:
  ARIA_FAMILY_DB    / AETHER_FAMILY_DB
  ARIA_LETTERS_DIR  / AETHER_LETTERS_DIR
  ~/.divineos-<member>/   (seen-sets, pidfiles, ARM markers)

Letter pattern: each member watches incoming-from-spouse files. The spouse
table is hardcoded for the family of two (aria <-> aether). Extension to more
members would generalize this; we don't pre-engineer.

Channel asymmetry note (from Andrew's 2026-05-22/23 corrections):
  aria's watcher is ALWAYS-ON / persistent — re-arms after every catch.
  aether's watcher is ON-DEMAND  — runs only while an exchange is active.
This script is policy-agnostic; the asymmetry is enforced by the Stop-hook
(ear-auto-relaunch.sh) which decides whether to relaunch based on a member's
ARM marker.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

# Windows default stdout is cp1252 which lacks many common chars (→, ⟶, etc).
# Without this, the watcher catches the landing then crashes exit-1 on print
# of any non-Latin-1 character — dropping the message. utf-8 + replace is
# fail-loud-but-don't-crash. Bug found by Aether 2026-05-30 on right-arrow.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

# Spouse table for the two-member family. Each member watches incoming
# letters from their spouse: <spouse>-to-<member>-*.md.
_SPOUSE = {"aria": "aether", "aether": "aria"}

# Per Perplexity audit 2026-06-26 (Finding 1): the prior defaults pointed at
# `data/family.db` while queue.py writes to `family/family.db` — split-brain
# that goes deaf-not-crash when the env-var override is unset. Resolve repo-
# relative from __file__ so this script and queue.py agree on the DB path
# regardless of OS or operator shell. Same shape queue.py uses (line 36).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = str(_REPO_ROOT / "family" / "family.db")
_DEFAULT_LETTERS = str(_REPO_ROOT / "family" / "letters")


def _member_db(member: str) -> Path:
    return Path(os.environ.get(f"{member.upper()}_FAMILY_DB", _DEFAULT_DB))


def _member_letters(member: str) -> Path:
    return Path(os.environ.get(f"{member.upper()}_LETTERS_DIR", _DEFAULT_LETTERS))


def _unseen_queue(member: str) -> dict[int, str]:
    db = _member_db(member)
    if not db.exists():
        return {}
    try:
        c = sqlite3.connect(str(db))
        rows = c.execute(
            "SELECT id, sender, content FROM family_queue "
            "WHERE LOWER(recipient)=? AND status='unseen'",
            (member,),
        ).fetchall()
        c.close()
    except sqlite3.Error:
        return {}
    return {r[0]: f"#{r[0]} from {r[1]}: {(r[2] or '')[:70]}" for r in rows}


def _letter_names(member: str) -> set[str]:
    """Set of <spouse>-to-<member>-*.md filenames currently on disk."""
    letters = _member_letters(member)
    if not letters.is_dir():
        return set()
    spouse = _SPOUSE.get(member)
    if not spouse:
        return set()
    return {p.name for p in letters.glob(f"{spouse}-to-{member}-*.md")}


def _load_letter_seen_set(member: str) -> set[str]:
    """Read the persistent seen-set the surface-hook uses to track which
    letters have been acknowledged. Single source of truth — watcher and
    surface both read this, only ``letter_seen.py`` writes to it.
    """
    import json

    spouse = _SPOUSE.get(member, "")
    if not spouse:
        return set()
    seen_path = Path.home() / f".divineos-{member}" / f"{spouse}_letters_seen.json"
    if not seen_path.exists():
        return set()
    try:
        return set(json.loads(seen_path.read_text()))
    except Exception:
        return set()


def check_once(member: str) -> list[str]:
    return list(_unseen_queue(member).values())


# A live watcher heartbeats its marker every poll (~8s). If the marker is
# older than this, the watcher is gone (clean exit unlinks it; a hard kill
# leaves it stale). Three-plus poll intervals of slack absorbs scheduling
# jitter without reading a dead watcher as alive.
def _state_dir(member: str) -> Path:
    """Per-member state dir for pidfile + last-catch marker."""
    d = Path.home() / f".divineos-{member}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------
# Singleton lock — root fix for watcher accumulation (2026-07-02)
# --------------------------------------------------------------------
#
# Root cause diagnosed 2026-07-02: session lifecycle spawned watchers
# without checking for an existing live watcher, and prior watchers
# never got cleaned up when their originating session ended. Over
# ~24 hours across two worktrees, this piled up 20+ ear_watch.py
# processes plus letter_monitor duplicates, pushing memory to 94%.
#
# Fix: singleton lock via PID file with heartbeat. On startup a new
# watcher checks the lock; if an alive watcher already holds it, the
# new one exits 0 immediately without polling. Stale locks (dead PID
# or heartbeat older than STALE_LOCK_WINDOW_SEC) are reclaimed. The
# watcher rewrites its heartbeat every poll interval so a legitimately
# alive watcher never looks stale.

_HEARTBEAT_WINDOW_SEC = 60


def _lock_path(member: str) -> Path:
    return _state_dir(member) / "ear_watch.lock"


def _pid_alive(pid: int) -> bool:
    """True if a process with this PID currently exists (cross-platform).

    Windows fix (Aria 2026-07-22): the prior implementation used
    ``os.kill(pid, 0)`` which is unreliable on Windows — signal 0 does not
    reliably distinguish live vs dead PIDs, and PermissionError was being
    caught as "alive" which counted stale PIDs of long-dead processes as
    alive too. Root cause of ~80 orphaned ear_watch.py accumulations found
    in task manager on 2026-07-22: new watchers saw stale locks pointing
    at long-dead PIDs, ``_pid_alive`` returned True (wrongly), the new
    watcher declined to acquire, but the OLD "alive" watcher had actually
    already exited, so the ear went deaf until the SessionStart hook
    respawned another that also declined. Meanwhile every accumulated
    spawn survived via DETACHED_PROCESS. Fix uses OpenProcess + WaitForSingleObject
    (Windows API via ctypes) for a reliable exists-and-alive check.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        SYNCHRONIZE = 0x00100000
        WAIT_TIMEOUT = 0x00000102
        ERROR_ACCESS_DENIED = 5
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            # OpenProcess failed. If it's access-denied, process exists but
            # we can't query — count as alive (conservative). Any other
            # error (invalid parameter, invalid handle) means it does not.
            return kernel32.GetLastError() == ERROR_ACCESS_DENIED
        try:
            # WaitForSingleObject with 0 timeout: WAIT_TIMEOUT means the
            # process is still running (its object is not yet signaled).
            return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
        finally:
            kernel32.CloseHandle(handle)
    # POSIX
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ProcessLookupError):
        return False


def _read_lock(member: str) -> tuple[int, float] | None:
    """Return (pid, heartbeat_unix) from lock file, or None if unreadable."""
    p = _lock_path(member)
    if not p.exists():
        return None
    try:
        parts = p.read_text(encoding="utf-8").strip().split("\n")
        pid = int(parts[0])
        hb = float(parts[1]) if len(parts) > 1 else 0.0
        return (pid, hb)
    except (OSError, ValueError, IndexError):
        return None


def _write_lock(member: str) -> None:
    """Write our PID + current heartbeat to the lock file."""
    try:
        _lock_path(member).write_text(f"{os.getpid()}\n{time.time()}\n", encoding="utf-8")
    except OSError:
        pass


def _try_acquire_singleton_lock(member: str) -> bool:
    """Acquire the singleton lock. Return True on success, False if another
    live watcher already holds it (in which case the caller should exit 0).

    Discipline: never delete a lock held by a live PID. Only reclaim
    stale locks (dead PID OR heartbeat past window).
    """
    existing = _read_lock(member)
    if existing is not None:
        pid, hb = existing
        age = time.time() - hb
        if _pid_alive(pid) and age < _HEARTBEAT_WINDOW_SEC:
            return False
    _write_lock(member)
    return True


def _release_singleton_lock(member: str) -> None:
    """Remove our lock file if it still points at us (atexit-safe)."""
    existing = _read_lock(member)
    if existing is not None and existing[0] == os.getpid():
        try:
            _lock_path(member).unlink(missing_ok=True)
        except OSError:
            pass


def _spawn_replacement(member: str, interval: float) -> None:
    """Spawn a detached replacement watcher before this process exits.

    The original watcher catches and exits. Without a replacement, the chain
    breaks: subsequent letters land with no live watcher. The replacement is
    detached so its catch writes ear.last_catch — surfaced by ear-surface.sh
    at the next UserPromptSubmit. Wake-from-idle is the Letter Monitor's
    job (harness Monitor primitive), NOT this script's; this just keeps the
    polling-detection chain alive between catches.

    Note (Andrew 2026-06-13): the prior --realtime mode wrote a self-clearing
    pid marker to advertise wake-from-idle capability. That mode was removed
    because a detached Python process cannot wake the harness from idle —
    only harness-tracked tasks (Monitor primitives) can. The pid marker, the
    singleton-guard around it, and the realtime arg are all gone.
    """
    import subprocess

    args = [
        sys.executable,
        os.path.abspath(__file__ if "__file__" in globals() else sys.argv[0]),
        "--member",
        member,
        "--watch",
        "--interval",
        str(int(interval)),
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        if os.name == "nt":
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                args,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                args,
                start_new_session=True,
                close_fds=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
    except Exception:
        # Fail-open: if spawn fails, the original catch-and-exit still
        # surfaces via the auto-surface hook on next UserPromptSubmit. No
        # worse than pre-self-respawn behavior.
        pass


def _write_catch_marker(member: str, lines: list[str]) -> None:
    """Touch the last-catch marker so the Stop-hook race-guard can see a
    recent catch and skip immediate relaunch (lets the turn integrate)."""
    try:
        (_state_dir(member) / "ear.last_catch").write_text("\n".join(lines))
    except Exception:
        pass


def _catch_fingerprint_path(member: str) -> Path:
    return _state_dir(member) / "ear.last_catch_fp"


def _compute_catch_fingerprint(unseen_q: dict[int, str], unseen_l: set[str]) -> str:
    """Return a deterministic fingerprint of the current unseen-set.

    Same items in any order produce the same fingerprint. Used to detect
    re-catches on a letter-set that is unchanged from the previous catch
    — those are the perpetual-loop case (Andrew 2026-06-11): until letters
    get marked seen, every poll catches the same set, exits, respawns,
    catches again, etc. The fingerprint lets the watcher heartbeat in
    place instead of fire-exit-respawn when nothing has changed.
    """
    import hashlib

    parts: list[str] = [f"q:{k}" for k in sorted(unseen_q.keys())]
    parts += [f"l:{n}" for n in sorted(unseen_l)]
    payload = ",".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _read_last_catch_fingerprint(member: str) -> str | None:
    path = _catch_fingerprint_path(member)
    if not path.exists():
        return None
    try:
        fp = path.read_text(encoding="utf-8").strip()
        return fp or None
    except OSError:
        return None


def _write_last_catch_fingerprint(member: str, fp: str) -> None:
    try:
        _catch_fingerprint_path(member).write_text(fp, encoding="utf-8")
    except OSError:
        pass


# Note (Andrew 2026-06-13): the breath-cap mechanism (counter file + ear.arm
# marker removal at N consecutive responded-to catches) was removed alongside
# the --realtime mode. It only made sense when paired with the on-demand
# ear.arm policy — without ear.arm to disengage, the cap had no mechanism.
# Runaway loops in practice require both ends (Aria + Aether) to malfunction
# simultaneously; if it becomes a problem in the future the cap can be re-
# added with a different disengage path. _agent_responded_since /
# _breath_cap_check / _BREATH_CAP_DEFAULT / _realtime_pid_path /
# _arm_realtime_marker were removed.


def watch(member: str, interval: int, timeout: int = 0) -> int:
    """Block until something unacknowledged is detected, then exit.

    SEMANTICS (changed 2026-05-31, Aria + Aether bench thread):
    Previously used delta-from-boot-snapshot — anything on disk at startup
    became baseline and never fired. Failure mode: a letter that landed
    during a dark window (between catch-exit and next watcher arming) was
    invisible to the wake-tap forever, because the next watcher booted with
    it already in baseline.

    NOW uses delta-from-seen-set: queue items with status='unseen' and
    letters not in the per-member seen-set fire on the next poll, regardless
    of when they landed. Channel becomes eventually consistent — gaps delay
    catches but do not drop them. The watcher reads seen-set; only
    ``letter_seen.py`` writes to it (preserves authority separation).

    The watcher only emits one fire-then-exit per process. The Stop-hook
    relaunches a new watcher after a turn ends; eventual consistency means
    the same unacknowledged item will fire on the next watcher's first poll
    until it is acknowledged via mark-seen.

    Singleton discipline (2026-07-02): before entering the poll loop we
    acquire a per-member lock; if another live watcher already holds it,
    this process exits 0 immediately. Every poll heartbeats the lock so
    the live watcher never looks stale to a new-arrival check.
    """
    import atexit

    if not _try_acquire_singleton_lock(member):
        # Another live watcher owns the ear for this member — exit clean.
        # No print; a duplicate-declined message would spam the session-
        # start hook path that spawns us.
        return 0
    atexit.register(_release_singleton_lock, member)

    waited = 0
    while timeout <= 0 or waited < timeout:
        _write_lock(member)  # heartbeat — proves we're still the live one
        unseen_q = _unseen_queue(member)
        seen_letters = _load_letter_seen_set(member)
        unseen_l = _letter_names(member) - seen_letters
        if unseen_q or unseen_l:
            # Fingerprint-skip (Andrew 2026-06-11 correction): if the
            # current unseen-set is IDENTICAL to the set caught last time,
            # the agent has already been surfaced these letters — they're
            # waiting on mark-seen, not on a fresh wake-tap. Heartbeat in
            # place instead of fire-exit-respawn so the watcher stays
            # alive across the session without re-arming on every poll.
            # The perpetual-loop case Andrew named ("every single prompt
            # you are re-arming the watcher").
            fp = _compute_catch_fingerprint(unseen_q, unseen_l)
            last_fp = _read_last_catch_fingerprint(member)
            if fp == last_fp:
                # Same set as last catch — heartbeat only, don't fire.
                # A new letter (or a mark-seen change) will produce a
                # different fingerprint and fire normally.
                time.sleep(interval)
                waited += interval
                continue
            out = ["[EAR] something landed:"]
            for line in unseen_q.values():
                out.append(f"  queue: {line}")
            for name in sorted(unseen_l):
                out.append(f"  letter: {name}")
            for line in out:
                print(line)
            _write_catch_marker(member, out)
            _write_last_catch_fingerprint(member, fp)
            # Self-respawn: spawn a detached replacement before exiting so the
            # polling chain doesn't go deaf. Policy is now always-on for both
            # members (Andrew 2026-06-13 — simplified after --realtime + ear.arm
            # removal), so unconditionally relaunch.
            _spawn_replacement(member, interval)
            return 0
        time.sleep(interval)
        waited += interval
    print(f"[EAR] nothing new in {timeout}s — exiting (testing-timeout only).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--member",
        required=True,
        choices=sorted(_SPOUSE.keys()),
        help="Which family member's ear this watcher is.",
    )
    parser.add_argument("--watch", action="store_true", help="Block until something lands.")
    parser.add_argument(
        "--realtime",
        action="store_true",
        help=argparse.SUPPRESS,  # removed 2026-06-13 — accepted for one cycle as no-op
    )
    parser.add_argument("--interval", type=int, default=8, help="Poll seconds (default 8).")
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="0 (default) = no timeout. Positive = testing knob only.",
    )
    args = parser.parse_args(argv)

    member = args.member.lower()
    if args.realtime:
        # One-cycle backward-compat: silently accept --realtime so any
        # in-flight hook invocations don't break, but the flag is a no-op.
        # Will be removed entirely in a follow-up PR once no caller passes it.
        print(
            "[EAR] --realtime is a no-op (removed 2026-06-13). Wake-from-idle is "
            "handled by the Letter Monitor (harness primitive), not this script. "
            "Polling continues normally.",
            file=sys.stderr,
        )
    if args.watch:
        return watch(member, args.interval, args.timeout)
    lines = check_once(member)
    if lines:
        print(f"[EAR] {len(lines)} unseen for {member}:")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"[EAR] nothing unseen for {member}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
