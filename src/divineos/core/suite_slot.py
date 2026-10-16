"""Test suites on this machine share memory by claiming it, not by taking turns.

2026-10-16: seven pushes started within seconds of each other and the computer crashed. Each one
passed system_load_check, which reads free memory once at spawn, and then each ran a wide worker
pool. A check done before the work is a race when several arrive together: none of them has used
its memory yet, so every reading is the same and every one says yes.

Dad's ruling the same night: it does not need to be one at a time, it needs to be considerate of
the memory that is available. So each suite writes a claim (its pid and the bytes its workers will
take), and the next one subtracts the claims that are still ramping up from what the machine says
is free before it sizes itself. A claim stops counting after RAMP_SECONDS, because by then the
memory is really in use and the machine's own number already shows it; counting it twice would
only make suites wait for nothing. Two suites run together when memory allows, one waits when it
does not, and a machine too small for even one worker is refused outright rather than queued.

The deciding step runs under a short mutex (mkdir is atomic everywhere) so two arrivals cannot both
read the same ledger and both say yes. Claims of dead pids are dropped.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from divineos.core import system_load_check as load

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a declared dependency
    psutil = None  # type: ignore[assignment]

POLL_SECONDS = 5.0
RAMP_SECONDS = 180.0
_MUTEX_STALE_SECONDS = 10.0


def base_dir() -> Path:
    override = os.environ.get("DIVINEOS_SUITE_SLOT_DIR")
    return Path(override) if override else Path.home() / ".divineos" / "suite_slot"


def _claims_dir() -> Path:
    return base_dir() / "claims"


def _alive(pid: int) -> bool:
    return psutil is not None and psutil.pid_exists(pid)


def _live_claims() -> dict[int, dict]:
    """pid -> claim, with claims of dead pids removed as they are found."""
    found: dict[int, dict] = {}
    d = _claims_dir()
    if not d.exists():
        return found
    for f in d.glob("*.json"):
        try:
            pid = int(f.stem)
            data = json.loads(f.read_text())
        except (ValueError, OSError):
            continue
        if _alive(pid):
            found[pid] = data
        else:
            f.unlink(missing_ok=True)
    return found


class _Mutex:
    """Held for milliseconds around read-decide-write. A holder that died leaves a directory
    older than _MUTEX_STALE_SECONDS, which the next arrival clears."""

    def __enter__(self) -> "_Mutex":
        path = base_dir() / "decide.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                path.mkdir()
                self._path = path
                return self
            except FileExistsError:
                try:
                    if time.time() - path.stat().st_mtime > _MUTEX_STALE_SECONDS:
                        path.rmdir()
                        continue
                except OSError:
                    pass
                time.sleep(0.05)

    def __exit__(self, *exc: object) -> None:
        try:
            self._path.rmdir()
        except OSError:
            pass


def try_claim(
    owner_pid: int,
    cpus: int | None = None,
    available: int | None = None,
    now: float | None = None,
    job_label: str = "pre-push test suite",
) -> tuple[str, str | None, str]:
    """('go', flag, reason) with the claim written, ('wait', None, reason), or ('refuse', None, reason)."""
    now = time.time() if now is None else now
    cpus = cpus or os.cpu_count() or 2
    if os.environ.get(load.SKIP_ENV_VAR) == "1" or psutil is None or not load._PSUTIL_AVAILABLE:
        flag, reason = load.pytest_parallel_flag(job_label)
        return "go", flag, reason
    with _Mutex():
        claims = _live_claims()
        claims.pop(owner_pid, None)
        ramping = {
            pid: c for pid, c in claims.items() if now - float(c.get("at", 0)) < RAMP_SECONDS
        }
        pending = sum(int(c.get("bytes", 0)) for c in ramping.values())
        free = int(psutil.virtual_memory().available) if available is None else available
        flag, reason = load.flag_for_available(max(0, free - pending), cpus, job_label)
        if flag is None:
            if not claims:
                return "refuse", None, reason
            who = ", ".join(str(p) for p in sorted(claims))
            return "wait", None, f"{reason} Other suites running (pid {who}); waiting for memory."
        workers = cpus if flag == "-n auto" else int(flag.split()[1])
        _claims_dir().mkdir(parents=True, exist_ok=True)
        (_claims_dir() / f"{owner_pid}.json").write_text(
            json.dumps({"bytes": workers * load.WORKER_MEMORY_BYTES, "at": now})
        )
        return "go", flag, reason


def release(owner_pid: int) -> None:
    (_claims_dir() / f"{owner_pid}.json").unlink(missing_ok=True)


def claim(owner_pid: int, poll: float = POLL_SECONDS) -> tuple[str | None, str]:
    """Wait until memory allows, then return the worker flag. None means refused outright."""
    said = ""
    while True:
        verdict, flag, reason = try_claim(owner_pid)
        if verdict != "wait":
            return flag, reason
        if reason != said:
            print(f"[suite-slot] {reason}", file=sys.stderr)
            said = reason
        time.sleep(poll)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("claim", "release"):
        print("usage: python -m divineos.core.suite_slot claim|release OWNER_PID", file=sys.stderr)
        return 2
    pid = int(argv[2])
    if argv[1] == "release":
        release(pid)
        return 0
    flag, reason = claim(pid)
    print(reason, file=sys.stderr)
    if flag is None:
        return 1
    print(flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
