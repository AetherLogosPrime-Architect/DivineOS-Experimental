"""Which paths are substrate, and which are work in progress.

The declaration half of the branch-blind checkpoint fix (Aria + Aether,
2026-08-27). Aether takes the mechanism: substrate commits go to a named
branch by plumbing, never by checkout. This module answers the question
that mechanism cannot answer for itself — WHICH paths belong there.

The fix is not a new list. ``ExternalChannel`` already declares, per
channel, where in the repo its files land. That declaration was being
thrown away: ``auto_commit_substrate`` synced the channels and then ran
``git add -A``, so the sweep took the whole dirty tree and sealed it into
one commit with the synced files. Seventy-five letters landed on one
split and eighty on another because nothing downstream of the sync knew
the difference between what it had just pulled in and what happened to
be lying around.

So the boundary is: **a path is substrate only if a declared channel
says it is.** Everything else is work in progress and stays on HEAD.

THE FAIL DIRECTION IS DELIBERATE AND IT IS NOT SYMMETRIC. An unknown
path classifies as work, never as substrate. Misfiling work as substrate
is the bug we are fixing — it puts half-finished edits onto the branch
other people review. Misfiling substrate as work costs one letter left
uncommitted until the next checkpoint, which is visible and recoverable.
One direction is loud and cheap; the other is quiet and expensive.

An empty channel set raises rather than classifying everything as work.
Zero channels is a broken configuration, and a broken configuration that
answers every question with "work in progress" looks exactly like a
working one that has nothing to sync.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from divineos.core.uncommitted_work_check import DEFAULT_CHANNELS, ExternalChannel


class NoChannelsDeclared(RuntimeError):
    """No external channels were declared, so nothing can be classified.

    Raised rather than returning "everything is work in progress",
    because the two are indistinguishable at the call site and only one
    of them is correct.
    """


def substrate_mirrors(
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> tuple[PurePosixPath, ...]:
    """The repo-relative directories that declared channels write into.

    Derived from the channel definitions rather than restated here. A
    second copy of this list would drift from the first, and the drift
    would be silent — the sweep would keep working while quietly
    disagreeing about one directory.
    """
    if not channels:
        raise NoChannelsDeclared("no external channels declared; cannot classify paths")
    return tuple(PurePosixPath(c.repo_mirror.as_posix()) for c in channels)


def is_substrate_path(
    rel_path: str | Path,
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> bool:
    """True when ``rel_path`` lies inside a declared channel mirror.

    ``rel_path`` is repo-relative, in either separator style — git
    porcelain emits forward slashes and Windows callers hold backslashes,
    and a classifier that silently disagreed with itself depending on
    which one it got would be the same class of fault it exists to stop.

    A path that escapes the repo root (``..``) is work, not substrate.
    Nothing outside the repo can be inside a mirror, and treating an
    escape as a match would let a traversal write to the reviewed branch.
    """
    mirrors = substrate_mirrors(channels)
    candidate = PurePosixPath(str(rel_path).replace("\\", "/"))
    if ".." in candidate.parts:
        return False
    return any(candidate.is_relative_to(m) for m in mirrors)


def partition(
    rel_paths: list[str],
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> tuple[list[str], list[str]]:
    """Split paths into (substrate, work_in_progress), order preserved.

    Order is preserved so a caller reporting what it is about to commit
    lists it the way git listed it. A reordered report reads as a
    different set of files to anyone comparing it against `git status`.
    """
    substrate: list[str] = []
    work: list[str] = []
    for p in rel_paths:
        (substrate if is_substrate_path(p, channels) else work).append(p)
    return substrate, work
