"""One full test suite at a time on this machine.

2026-10-16: seven pushes started within seconds of each other and the computer crashed. Each one
passed system_load_check, which reads free memory once at spawn, and then each ran a wide worker
pool. A check done before the work is a race when several arrive together, so the answer is not a
better reading but a single turnstile: only the holder runs a suite, everyone else waits.

The lock is a directory (mkdir is atomic on every platform). It records its owner's pid and is
taken over when that process no longer exists, so a push that died cannot hold the line forever.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a declared dependency
    psutil = None  # type: ignore[assignment]

POLL_SECONDS = 5.0


def lock_dir() -> Path:
    override = os.environ.get("DIVINEOS_SUITE_SLOT_DIR")
    return Path(override) if override else Path.home() / ".divineos" / "suite_slot.lock"


def _alive(pid: int) -> bool:
    return psutil is not None and psutil.pid_exists(pid)


def _owner(path: Path) -> int | None:
    try:
        return int((path / "owner").read_text().strip())
    except (OSError, ValueError):
        return None


def try_acquire(owner_pid: int) -> bool:
    path = lock_dir()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir()
    except FileExistsError:
        held_by = _owner(path)
        if held_by is not None and _alive(held_by):
            return False
        if held_by is None:
            # Between the holder's mkdir and its owner write the dir is briefly ownerless;
            # only an ownerless dir that has sat for a while was abandoned.
            try:
                if time.time() - path.stat().st_mtime < 30:
                    return False
            except OSError:
                return False
        # Owner gone, or the owner file was never written (died between mkdir and write).
        # Remove and retry once; losing this race to another waiter just means False.
        try:
            (path / "owner").unlink(missing_ok=True)
            path.rmdir()
            path.mkdir()
        except OSError:
            return False
    (path / "owner").write_text(str(owner_pid))
    return True


def release(owner_pid: int) -> None:
    path = lock_dir()
    if _owner(path) != owner_pid:
        return
    (path / "owner").unlink(missing_ok=True)
    try:
        path.rmdir()
    except OSError:
        pass


def acquire(owner_pid: int, poll: float = POLL_SECONDS) -> None:
    said = False
    while not try_acquire(owner_pid):
        if not said:
            print(
                f"[suite-slot] another full test run is going (pid {_owner(lock_dir())}); "
                "waiting my turn so the machine is not asked to run two at once.",
                file=sys.stderr,
            )
            said = True
        time.sleep(poll)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("acquire", "release"):
        print(
            "usage: python -m divineos.core.suite_slot acquire|release OWNER_PID", file=sys.stderr
        )
        return 2
    pid = int(argv[2])
    if argv[1] == "acquire":
        acquire(pid)
    else:
        release(pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
