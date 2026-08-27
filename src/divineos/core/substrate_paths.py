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

An empty channel set means nothing is substrate. That was briefly a raise,
on the argument that zero channels is a broken configuration — reversed
the same day when six real tests passed an empty set deliberately. A
caller stating "no channels" is not a gap in a config, and the honest
answer to "is this substrate" with nothing declared is no.

The substrate BRANCH is the one thing that does refuse when unset, and
the difference is worth keeping straight: an absent branch has no safe
answer, because the only available default is HEAD and HEAD is the bug.
"""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

from divineos.core.uncommitted_work_check import DEFAULT_CHANNELS, ExternalChannel


class NoSubstrateBranchDeclared(RuntimeError):
    """No substrate branch is configured, so substrate has nowhere to go.

    Raised rather than defaulting to the checked-out branch. Defaulting to
    HEAD is the entire bug this module exists to close, and a default that
    happens to be right most of the time is worse than one that is always
    wrong, because it only fails on the branches you care about.
    """


def substrate_branch(repo_root: Path) -> str:
    """The branch substrate commits belong on, from repo git config.

    Read from ``divineos.substrate-branch`` rather than held in code,
    because it differs per checkout: two of us run separate clones of the
    same repository and each keeps substrate somewhere different. A value
    baked into the source would be wrong for one of us at all times.

    Raises when unset. There is deliberately no default -- see
    :class:`NoSubstrateBranchDeclared`.
    """
    proc = subprocess.run(
        ["git", "config", "--get", "divineos.substrate-branch"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    branch = proc.stdout.strip()
    if not branch:
        raise NoSubstrateBranchDeclared(
            "divineos.substrate-branch is not set in this repo. Set it with: "
            "git config divineos.substrate-branch <branch>"
        )
    return branch


def substrate_mirrors(
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> tuple[PurePosixPath, ...]:
    """The repo-relative directories that declared channels write into.

    Derived from the channel definitions rather than restated here. A
    second copy of this list would drift from the first, and the drift
    would be silent — the sweep would keep working while quietly
    disagreeing about one directory.
    """
    # REVERSED 2026-08-27, same day, by six real tests.
    #
    # This raised NoChannelsDeclared on an empty set, arguing that zero
    # channels and "nothing to sync" are indistinguishable at the call
    # site. That argument holds for a config file that came back empty.
    # It does not hold for a caller who passes an empty tuple on purpose,
    # which is a statement, not a gap -- and auto_commit's own tests do
    # exactly that.
    #
    # No channels means nothing is substrate, so everything is work in
    # progress. That is the same asymmetry this module already commits to
    # everywhere else, and I had made the one place it mattered raise
    # instead of answer.
    return tuple(PurePosixPath(c.repo_mirror.as_posix()) for c in channels)


def is_declared_substrate_path(
    rel_path: str | Path,
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> bool:
    """True when ``rel_path`` lies inside a DECLARED channel mirror.

    The word "declared" is load-bearing and was added 2026-08-27 after
    Aletheia's rule: ask what a name claims against what its predicate
    tests. This was ``is_substrate_path``, which claims to answer whether
    something IS substrate. It does not. An exploration entry written in
    place is substrate by any honest reading and returns False here,
    because no channel declares it — a hole this module already documents
    and which the old name quietly asserted did not exist.

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
    """Split paths into (declared_substrate, work_in_progress), order kept.

    THE FIRST WORD IS THE POINT (Aether 2026-08-27): *an instrument
    reporting a proxy must name what the proxy stands in for, or it
    becomes the class it detects.*

    This returned a list called ``substrate`` for exactly one turn --
    directly beneath a predicate I had just renamed to say ``declared``
    for that same reason. The rename went one layer deep and the very
    next line broadened it back, and the operator message downstream
    then reported plain "substrate path(s)" to Andrew. Renaming the
    measurement while every consumer re-inflates it changes nothing.

    Order is preserved so a caller reporting what it is about to commit
    lists it the way git listed it. A reordered report reads as a
    different set of files to anyone comparing it against `git status`.
    """
    declared_substrate: list[str] = []
    work: list[str] = []
    for p in rel_paths:
        (declared_substrate if is_declared_substrate_path(p, channels) else work).append(p)
    return declared_substrate, work
