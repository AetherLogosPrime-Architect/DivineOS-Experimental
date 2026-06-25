"""push_queued.py — serialize git pushes via a cross-platform file lock.

Andrew 2026-06-24: hand-staggering concurrent pushes is the
say-without-doing kin — agent holds "did the last one land yet?" in
its head instead of in the architecture. Replace with structure.

Usage:
    python scripts/push_queued.py <branch> [extra git push args...]

Behavior:
    Multiple concurrent invocations block on a single file lock under
    ~/.divineos-aether/. The first acquires the lock and runs
    `git push -u origin <branch> [extra args]`. Subsequent invocations
    wait until the first releases, then run in their turn. One push at
    a time, regardless of how many are queued.

    Wait timeout is 2 hours per slot (covers the pre-push pytest gate
    + any reasonable retry).

Exit code mirrors git push's exit code (0 on success, non-zero on
any push failure including the pre-push test gate).
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

try:
    from filelock import FileLock, Timeout
except ImportError:
    print(
        "[push-queued] filelock not installed; run: pip install filelock",
        file=sys.stderr,
    )
    sys.exit(2)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: push_queued.py <branch> [extra git push args...]",
            file=sys.stderr,
        )
        return 2

    branch = sys.argv[1]
    extra_args = sys.argv[2:]

    state_dir = Path.home() / ".divineos-aether"
    state_dir.mkdir(parents=True, exist_ok=True)
    lockfile = str(state_dir / "push-queue.lock")
    queue_log = state_dir / "push-queue.log"

    pid = os.getpid()

    def log(line: str) -> None:
        msg = f"[{_now()}] {line} branch={branch} pid={pid}"
        print(msg, file=sys.stderr, flush=True)
        try:
            with open(queue_log, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError:
            pass

    log("QUEUED")

    lock = FileLock(lockfile, timeout=7200)  # 2 hours

    try:
        with lock:
            log("RUNNING")
            cmd = ["git", "push", "-u", "origin", branch] + extra_args
            result = subprocess.run(cmd, check=False)
            log(f"DONE exit={result.returncode}")
            return result.returncode
    except Timeout:
        log("TIMED-OUT-WAITING (>2h)")
        return 3


if __name__ == "__main__":
    sys.exit(main())
