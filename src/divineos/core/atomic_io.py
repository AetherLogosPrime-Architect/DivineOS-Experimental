"""Atomic file I/O helpers for marker and state files.

Audit finding 2026-05-03 round 4: 7 marker files in core/ wrote JSON
state non-atomically:

    path.write_text(json.dumps(payload), encoding="utf-8")

If the process is killed (signal, OOM, power loss) mid-write, the
target file is left half-written. The reader code uses
``try: json.loads(...) except: {}`` — so corruption is silently
recovered as "no marker." The recovery semantics are
wrong-direction: a corruption clears an active gate. For example,
``theater_marker.py`` writes ``theater_unresolved.json`` to gate
non-bypass tools until the agent acknowledges a violation; if a
write is interrupted mid-flight, the next reader treats it as
cleared and the gate self-heals into "no theater detected"
without anyone clearing it intentionally.

This module's ``atomic_write_text`` performs a write-then-rename:
the target is replaced atomically (POSIX) or near-atomically
(Windows). The reader either sees the prior state or the new
state, never a partial state. A few extra lines per call site, no
new dependencies.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

_REPLACE_ATTEMPTS = 5
_REPLACE_BACKOFF_SECONDS = 0.05


def _temp_for(path: Path, per_process: bool) -> Path:
    """The temporary name written beside ``path``.

    One fixed name is right when a single writer owns the file. When two processes can write the
    same file at the same moment (the words door's index, built by Aria's window and Aether's),
    each needs a name of its own, or their bytes interleave in one temporary and the swap installs
    the mixture: the old shelf code guarded this with pid-named temporaries, and moving it onto the
    shared writer without the option would have removed that guard."""
    suffix = f".{os.getpid()}.tmp" if per_process else ".tmp"
    return path.with_suffix(path.suffix + suffix)


def atomic_write_text(
    path: Path, content: str, encoding: str = "utf-8", per_process: bool = False
) -> None:
    """Write ``content`` to ``path`` atomically.

    Sequence:
      1. Write to ``path.with_suffix(path.suffix + '.tmp')``
      2. ``Path.replace`` the temp into the target (atomic on POSIX,
         near-atomic on Windows — Windows' MoveFileEx with
         REPLACE_EXISTING is the closest available primitive).

    The temp file lives in the same directory as the target so the
    rename can't cross filesystem boundaries (which would degrade
    to a copy + unlink pair).

    If the write or rename raises, the temp file may be left behind;
    callers are responsible for tolerating stale ``.tmp`` files in
    their state directories. Cleanup is a separate concern from
    correctness — a leftover ``.tmp`` doesn't corrupt the target.
    """
    tmp = _temp_for(path, per_process)
    with open(tmp, "w", encoding=encoding) as fh:
        fh.write(content)
        fh.flush()
        # Wait for the bytes to reach the disk before the swap, so a power
        # cut after the rename cannot leave the new name pointing at an
        # empty file (2026-09-28, while moving the brake onto this helper).
        os.fsync(fh.fileno())
    _swap(tmp, path)


def atomic_write_bytes(path: Path, data: bytes, per_process: bool = False) -> None:
    """The same write-then-rename for binary content (a numpy array's bytes).

    Added 2026-10-05 for the words door's vector file. It shares the swap, with
    its Windows lock retry, rather than keeping a second writer that behaves
    differently when an antivirus scan holds the target.
    """
    tmp = _temp_for(path, per_process)
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    _swap(tmp, path)


def _swap(tmp: Path, path: Path) -> None:
    # Windows refuses the rename with PermissionError while another process
    # (antivirus, the search indexer) briefly holds the target. Pulling the
    # brake must not fail on that, so retry a few times before raising
    # (council walk 2026-09-28, the Wayne lens).
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_BACKOFF_SECONDS * (attempt + 1))


__all__ = ["atomic_write_bytes", "atomic_write_text"]
