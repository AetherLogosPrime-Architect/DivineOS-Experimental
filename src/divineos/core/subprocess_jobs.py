# mypy: disable-error-code="attr-defined"
# Rationale: this module uses Windows-only ctypes attributes (WinDLL, WinError,
# get_last_error) inside `if _IS_WINDOWS:` guards. Linux CI's mypy doesn't see
# those attributes on ctypes because they're platform-guarded there. Every
# access below is already guarded at runtime; only the static-check needs the
# silence. Alternative approaches (13 line-level ignores, sys.platform-narrow
# refactor) were considered and rejected as either noisier or riskier for a
# substrate-preservation hotfix. This file-level directive is scoped only to
# attr-defined — all other type errors remain in scope.
"""Windows Job Object subprocess wrapper — kernel-guaranteed parent-death-kills-children.

Root fix for orphan-child-process accumulation. `scripts/precommit.sh` and
`scripts/check_push_readiness.sh` spawn heavy pytest and mypy processes; when
the parent bash dies (harness timeout, app close, crash), Windows does NOT
propagate death to children. They keep running and eating RAM. Nearly crashed
Andrew's machine 2026-07-13 with ~5GB of leaked pytest/mypy workers.

This module wraps subprocess spawn so children run inside a Windows Job Object
with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. When the wrapper's Python process
dies for any reason, the OS closes its handle to the job, which triggers
kill-on-close, which terminates every process in the job. Kernel guarantee, no
trap logic required.

Design (Aria review 2026-07-13, both refinements integrated):

1. Children cannot detach. `SetInformationJobObject` leaves both
   `JOB_OBJECT_LIMIT_BREAKAWAY_OK` and `JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK`
   OFF, so a pytest-xdist worker (or any grandchild) cannot create its own
   Job Object to escape the parent job.

2. Startup race closed. Use `CREATE_SUSPENDED` when spawning the child, then
   `AssignProcessToJobObject`, then resume the main thread. The child is
   inside the job before it executes a single instruction.

Non-Windows fallback: `preexec_fn=os.setsid` + `killpg` on timeout. Standard
POSIX process-group semantics — the same intent, different OS primitive.

Pre-reg: `prereg-dae52c6ca269`.

CLI usage:
    python -m divineos.core.subprocess_jobs -- <cmd> [args...]

Called from shell scripts to wrap the heavy invocations. Stdout/stderr are
inherited so the child's output flows through the wrapper unchanged; exit
code is propagated.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import Any

_IS_WINDOWS = os.name == "nt"


if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _JobObjectExtendedLimitInformation = 9

    _CREATE_SUSPENDED = 0x00000004
    _TH32CS_SNAPTHREAD = 0x00000004
    _THREAD_SUSPEND_RESUME = 0x0002
    _INVALID_HANDLE_VALUE = -1
    _RESUME_THREAD_FAIL = 0xFFFFFFFF

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    def _create_kill_on_close_job() -> int:
        job = _kernel32.CreateJobObjectW(None, None)
        if not job:
            raise ctypes.WinError(ctypes.get_last_error())
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        # BREAKAWAY_OK flags left OFF — children cannot escape the job.
        ok = _kernel32.SetInformationJobObject(
            job,
            _JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            err = ctypes.get_last_error()
            _kernel32.CloseHandle(job)
            raise ctypes.WinError(err)
        return int(job)

    def _resume_main_thread(pid: int) -> None:
        """Enumerate threads of pid, resume the (single) main thread.

        A suspended new process has exactly one thread (its main). This
        walks the system thread snapshot to find and resume it. Ugly but
        avoids reimplementing CreateProcess in ctypes just to get a thread
        handle back from Popen.
        """
        snap = _kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0)
        if snap == _INVALID_HANDLE_VALUE or snap == 0:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            entry = _THREADENTRY32()
            entry.dwSize = ctypes.sizeof(_THREADENTRY32)
            if not _kernel32.Thread32First(snap, ctypes.byref(entry)):
                raise ctypes.WinError(ctypes.get_last_error())
            while True:
                if entry.th32OwnerProcessID == pid:
                    thread_h = _kernel32.OpenThread(
                        _THREAD_SUSPEND_RESUME, False, entry.th32ThreadID
                    )
                    if thread_h:
                        try:
                            if _kernel32.ResumeThread(thread_h) == _RESUME_THREAD_FAIL:
                                raise ctypes.WinError(ctypes.get_last_error())
                            return
                        finally:
                            _kernel32.CloseHandle(thread_h)
                if not _kernel32.Thread32Next(snap, ctypes.byref(entry)):
                    break
            raise RuntimeError(f"No main thread found for pid {pid}")
        finally:
            _kernel32.CloseHandle(snap)


def run_managed(
    cmd: list[str],
    *,
    timeout: float | None = None,
    cwd: str | os.PathLike | None = None,
    env: dict[str, str] | None = None,
    stdout: Any = None,
    stderr: Any = None,
) -> subprocess.CompletedProcess:
    """Run ``cmd`` as a subprocess inside a job that dies with our process.

    On Windows: wrapped in a Job Object with KILL_ON_JOB_CLOSE — when this
    Python process exits for any reason, the OS terminates the child and
    all its descendants.

    On POSIX: process group via ``setsid``; ``killpg`` on timeout.

    Returns a ``subprocess.CompletedProcess`` when the child exits normally.
    Raises ``subprocess.TimeoutExpired`` if ``timeout`` is reached.
    """
    if _IS_WINDOWS:
        result_win: subprocess.CompletedProcess = _run_managed_windows(
            cmd, timeout, cwd, env, stdout, stderr
        )
        return result_win
    result_posix: subprocess.CompletedProcess = _run_managed_posix(
        cmd, timeout, cwd, env, stdout, stderr
    )
    return result_posix


def _run_managed_windows(cmd, timeout, cwd, env, stdout, stderr) -> subprocess.CompletedProcess:
    job = _create_kill_on_close_job()
    proc: subprocess.Popen | None = None
    try:
        # Spawn suspended so the child is frozen until assigned to the job.
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=_CREATE_SUSPENDED,
        )
        # Assign before any child code has run.
        # proc._handle is Windows-only internal Popen state; mypy's cross-platform
        # stubs don't model it. Documented in Python source; stable since 3.0.
        if not _kernel32.AssignProcessToJobObject(job, int(proc._handle)):  # type: ignore[attr-defined]
            err = ctypes.get_last_error()
            proc.terminate()
            raise ctypes.WinError(err)
        # Resume the main thread now that the child is inside the job.
        _resume_main_thread(proc.pid)
        # Standard wait; on timeout let the caller see it. Closing the job
        # in the finally block will kill any remaining processes.
        stdout_data, stderr_data = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout_data, stderr_data)
    finally:
        # Closing the job handle triggers KILL_ON_JOB_CLOSE for anything
        # still alive in it. If the child already exited normally, this
        # is a no-op on the child side.
        _kernel32.CloseHandle(job)


def _run_managed_posix(cmd, timeout, cwd, env, stdout, stderr) -> subprocess.CompletedProcess:
    # os.setsid / killpg / getpgid / signal.SIGKILL are POSIX-only; mypy on
    # Windows flags them as missing. This branch never executes on Windows
    # (guarded by _IS_WINDOWS in run_managed) so the type-ignores are safe.
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        preexec_fn=os.setsid,  # type: ignore[attr-defined]
    )
    try:
        stdout_data, stderr_data = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # type: ignore[attr-defined]
        except (ProcessLookupError, PermissionError):
            pass
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout_data, stderr_data)


def _pid_alive(pid: int) -> bool:
    """Return True iff the OS reports pid as a live, non-zombie process."""
    if _IS_WINDOWS:
        _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        _STILL_ACTIVE = 259
        h = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            exit_code = wintypes.DWORD()
            if not _kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code)):
                return False
            return exit_code.value == _STILL_ACTIVE
        finally:
            _kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _watch_parent(initial_ppid: int, poll_seconds: float = 1.0) -> None:
    """Watchdog thread: exit this process if the recorded parent dies.

    Belt-and-suspenders for the CLI wrapper case (invoked from bash /
    another script). If our parent gets killed but this Python wrapper
    survives, the job handle stays open and the child keeps running —
    the exact leak this module exists to close. Exiting on parent-death
    releases the job handle, kill-on-close fires, child dies.
    """
    import time as _time

    while True:
        if not _pid_alive(initial_ppid):
            # Hard exit — releases all handles, including the job.
            os._exit(1)
        _time.sleep(poll_seconds)


def _main(argv: list[str]) -> int:
    """CLI entry point for shell-script wrapping.

    Usage:
        python -m divineos.core.subprocess_jobs -- <cmd> [args...]

    The `--` is optional; anything after it is the wrapped command.
    Stdout/stderr are inherited from this wrapper (no capture) so the
    child's output streams unchanged. Exit code is the child's.

    Also arms a watchdog thread: if the process that invoked us dies,
    we exit ourselves so the job's kill-on-close terminates the child.
    """
    args = argv[1:] if argv and argv[0] == "--" else argv
    if not args:
        print("usage: python -m divineos.core.subprocess_jobs -- <cmd> [args...]", file=sys.stderr)
        return 2
    # Arm the parent-death watchdog before spawning anything.
    import threading

    watchdog = threading.Thread(target=_watch_parent, args=(os.getppid(),), daemon=True)
    watchdog.start()
    try:
        result = run_managed(args, stdout=None, stderr=None)
        return result.returncode
    except subprocess.TimeoutExpired:
        return 124  # convention: same as GNU timeout(1)
    except FileNotFoundError as e:
        print(f"subprocess_jobs: {e}", file=sys.stderr)
        return 127
    except KeyboardInterrupt:
        # Ctrl-C hits us — job cleanup happens via finally, killing the child.
        return 130


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
