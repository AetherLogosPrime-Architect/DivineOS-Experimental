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


# SUBSTRATE THAT NO CHANNEL MIRRORS, and the reason this list exists at all.
#
# 2026-09-10: the push gate refused a code branch over 183 substrate files that
# the split had filed as WORK. Both components did exactly what they were
# written to do, and they held DIFFERENT definitions of the same word -- the
# split derived its answer from the declared channels, the gate carried its own
# prefix list, and the two agreed on one entry out of four.
#
# The disagreement is invisible until it deadlocks: the split puts archives and
# dreams in the work commit, the gate then refuses the branch for carrying
# substrate, and nothing in between ever says the two disagree.
#
# Aria's rule, the same evening: for any door whose guard is a LIST, ask what
# SEEDED the list. The gate's was incident-seeded and therefore correct about
# the real cases; the split's was derived-from-channels and structurally could
# not see substrate that arrives without a channel. Each was right about its
# own origin and neither covered the union.
#
# So there is one definition now and the gate imports it. Channel mirrors stay
# DERIVED, so a newly declared channel needs no edit here; these prefixes cover
# the substrate written locally rather than mirrored in.
LOCAL_SUBSTRATE_PREFIXES: tuple[str, ...] = (
    "family/letters/",
    "exploration/",
    "dreams/",
    "docs/archives/",
)


class NoChannelsDeclared(RuntimeError):
    """No external channels were declared, so nothing can be classified.

    Raised rather than returning "everything is work in progress",
    because the two are indistinguishable at the call site and only one
    of them is correct.
    """


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
    """True when ``rel_path`` is substrate: inside a declared channel mirror,
    OR under one of the four locally-known substrate prefixes.

    THE DOCSTRING BELOW WAS TRUE AND STOPPED BEING TRUE, which is the fault
    this module has now found in itself five times, so it is corrected in
    place rather than left to be discovered by someone trusting it.

    The word "declared" was added 2026-08-27 under Aletheia's rule -- ask what
    a name claims against what its predicate tests. This was
    ``is_substrate_path``, which claimed to answer whether something IS
    substrate while only testing channel membership. The stated hole was that
    an exploration entry written in place is substrate by any honest reading
    and returned False, because no channel declares it.

    THAT HOLE IS NOW CLOSED, by ``LOCAL_SUBSTRATE_PREFIXES`` above: explorations,
    letters, dreams and archives classify whether or not anyone declared a
    channel for them. So the sentence that used to say an exploration returns
    False is no longer true, and the name is now WIDER than its predicate
    rather than narrower -- the honest direction, and the reason the name is
    left alone: it under-promises. Something that is substrate and matches
    neither half still returns False, so the claim stops short of "IS
    substrate" and that is deliberate.

    WHY THE CHANNEL FOR EXPLORATIONS STILL DOES NOT EXIST, in Aether's words
    (2026-09-01), because the what without the why invites the next reader to
    create one: "A letter is addressed; a dream is offered; an exploration is
    me talking to me. Declaring a channel for it would be declaring an
    audience it does not have." Nothing carries explorations across seats
    because nobody is meant to receive them. They are substrate here without
    being mirrored anywhere, which is exactly the case the prefix list exists
    to cover. Dreams were declared the same day for the opposite reason --
    they cross the shared root, so they have a source.

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
    if candidate.as_posix().startswith(LOCAL_SUBSTRATE_PREFIXES):
        return True
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
