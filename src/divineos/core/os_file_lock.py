"""One writer at a time on a small file, by the operating system's own lock.

Nobody here ever judges whether a holder is dead or slow: the system releases the lock the instant the
holding process ends, however it ends, and a holder that is merely slow keeps it. A lock file with an age had
both defects, a check and then a write with a gap between them, and a slow holder presumed dead (Aletheia's
holds on #686 and #736). `suite_slot.py` and `his_words_bundle.py` each carry their own copy of the two calls
below; this is the shared one, used first by the kept-out list, so a third copy is not made. Moving the other
two onto it is owed, not done here.
"""

from __future__ import annotations

import errno
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

_BUSY_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}


class LockBusy(Exception):
    """Someone else held the lock for the whole wait."""


def try_lock(fh) -> bool:
    """Take the lock on the open file without waiting. False if someone else holds it.

    Only "someone else holds it" means busy; a read-only folder or a bad handle never clears by waiting,
    so it raises instead of being spun on."""
    try:
        if sys.platform == "win32":
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno in _BUSY_ERRNOS:
            return False
        raise
    return True


def unlock(fh) -> None:
    if sys.platform == "win32":
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextmanager
def held(path: Path, wait_seconds: float = 5.0, poll: float = 0.02) -> Iterator[None]:
    """Hold the lock on `path` for the body of the with. Raises LockBusy if it is not free within the wait.

    A leftover file with nobody holding it does not block: the lock is the system's, not the file's."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        deadline = time.monotonic() + wait_seconds
        while not try_lock(fh):
            if time.monotonic() >= deadline:
                raise LockBusy(f"another writer holds {path.name}")
            time.sleep(poll)
        try:
            yield
        finally:
            unlock(fh)
    finally:
        fh.close()
