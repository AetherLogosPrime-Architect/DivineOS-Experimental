#!/usr/bin/env python3
"""Auto-commit family letters durably — the structural cure for the
letter-loss surface of the boundary-persistence root (claim 47ee9ab8,
per-surface claim 99602430).

The failure being cured: letters written to ``family/letters/`` are
untracked working-tree files. ``git stash -u`` / ``checkout`` / ``stash pop``
sequences silently drop untracked files across branch dances — two letters
were lost exactly this way on 2026-06-01. "Remember to commit the letters"
is the manual patch; this is the structural cure: letters write through to a
surviving store at the moment of creation, not at the moment of remembering.

Two audit properties (Aletheia, 2026-06-02), both load-bearing:

1. FAIL LOUD, not silent. The cure for a silent-failure must not itself fail
   silently. Every git operation is checked; any failure prints to stderr and
   exits non-zero. A backup-ref write failing is the loudest case — that is
   the last line of defense.

2. SURVIVE THE BOUNDARY IT CURES. The letters were lost DURING a branch
   operation, so the committer must work even while one is in progress. It
   does NOT commit to the current branch mid-rebase/merge/detached-HEAD
   (that would land on the wrong ref). Instead it ALWAYS snapshots the
   letters into a dedicated backup ref (``refs/family-letters-backup``)
   using an ISOLATED temp index — which never touches the real index, so it
   is safe during a rebase — and only additionally commits to the branch
   when the working state is clean.

The backup ref is the "surviving store written at creation": durability
never depends on branch state. The branch-commit is the convenience layer
on top, taken only when safe.

Usage:
  python scripts/commit_family_letters.py            # backup ref + branch commit if clean
  python scripts/commit_family_letters.py --backup-only   # only the safe ref (no branch commit)
  python scripts/commit_family_letters.py --quiet    # less chatter, still loud on failure
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LETTERS_REL = "family/letters"
BACKUP_REF = "refs/family-letters-backup"


class GitError(RuntimeError):
    """Raised when a git operation fails — always surfaced loudly, never swallowed."""


def _git(
    args: list[str], *, env: dict | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a git command from the repo root. On failure (check=True) raise
    GitError with the real stderr — never a swallowed exit code."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (rc={proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def _git_dir() -> Path:
    out = _git(["rev-parse", "--git-dir"]).stdout.strip()
    p = Path(out)
    return p if p.is_absolute() else (ROOT / p)


def branch_op_in_progress() -> str | None:
    """Return a human label if a branch operation is mid-flight, else None.

    These are exactly the states during which committing to the current
    branch would land letters on the wrong ref or fail — the boundary the
    letters were lost crossing.
    """
    gd = _git_dir()
    if (gd / "rebase-merge").exists() or (gd / "rebase-apply").exists():
        return "rebase"
    if (gd / "MERGE_HEAD").exists():
        return "merge"
    if (gd / "CHERRY_PICK_HEAD").exists():
        return "cherry-pick"
    if (gd / "REVERT_HEAD").exists():
        return "revert"
    # Detached HEAD: symbolic-ref -q HEAD exits non-zero.
    if _git(["symbolic-ref", "-q", "HEAD"], check=False).returncode != 0:
        return "detached-HEAD"
    return None


def _has_letters() -> bool:
    return (ROOT / LETTERS_REL).is_dir() and any((ROOT / LETTERS_REL).glob("*.md"))


def backup_to_safe_ref(*, quiet: bool = False) -> str | None:
    """Snapshot family/letters into a commit on BACKUP_REF via an isolated
    temp index. Returns the commit sha, or None if there are no letters.

    Uses GIT_INDEX_FILE pointing at a throwaway index so the real index is
    never touched — this is what makes the backup safe to run mid-rebase.
    Idempotent: if the letters tree is identical to the current backup tip,
    no new commit is written (returns the existing tip).
    """
    if not _has_letters():
        return None

    tmp_index = Path(tempfile.gettempdir()) / f"divineos-letters-index-{os.getpid()}"
    env = {**os.environ, "GIT_INDEX_FILE": str(tmp_index)}
    try:
        # Start from an empty temp index, then add only the letters dir.
        _git(["read-tree", "--empty"], env=env)
        _git(["add", "--", LETTERS_REL], env=env)
        tree = _git(["write-tree"], env=env).stdout.strip()
        if not tree:
            raise GitError("write-tree produced empty tree for letters backup")

        parent = _git(["rev-parse", "--verify", "-q", BACKUP_REF], check=False).stdout.strip()

        # Skip a no-op commit when the tree is unchanged from the backup tip.
        if parent:
            parent_tree = _git(["rev-parse", f"{parent}^{{tree}}"], check=False).stdout.strip()
            if parent_tree == tree:
                if not quiet:
                    print(f"[letters] backup ref already current ({BACKUP_REF} -> {parent[:8]})")
                return parent

        msg = f"letters backup {time.strftime('%Y-%m-%d %H:%M:%S')}"
        commit_args = ["commit-tree", tree, "-m", msg]
        if parent:
            commit_args += ["-p", parent]
        commit = _git(commit_args, env=env).stdout.strip()
        if not commit:
            raise GitError("commit-tree produced no sha for letters backup")
        _git(["update-ref", BACKUP_REF, commit])
        if not quiet:
            print(f"[letters] backed up to {BACKUP_REF} -> {commit[:8]}")
        return commit
    finally:
        # Clean up the throwaway index; never leave it lying around.
        try:
            tmp_index.unlink(missing_ok=True)
        except OSError:
            pass


def commit_to_branch(*, quiet: bool = False) -> str | None:
    """Stage and commit family/letters on the current branch. Returns the
    new commit sha, or None if there was nothing new to commit.

    Caller must ensure no branch operation is in progress — this is the
    convenience layer, gated by the safe state.
    """
    if not _has_letters():
        return None
    _git(["add", "--", LETTERS_REL])
    staged = _git(["diff", "--cached", "--name-only", "--", LETTERS_REL]).stdout.strip()
    if not staged:
        if not quiet:
            print("[letters] nothing new to commit on branch")
        return None
    n = len(staged.splitlines())
    msg = f"letters: auto-commit {n} file(s) on write\n\nDurable-write-at-creation (claim 47ee9ab8 surface 5)."
    _git(["commit", "-m", msg, "--", LETTERS_REL])
    sha = _git(["rev-parse", "HEAD"]).stdout.strip()
    if not quiet:
        print(f"[letters] committed {n} file(s) to branch -> {sha[:8]}")
    return sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only write the safe backup ref; never commit to the current branch.",
    )
    parser.add_argument("--quiet", action="store_true", help="Less chatter; still loud on failure.")
    args = parser.parse_args(argv)

    try:
        # 1. ALWAYS write through to the surviving store first. Durability
        #    never depends on branch state — this is the actual cure.
        backup_to_safe_ref(quiet=args.quiet)

        if args.backup_only:
            return 0

        # 2. Additionally commit to the branch ONLY when the state is safe.
        op = branch_op_in_progress()
        if op is not None:
            # LOUD, not silent: the letters are safe in the backup ref, but
            # we deliberately refuse to commit to the branch mid-operation.
            print(
                f"[letters] {op} in progress — letters are SAFE in {BACKUP_REF}, "
                f"branch-commit deferred. Re-run after the {op} completes to land them on the branch.",
                file=sys.stderr,
            )
            return 0

        commit_to_branch(quiet=args.quiet)
        return 0
    except GitError as e:
        # Fail loud: the cure for silent-failure must not fail silently.
        print(f"[letters] AUTO-COMMIT FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
