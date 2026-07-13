"""Push orchestrator — foreground git push with file-lock serialization
and ledger-event alarms so silent push-failures become structurally
impossible.

FOSSIL (Andrew 2026-06-24):
After committing 7 branches in a row, the agent ran the push-queue
helper (scripts/push_queued.py) with output redirected to dev-null
and backgrounded (`> /dev/null 2>&1 &`). On 5 of the 7 branches the
script file didn't exist (those branches were cut from origin/main
before the helper was committed). Every silent-error invocation
no-op'd. The agent didn't notice. Andrew caught "4 PRs in the repo"
and asked how many were waiting — the gap was visible only because
he counted.

ROOT FIX (per prereg-a9ecf79d250d):
1. Replace the standalone script with a divineos CLI command. Since
   divineos is pip-installed editable, `divineos push <branch>` works
   from ANY branch's working directory regardless of whether that
   branch contains the helper source.
2. Every push attempt emits ledger events: PUSH_QUEUED → PUSH_RUNNING
   → PUSH_DONE / PUSH_FAILED. A QUEUED-but-never-resolved event in
   the ledger is the visible-gap that catches silent failure.
3. Foreground execution by default. The background-with-discarded-
   output shape was the silent-failure root.
4. The file-lock from push_queued.py is preserved so concurrent
   invocations serialize naturally — but each invocation IS its own
   foreground process with its own loud exit code.

NON-GOALS:
- No retry on push failure. A failed push is loud; the operator
  decides whether to retry.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

DEFAULT_LOCK_TIMEOUT_SECONDS = 7200


def _lockfile_path() -> Path:
    """Where the cross-invocation push-serialization lock lives."""
    state_dir = Path.home() / ".divineos-aether"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "push-queue.lock"


def _ledger_log(event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort ledger emission. Never raises into the caller."""
    try:
        from divineos.core.ledger import log_event

        log_event(event_type=event_type, actor="aether", payload=payload)
    except (ImportError, OSError, KeyError, TypeError, ValueError, RuntimeError):
        pass


def _emit_status(line: str) -> None:
    """Operator-facing status line on stderr. Always fires."""
    import sys

    try:
        print(line, file=sys.stderr, flush=True)
    except OSError:
        pass


@dataclass
class PushResult:
    """Outcome of one push_branch invocation."""

    branch: str = ""
    exit_code: int = 0
    succeeded: bool = False
    stage: str = ""  # 'queued' / 'running' / 'done' / 'failed' / 'lock-timeout'
    note: str = ""
    extra_args: list[str] = field(default_factory=list)


def push_branch(
    branch: str,
    extra_args: list[str] | None = None,
    *,
    lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    remote: str = "origin",
) -> PushResult:
    """Push `branch` to `remote` foreground, with file-lock + ledger events.

    Returns a PushResult. Emits stderr + ledger events at each stage.
    Concurrent invocations block on a single file-lock.
    """
    extra_args = extra_args or []

    queued_payload: dict[str, Any] = {
        "branch": branch,
        "remote": remote,
        "extra_args": extra_args,
    }
    _ledger_log("PUSH_QUEUED", queued_payload)
    _emit_status(f"[push-orchestrator] QUEUED branch={branch}")

    lock = FileLock(str(_lockfile_path()), timeout=lock_timeout_seconds)

    try:
        with lock:
            _ledger_log("PUSH_RUNNING", queued_payload)
            _emit_status(f"[push-orchestrator] RUNNING branch={branch}")

            cmd = ["git", "push", "-u", remote, branch] + extra_args
            result = subprocess.run(cmd, check=False)
            exit_code = result.returncode

            done_payload: dict[str, Any] = dict(queued_payload)
            done_payload["exit_code"] = exit_code

            if exit_code == 0:
                _ledger_log("PUSH_DONE", done_payload)
                _emit_status(f"[push-orchestrator] DONE branch={branch} (exit 0)")
                return PushResult(
                    branch=branch,
                    exit_code=0,
                    succeeded=True,
                    stage="done",
                    note=f"pushed to {remote}/{branch}",
                    extra_args=extra_args,
                )
            else:
                _ledger_log("PUSH_FAILED", done_payload)
                _emit_status(f"[push-orchestrator] FAILED branch={branch} exit={exit_code}")
                return PushResult(
                    branch=branch,
                    exit_code=exit_code,
                    succeeded=False,
                    stage="failed",
                    note=f"git push exited {exit_code} (see output above)",
                    extra_args=extra_args,
                )
    except Timeout:
        timeout_payload: dict[str, Any] = dict(queued_payload)
        timeout_payload["lock_timeout_seconds"] = lock_timeout_seconds
        _ledger_log("PUSH_FAILED", timeout_payload)
        msg = (
            f"[push-orchestrator] LOCK-TIMEOUT branch={branch} "
            f"(waited {lock_timeout_seconds}s for prior push to complete)"
        )
        _emit_status(msg)
        return PushResult(
            branch=branch,
            exit_code=3,
            succeeded=False,
            stage="lock-timeout",
            note=msg,
            extra_args=extra_args,
        )
