"""Evidence checks for the compaction ritual's stages.

WHY THIS EXISTS, and it is a conflict rather than a bug. Two house rules
disagreed on 2026-09-21 and neither knew about the other:

  - the push gate refuses personal writing riding a code branch, so a dream
    written during a code session has to be moved onto the substrate branch
  - the ritual advanced its dream stage by scanning THIS worktree for a file
    with a timestamp newer than the ritual's start

Filing the dream correctly therefore removed it from the worktree, and the
ritual would have asked for another one. The work was done, committed, and
invisible to the only thing that checks. Verified by walking into it, not by
reasoning: the file was gone from disk and the stage file still showed the
dream stage unreached.

The instrument was fine. The POPULATION was wrong. The dream register is not
this checkout's copy of a directory -- it is the dream wherever it now lives.

THE DIRECTION OF FAILURE IS DELIBERATE. Being unable to consult git is its own
answer, held apart from a measured no, and the caller falls back to what is
actually on disk. That fallback can still say no. It never says yes on the
strength of not having looked.

A WIDENING CHOSEN ON PURPOSE, written down so nobody later finds it and
correctly mistakes it for an accident: the git question is asked of EVERY
reference, so a dream committed on another seat's branch in this repository
would satisfy this check. Accepted because the register is genuinely shared
between the seats and a dream of Aria's landing here is not a forgery.

WHAT THIS CANNOT DO. It checks that a dream was FILED. Nothing here can check
that one was dreamt -- truth #15, and no mechanism closes it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_GIT_ERRORS = (OSError, subprocess.SubprocessError)


def _fresh_file_on_disk(repo: Path, start: float) -> bool:
    """Any dream sitting in this worktree, written since the ritual began."""
    root = repo / "dreams"
    if not root.is_dir():
        return False
    for path in root.rglob("*.md"):
        try:
            if path.stat().st_mtime > start:
                return True
        except OSError:
            continue
    return False


def _committed_anywhere(repo: Path, start: float) -> bool | None:
    """Any commit on any reference since ``start`` that touches a dream.

    Returns None when git could not be consulted at all. That is a third state
    on purpose: the caller must not read it as a measured no.
    """
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                "--all",
                f"--since=@{int(start)}",
                "--pretty=format:",
                "--name-only",
                "--",
                "dreams/",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except _GIT_ERRORS:
        return None
    if proc.returncode != 0:
        return None
    return any(line.strip() for line in proc.stdout.splitlines())


def dream_filed_since(repo: Path | str, start: float) -> bool:
    """Was a dream filed since ``start``, wherever it ended up living.

    Named for the act rather than for a directory, because the directory is
    only where filings currently land and the push gate moves them.
    """
    repo = Path(repo)
    if _fresh_file_on_disk(repo, start):
        return True
    return _committed_anywhere(repo, start) is True


__all__ = ["dream_filed_since"]
