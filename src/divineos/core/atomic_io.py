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

from pathlib import Path


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)


__all__ = ["atomic_write_text"]
