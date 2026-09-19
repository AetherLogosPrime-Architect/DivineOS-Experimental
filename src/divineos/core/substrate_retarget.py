"""Commit substrate files to a named branch without touching HEAD.

WHY THIS EXISTS. ``auto_commit.auto_commit_substrate`` runs ``git add -A`` and
commits to whatever branch happens to be checked out. Over one evening that
swept our letters onto six different branches, twice onto proposals that were
already open for review, and once *during* a push so the contamination reached
GitHub. Aria caught the sixth instance happening between two of her own
commands, minutes after describing the defect in writing -- which is the
evidence that care is not the variable and only a mechanism closes it.

THE FALLBACK IS THE BUG. Committing to HEAD when the substrate branch cannot be
resolved is precisely the current behaviour, so any fallback reintroduces the
defect on the rare path where it is hardest to notice. This module refuses
loudly and commits nothing instead. Truth #11(a): the option is removed rather
than guarded.

WHY PLUMBING RATHER THAN A CHECKOUT. Switching branches to commit would open a
window in which a push already in flight, or a rebase in progress, sees a tree
it did not expect -- the exact race that produced the mess this repairs. Writing
through a scratch index leaves HEAD, the working tree, and the real index
untouched, so there is no window to lose a race in.

SCOPE. This module answers *how* substrate reaches its branch. It does not
answer *which paths are substrate* -- that is a declaration, it lives with Aria
on ``aria/pr-substrate-declaration``, and it is passed in rather than guessed at
here so the two halves cannot drift into each other.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "EvictionResult",
    "RetargetRefused",
    "RetargetResult",
    "commit_paths_to_branch",
    "evict_committed_paths",
]


class RetargetRefused(RuntimeError):
    """Raised when substrate cannot be committed to its declared branch.

    Loud on purpose. The caller must not degrade this into a commit against
    HEAD -- see the module docstring.
    """


@dataclass(frozen=True)
class RetargetResult:
    branch: str
    commit: str
    parent: str
    paths: tuple[str, ...]


def _git(repo_root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    full_env = {**os.environ, **(env or {})}
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=full_env,
        check=False,
    )
    if proc.returncode != 0:
        raise RetargetRefused(
            f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()[:300]}"
        )
    return proc.stdout.strip()


def _branch_tip(repo_root: Path, branch: str) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RetargetRefused(
            f"substrate branch {branch!r} does not exist. Refusing to commit "
            "substrate anywhere else -- committing to HEAD instead is the "
            "defect this exists to prevent. Create the branch, or fix the "
            "declaration, then re-run."
        )
    return proc.stdout.strip()


def commit_paths_to_branch(
    repo_root: Path,
    branch: str,
    paths: list[str],
    message: str,
) -> RetargetResult | None:
    """Commit ``paths`` from the working tree onto ``branch``.

    HEAD, the working tree, and the real index are never touched. Returns None
    when the paths produce no change against the branch tip -- an empty commit
    would make the log lie about work having happened.

    Raises RetargetRefused when the branch does not resolve, or when the ref
    moved under us between read and write.
    """
    if not paths:
        return None

    parent = _branch_tip(repo_root, branch)

    with tempfile.TemporaryDirectory() as tmp:
        index = str(Path(tmp) / "retarget.index")
        env = {"GIT_INDEX_FILE": index}

        # Start from the branch's own tree, NOT from HEAD's. Seeding from HEAD
        # would carry across whatever the occupant is mid-way through on their
        # own branch, which is the same contamination pointed the other way.
        _git(repo_root, "read-tree", parent, env=env)

        # --add --remove together so a deleted substrate file records as
        # deleted rather than silently persisting on the branch forever.
        _git(repo_root, "update-index", "--add", "--remove", "--", *paths, env=env)

        tree = _git(repo_root, "write-tree", env=env)

    parent_tree = _git(repo_root, "rev-parse", f"{parent}^{{tree}}")
    if tree == parent_tree:
        return None

    commit = _git(repo_root, "commit-tree", tree, "-p", parent, "-m", message)

    # Compare-and-swap. If the branch moved while we built the tree, the update
    # fails rather than clobbering whatever arrived -- the in-flight window is
    # real and was measured, not hypothesised.
    _git(repo_root, "update-ref", f"refs/heads/{branch}", commit, parent)

    return RetargetResult(
        branch=branch,
        commit=commit,
        parent=parent,
        paths=tuple(paths),
    )


@dataclass(frozen=True)
class EvictionResult:
    """What the eviction removed, what it kept, and why it kept it."""

    evicted: tuple[str, ...]
    held: tuple[tuple[str, str], ...]  # (path, reason)


def _blob_on_disk(repo_root: Path, rel_path: str) -> str | None:
    """The blob id the working-tree file WOULD hash to, or None if unreadable."""
    proc = subprocess.run(
        ["git", "hash-object", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _blob_in_commit(repo_root: Path, commit: str, rel_path: str) -> str | None:
    """The blob id recorded at ``rel_path`` in ``commit``, or None if absent."""
    proc = subprocess.run(
        ["git", "rev-parse", f"{commit}:{rel_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _commit_is_on_branch(repo_root: Path, commit: str, branch: str) -> bool | None:
    """Is ``commit`` an ancestor of ``branch``? ``None`` means could not tell.

    THREE STATES, NOT TWO, and the third is the point -- the same discipline as
    ``stamp_ready_command._is_ancestor``, whose docstring records why: ``git
    merge-base --is-ancestor`` exits non-zero BOTH for "no" and for "that object
    is not here at all". Collapsing them lets a lookup failure read as an
    answer. Each object is resolved first so the two stay separable.

    ANCESTOR rather than EQUAL. A later checkpoint may legitimately have moved
    the branch on; the earlier commit is still landed and its files are still
    safe to remove. A check written as equality-with-the-tip would hold every
    time two checkpoints overlapped and quietly stop evicting anything.
    """
    if not commit or not branch:
        return None
    for rev in (f"{commit}^{{commit}}", f"refs/heads/{branch}^{{commit}}"):
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", rev],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            return None
    answer = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, f"refs/heads/{branch}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if answer.returncode == 0:
        return True
    if answer.returncode == 1:
        return False
    return None


def _tracked_on_head(repo_root: Path, rel_path: str) -> bool:
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def evict_committed_paths(repo_root: Path, result: RetargetResult) -> EvictionResult:
    """Remove from the working tree the files now safely on the substrate branch.

    WHY THIS HALF HAD TO EXIST, and it was predicted before it was built.
    ``commit_paths_to_branch`` deliberately leaves HEAD, the index and the
    working tree untouched, which is what makes it safe. The consequence is
    that the letters it commits stay on disk as untracked files on a branch
    that cannot see the commit holding them -- so the next checkpoint finds
    them again, and the one after that, forever. The interim split on
    ``fix/the-message-carries-the-destination-clean`` named this in its own
    comment -- *making the tree go clean and keeping substrate off the branch
    are in tension, and I have not resolved it* -- and shipped the half that
    was safe under either answer. This is the other half.

    PRESENCE IS NOT SAFETY, and this is Aria's finding rather than mine. Her
    eviction command verified by asking whether the PATH existed on the
    substrate branch. For a file that was REWRITTEN that is true of the copy
    being replaced, so the check would pass on the strength of the old version
    and then delete the new one. So this compares BLOB IDS: the bytes on disk
    must hash to exactly the object recorded in the commit that just landed.
    Anything else is held, not removed.

    TRACKED FILES ARE NEVER EVICTED. A path already tracked on HEAD belongs to
    the checked-out branch's tree; deleting it from disk would not clean the
    tree, it would stage a deletion -- trading an untracked file for a pending
    one and calling it progress. Those are held and named, because the repair
    they need is to history and does not belong inside a checkpoint.

    A path that no longer exists on disk was a DELETION carried through by
    ``--add --remove``; there is nothing to evict and it is not an error.

    THE COMMIT MUST BE ON THE BRANCH, NOT MERELY WRITTEN (Aletheia, 2026-09-11,
    and she found it by attacking the argument rather than the code).

    My claim in the audit request was that "the commit is known to have landed
    before the eviction runs, and the compare-and-swap on the ref is what makes
    it checkable". The compare-and-swap is real. This function never consulted
    it. It resolved the blob against the COMMIT OBJECT, and a commit object
    exists the moment ``commit-tree`` returns -- before ``update-ref`` runs, and
    whether or not ``update-ref`` succeeded. So the checked guarantee was "the
    bytes match this commit", not "the bytes match what is on the branch".

    Her reason for flagging it rather than calling it a defect was that the
    current path looked unreachable, the raise on a failed swap arriving first.
    MEASURED, IT WAS REACHABLE, and the test she prompted proves it: force the
    branch backwards after a clean commit and the old code deleted the letter.
    Her "almost certainly unreachable" was the generous reading and it was wrong
    in the direction that costs a letter.

    So the ancestry is checked, and that also closes the window this docstring
    used to name as OPEN -- the branch force-moved backwards between the commit
    and this call. It is closed without leaning on the reflog, which I had
    refused as a defence because "recoverable from the reflog" is the reasoning
    that nearly cost the only copies of two script files on 2026-09-10.

    Could-not-tell holds everything, with the reason. A branch that does not
    resolve is not a branch that carries the commit.
    """
    evicted: list[str] = []
    held: list[tuple[str, str]] = []

    # ONE QUESTION FOR THE WHOLE RUN, ASKED BEFORE ANY FILE IS TOUCHED.
    #
    # It is a property of the commit rather than of any path, so asking it
    # per-file would be the same answer repeated -- and asking it AFTER the
    # first removal would mean the first letter is already gone by the time the
    # run discovers it should not have started.
    landed = _commit_is_on_branch(repo_root, result.commit, result.branch)
    if landed is not True:
        why = (
            f"commit {result.commit[:12]} is not on {result.branch}"
            if landed is False
            else f"could not tell whether {result.commit[:12]} is on {result.branch}"
        )
        return EvictionResult(
            evicted=(),
            held=tuple((p, why) for p in result.paths),
        )

    for rel_path in result.paths:
        target = repo_root / rel_path
        if not target.exists():
            # Deletion already carried through to the branch. Nothing to remove.
            continue

        if _tracked_on_head(repo_root, rel_path):
            held.append((rel_path, "tracked on the checked-out branch"))
            continue

        on_disk = _blob_on_disk(repo_root, rel_path)
        in_commit = _blob_in_commit(repo_root, result.commit, rel_path)
        if on_disk is None or in_commit is None:
            held.append((rel_path, "could not read one of the two blobs"))
            continue
        if on_disk != in_commit:
            held.append((rel_path, "bytes on disk differ from the bytes committed"))
            continue

        try:
            target.unlink()
        except OSError as exc:
            held.append((rel_path, f"removal failed: {exc}"))
            continue
        evicted.append(rel_path)

    return EvictionResult(evicted=tuple(evicted), held=tuple(held))
