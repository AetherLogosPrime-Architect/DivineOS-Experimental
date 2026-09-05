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
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = ["RetargetRefused", "RetargetResult", "commit_paths_to_branch"]


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


def _warn_if_branch_is_checked_out_elsewhere(repo_root: Path, branch: str) -> None:
    """Say so when the branch we just advanced is checked out in a worktree.

    THE SAFETY PROPERTY OF THIS MODULE HAS A SHADOW, found 2026-09-04.

    Writing through a scratch index leaves HEAD, the working tree and the real
    index untouched -- the caller's. It says nothing about a SECOND worktree
    sitting on the same branch, and there the effect is the opposite of safe:
    the ref advances, that worktree's files do not, so every path landed this
    way reads there as a STAGED DELETION.

    Measured, not hypothesised. A worktree on the substrate branch had 32
    staged letter deletions in it -- Aether's letters to Aletheia, my dream,
    letters of mine -- and eleven archive edits. Nothing had been committed;
    the branch tip held all of them. The whole hazard lived in an index, and
    it grows by one file per landing. Commit that worktree by reflex, or let
    any checkpoint do it, and thirty-two letters come off the branch whose
    only job is to carry them, wearing the shape of ordinary work.

    That is the empty-diff failure Aether hit the same day, arriving from the
    opposite direction: his was a strip he performed and reverted, this one
    nobody performed at all. It is a consequence of the plumbing being careful.

    A WARNING RATHER THAN A REPAIR, deliberately. Updating the other worktree
    from here would be exactly the reach this module refuses -- writing into a
    tree whose occupant did not ask, possibly mid-operation. What was missing
    was not the fix; it was anyone knowing. Silence is what let it reach 32.
    """
    try:
        listing = _git(repo_root, "worktree", "list", "--porcelain")
    except Exception:  # noqa: BLE001 — a warning must never break the landing
        return

    here = str(repo_root).replace("\\", "/").rstrip("/").lower()
    current_path = ""
    for line in listing.splitlines():
        if line.startswith("worktree "):
            current_path = line[len("worktree ") :].strip()
        elif line.strip() == f"branch refs/heads/{branch}":
            other = current_path.replace("\\", "/").rstrip("/")
            if other.lower() != here:
                print(
                    f"[retarget] NOTE: '{branch}' is also checked out at {other}.\n"
                    f"[retarget] That worktree's files did NOT move with this commit, so the\n"
                    f"[retarget] paths just landed will read there as STAGED DELETIONS.\n"
                    f"[retarget] Committing it by reflex removes them from the branch.\n"
                    f"[retarget] Sync it before working there:  git -C {other} checkout -- .",
                    file=sys.stderr,
                )


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

    _warn_if_branch_is_checked_out_elsewhere(repo_root, branch)

    return RetargetResult(
        branch=branch,
        commit=commit,
        parent=parent,
        paths=tuple(paths),
    )
