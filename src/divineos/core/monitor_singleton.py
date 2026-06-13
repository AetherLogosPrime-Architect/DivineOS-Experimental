"""Named-mutex singleton primitive for long-running Monitor processes.

Deep-research 2026-06-13 surfaced this as the canonical Windows mechanism
for self-singleton enforcement when the parent harness drops task handles
on session-resume. The kernel manages the mutex lifecycle: handles
auto-release on process termination (including crash-kill), the object
is destroyed when the last handle closes, and the create-or-attach
operation is atomic at the syscall level (no race-on-launch).

Why this instead of a file-based heartbeat:
- No stale-file problem. The kernel cleans up on process death.
- No mtime-resolution arguments to debate.
- No regex-self-match (the bug the prior PowerShell-scan singleton hit).
- No race between check and write at process startup.

Sources cited in the deep-research synthesis (verified 3-0 unless noted):
- learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexa
- timgolden.me.uk/pywin32-docs/win32event.html
- learn.microsoft.com/en-us/archive/technet-wiki/34423.create-a-single-instance-desktop-application

## Identity model

Each long-running Monitor process declares its role by name (e.g.
"letter", "compaction"). The mutex name is computed from the role
through ``mutex_name_for_role``. Roles are role-stable (the letter
Monitor is "the letter monitor" regardless of which process happens
to be running it), so the identity does not change across launches
and the singleton-detection always finds the right siblings.

The mutex name is in the ``Local\\`` namespace (per-session), NOT
``Global\\``. Per-session is correct because a different Windows
user session SHOULD be able to run its own letter Monitor — global
would prevent that. The Monitor processes share the operator's
session by design.

## Usage

    from divineos.core.monitor_singleton import acquire_or_exit
    mutex_handle = acquire_or_exit("letter")  # exits 0 if sibling alive
    # ...run the polling loop...
    # mutex auto-releases on process exit; nothing to clean up

## Non-Windows fallback

On non-Windows platforms the module no-ops (returns a sentinel
handle and never reports siblings). This is safe-default — the dup
problem the module solves is Windows-specific (Claude Code Monitor
harness behavior on this platform). On Linux/macOS, parent-process
death reaps children normally via SIGCHLD, so the orphan-accumulation
failure mode does not exist.
"""

from __future__ import annotations

import os
import sys
from typing import Any

_MUTEX_NAMESPACE = "Local"  # per-session; intentionally not Global
_MUTEX_PREFIX = "divineos_monitor_"


def mutex_name_for_role(role: str) -> str:
    """Return the kernel mutex name for a Monitor role.

    Role-stable: same name for the same role across all launches, so
    sibling detection always finds the right peer. The role string is
    normalized to lowercase and stripped of separators so cosmetic
    variation doesn't fork the identity.
    """
    normalized = role.strip().lower().replace(" ", "_").replace("-", "_")
    return f"{_MUTEX_NAMESPACE}\\{_MUTEX_PREFIX}{normalized}"


def _is_windows() -> bool:
    return os.name == "nt"


def acquire(role: str) -> tuple[Any, bool]:
    """Try to acquire the named mutex for ``role``.

    Returns ``(handle, was_already_held)``. The ``was_already_held``
    flag is True iff another live process already held the mutex when
    we called CreateMutex. The caller is expected to exit cleanly in
    that case.

    On non-Windows: returns ``(None, False)`` — the dup problem is
    Windows-specific and the singleton-guard no-ops elsewhere.

    On Windows but missing pywin32: returns ``(None, False)`` with a
    stderr warning. Fail-open so a missing dependency never breaks a
    Monitor — the worst case reduces to the prior behavior (possible
    dup), not a launch refusal.
    """
    if not _is_windows():
        return None, False
    try:
        import win32api
        import win32event
        import winerror
    except ImportError:
        print(
            "[monitor-singleton] pywin32 not installed; skipping singleton guard. "
            "Install via: pip install pywin32",
            file=sys.stderr,
        )
        return None, False

    name = mutex_name_for_role(role)
    # CreateMutex: if name exists, returns handle to existing object
    # AND GetLastError reports ERROR_ALREADY_EXISTS. This is the
    # canonical Windows single-instance idiom (MS Learn).
    handle = win32event.CreateMutex(None, False, name)
    last_error = win32api.GetLastError()
    was_already_held = last_error == winerror.ERROR_ALREADY_EXISTS
    return handle, was_already_held


def acquire_or_exit(role: str, exit_code: int = 0) -> Any:
    """Convenience: acquire the mutex or exit cleanly if a sibling holds it.

    Prints a named ``[MONITOR-SINGLETON-DEDUP role=...]`` line on the
    sibling-detected path so the operator can see the singleton-guard
    fired. Returns the mutex handle on the acquired-the-slot path;
    the caller holds it for the rest of the process lifetime (kernel
    auto-releases on exit).
    """
    handle, was_already_held = acquire(role)
    if was_already_held:
        print(
            f"[MONITOR-SINGLETON-DEDUP role={role}] sibling already alive; "
            "exiting without arming (kernel-mutex singleton-guard)"
        )
        sys.exit(exit_code)
    return handle


def is_held(role: str) -> bool:
    """Check whether the named mutex for ``role`` is currently held.

    Used by the gate (require-monitors-armed.sh) to determine whether
    a Monitor of this role is alive WITHOUT spawning a process or
    scanning command-lines. Uses CreateMutex (same primitive as
    ``acquire``) and reads GetLastError — if ERROR_ALREADY_EXISTS,
    some other process holds the named object. The probe's own handle
    is closed immediately; if it was the only handle, the kernel
    destroys the object cleanly.

    Why CreateMutex instead of OpenMutex: OpenMutex requires explicit
    access rights and may not see Local\\ mutexes across some pywin32
    versions / process boundaries. CreateMutex's "attach to existing
    if present, otherwise create new" semantics are more reliable
    cross-process and match the canonical Windows single-instance idiom.

    On non-Windows or missing pywin32: returns False (fail-safe — the
    gate will say "not armed" and prompt the operator to arm).
    """
    if not _is_windows():
        return False
    try:
        import win32api
        import win32event
        import winerror
    except ImportError:
        return False

    name = mutex_name_for_role(role)
    try:
        handle = win32event.CreateMutex(None, False, name)
        last_error = win32api.GetLastError()
        win32api.CloseHandle(handle)
        return bool(last_error == winerror.ERROR_ALREADY_EXISTS)
    except Exception:  # noqa: BLE001 — probe must never raise; gate fail-safe
        return False
