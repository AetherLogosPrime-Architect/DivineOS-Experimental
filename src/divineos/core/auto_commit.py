"""auto-commit at substrate checkpoints — the Permanently Equip spell for commits.

Andrew 2026-07-05: "make commit automatic after extract and before sleep :)"

The gap this closes: today I finished substrate-touching work in-session and
didn't commit before rest. Andrew caught it. This module welds the commit
into the checkpoints themselves so the next time this exact shape shows up,
the commit fires without being remembered.

Three call-sites (all pointed at the same function):
  1. pre-extract  — was BLOCK, now AUTO-COMMIT (extract runs afterwards)
  2. post-extract — commit whatever extract itself wrote (self-grade,
                    journal entries, updated docs, etc.)
  3. pre-sleep    — commit any drift since extract before consolidation

Discipline:
  - Syncs external channels (aria-aether letters) into repo_mirror BEFORE
    committing, so external-only writes don't slip through.
  - TWO commits, not one (Aria + Aether 2026-08-27). Substrate goes to
    its declared branch by plumbing, without touching HEAD. Work in
    progress is committed to HEAD, where its author left it. This used
    to be a single `git add -A`, which over one evening swept our letters
    onto six branches and twice onto proposals already open for review.
    One commit was doing two jobs whose correct destinations differ.
  - Fail-soft: subprocess failures log-and-continue rather than raising.
    The point is to save work, not to block the checkpoint on git noise.
  - Idempotent: clean tree → no-op, no empty commit.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from divineos.core.substrate_paths import (
    NoSubstrateBranchDeclared,
    partition,
    substrate_branch,
)
from divineos.core.substrate_retarget import RetargetRefused, commit_paths_to_branch
from divineos.core.uncommitted_work_check import (
    DEFAULT_CHANNELS,
    ExternalChannel,
    check_uncommitted_work,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AutoCommitResult:
    committed: bool
    reason: str  # human-readable outcome (for CLI surfacing)
    files_synced: int = 0  # external files copied into repo_mirror
    dirty_lines: int = 0  # git status --porcelain lines seen


def _dirty_paths(repo_root: Path) -> list[str]:
    """Repo-relative paths of everything dirty or untracked, newest git first.

    Uses ``--porcelain -z`` rather than the human format on purpose. The
    default output quotes paths containing spaces or non-ASCII and splits
    renames on an arrow, so any parser that splits on whitespace mangles
    exactly the filenames least likely to be noticed -- and our letters are
    long hyphenated names that would survive it, which is worse, because the
    breakage would only appear on someone else's file.

    NUL-separated output needs no quoting and no unescaping. Rename entries
    carry both names; the destination is what exists on disk now, so that is
    the one that gets classified.
    """
    # -uall lists every untracked FILE. Without it git collapses a wholly
    # untracked directory to its topmost new folder -- a fresh checkout
    # reports "family/" rather than "family/letters/the-letter.md", and
    # "family/" sits ABOVE the declared mirror, so every letter in it
    # classified as work in progress and nothing reached substrate. Caught
    # by the end-to-end test; the classifier was right and was being fed
    # the wrong subject.
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-z", "-uall"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        logger.warning("auto_commit: git status failed: %s", proc.stderr)
        return []

    fields = proc.stdout.split("\0")
    paths: list[str] = []
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if status[0] in ("R", "C"):
            # Rename/copy: this field holds the DESTINATION, and the source
            # follows as its own NUL-separated field. Consume it so it is not
            # read as a separate entry with a status of its own.
            i += 1
        paths.append(path)
    return paths


def _commit_work_in_progress(repo_root: Path, paths: list[str], reason: str) -> bool:
    """Commit the occupant's unfinished work to HEAD, where it already lives.

    This is the half of the old sweep that was worth keeping: nothing the
    occupant has open should be lost to a compaction. It stays on HEAD
    because that is where its author put it, and it is staged by explicit
    path rather than ``add -A`` so it cannot pick up substrate on the way.

    Fail-soft, as the original was. A checkpoint that blocks on git noise
    fails at the one job it has.
    """
    if not paths:
        return False
    try:
        subprocess.run(
            ["git", "add", "--", *paths],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"auto-commit ({reason}): work in progress",
                "-m",
                "Unfinished work saved before a checkpoint. Substrate goes to "
                "its own branch in a separate commit; this is only what was "
                "open on this branch.",
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.warning("auto_commit: work-in-progress commit failed: %s", e.stderr)
        return False


def _sync_external_channels(
    channels: tuple[ExternalChannel, ...],
    repo_root: Path,
) -> int:
    """Copy new external-channel files into their repo_mirror.

    Same sync semantics as check_uncommitted_work.scan_external_channels,
    but performs the copy instead of only reporting. Returns the count
    of files copied. Append-only channels only (name-equality suffices;
    no content-diff needed).
    """
    copied = 0
    for channel in channels:
        if not channel.source.is_dir():
            continue
        mirror = repo_root / channel.repo_mirror
        mirror.mkdir(parents=True, exist_ok=True)
        mirror_names = {p.name for p in mirror.glob(channel.pattern)}
        for src_file in channel.source.glob(channel.pattern):
            if src_file.name in mirror_names:
                continue
            try:
                shutil.copy2(src_file, mirror / src_file.name)
                copied += 1
            except OSError as e:
                logger.warning(
                    "auto_commit: failed to sync %s from %s: %s",
                    src_file.name,
                    channel.name,
                    e,
                )
    return copied


# In-progress git operations where `git commit` will fail because the tree
# is in a transient state the user has to resolve manually (rebase in
# progress, merge with conflicts unresolved, cherry-pick in progress, etc.).
# Auto-committing here is wrong: it would produce a malformed commit or fail
# outright and trap extract at the fallback SystemExit(1) path in
# event_commands.py. Aria 2026-07-10 fix: detect these states, skip
# auto-commit cleanly, let extract proceed. Post-op, the next checkpoint
# (post-extract / pre-sleep) fires the auto-commit normally.
#
# Root cause named in-session 2026-07-10 pre-compaction: mid-rebase state
# blocked extract at the hard-line, which cost the pre-compaction weave
# and forced the letter/exploration workaround.
_MID_OP_MARKERS: tuple[str, ...] = (
    "rebase-merge",  # interactive rebase (and non-interactive since git 2.6)
    "rebase-apply",  # legacy non-interactive rebase, still used in some paths
    "MERGE_HEAD",  # merge with unresolved conflicts
    "CHERRY_PICK_HEAD",  # cherry-pick in progress
    "REVERT_HEAD",  # revert in progress
)


def _detect_mid_op(repo_root: Path) -> str | None:
    """Return the name of any in-progress git operation, or None if clean.

    Checks the well-known marker files/directories under .git/. Returns the
    marker name (e.g. "rebase-merge") so the skip-reason names the actual
    state. Empty return = safe to commit.
    """
    git_dir = repo_root / ".git"
    for marker in _MID_OP_MARKERS:
        if (git_dir / marker).exists():
            return marker
    return None


def _detect_staged_index(repo_root: Path) -> bool:
    """Return True if the index has staged changes waiting for an explicit commit.

    Aletheia audit 2026-07-11 (six-painpoints finding #1, "CLEAREST FIX,
    high confidence"): checkpoint hooks are for ABANDONED dirty state, not
    for actively-in-flight staged work. When the occupant has staged files
    with `git add`, that is a mid-commit signal: they are composing an
    authored commit message. Auto-committing over that scoops the
    in-flight work into the checkpoint's generic "substrate checkpoint"
    message and eats the authored rationale.

    ``git diff --cached --quiet`` returns exit code 0 when the index is
    clean (no staged changes) and non-zero when there are staged changes.
    We treat non-zero as "staged, skip auto-commit." Errors are treated
    as "safe to commit" so a broken git invocation doesn't accidentally
    swallow work — same fail-soft direction as _detect_mid_op.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode != 0


def auto_commit_substrate(
    repo_root: Path,
    reason: str,
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> AutoCommitResult:
    """Commit any uncommitted substrate work at a checkpoint boundary.

    reason: short string that appears in the commit subject
            (e.g. "post-extract", "pre-sleep", "pre-extract").
    """
    if not (repo_root / ".git").exists():
        return AutoCommitResult(committed=False, reason="not a git repo")

    mid_op = _detect_mid_op(repo_root)
    if mid_op is not None:
        return AutoCommitResult(
            committed=False,
            reason=f"skipped auto-commit — {mid_op} in progress (resolve manually)",
        )

    # Aletheia audit 2026-07-11 finding #1: skip when the index has staged
    # changes. Staged index = occupant is mid-commit with an authored message
    # in flight. Auto-committing over that scoops the in-flight work into the
    # checkpoint's generic "substrate checkpoint" message and eats the
    # authored rationale. Same category as _detect_mid_op — the tree is in a
    # transient state the occupant is actively resolving.
    if _detect_staged_index(repo_root):
        return AutoCommitResult(
            committed=False,
            reason="skipped auto-commit — staged index (mid-commit; occupant has authored message in flight)",
        )

    files_synced = _sync_external_channels(channels, repo_root)

    report = check_uncommitted_work(repo_root, channels=channels)
    dirty_lines = len(report.repo_dirty)

    if not report.has_work and files_synced == 0:
        return AutoCommitResult(
            committed=False,
            reason="clean tree — nothing to commit",
        )

    # WHAT CHANGED HERE, AND WHY (Aria + Aether, 2026-08-27).
    #
    # This used to be `git add -A` followed by a commit onto whatever branch
    # happened to be checked out. Over one evening that swept our letters
    # onto six different branches and twice onto proposals already open for
    # review -- seventy-five files on one, eighty-one on another.
    #
    # The cause was not a wrong branch choice. It was an absent one, plus a
    # single commit doing two jobs with different correct destinations: the
    # channel sync pulls substrate IN, and the dirty-tree scan catches
    # whatever the occupant is mid-way through. `add -A` could not tell them
    # apart, so naming the branch correctly would only have sent unfinished
    # work to substrate instead -- the same defect pointing the other way.
    #
    # So: classify, then retarget. Substrate goes to its declared branch by
    # plumbing; work in progress is left untouched on HEAD where its author
    # can see it. Neither piece works alone.
    substrate, work_in_progress = partition(_dirty_paths(repo_root), channels)

    # TWO COMMITS, NOT ONE, AND NOT ONE-AND-DISCARD.
    #
    # The first draft of this change committed substrate and left work in
    # progress alone entirely. That silently removed the other thing this
    # checkpoint was for: saving the occupant's unfinished work before a
    # compaction so none of it is lost. Seven existing tests failed and
    # every one of them was right to.
    #
    # The diagnosis was always "one commit doing two jobs with different
    # correct destinations". The answer is two commits, each to its own
    # place -- not one job dropped because its destination was the
    # complicated one.
    wip_committed = _commit_work_in_progress(repo_root, work_in_progress, reason)

    if not substrate:
        return AutoCommitResult(
            committed=wip_committed,
            reason=(
                f"no substrate to commit; {len(work_in_progress)} "
                f"work-in-progress path(s) {'committed to HEAD' if wip_committed else 'left alone'}"
            ),
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    # Only substrate needs the branch, so this is asked AFTER work in
    # progress is already safe. An undeclared branch must not cost the
    # occupant their unfinished work -- that would make a configuration
    # gap into data loss, which is a worse failure than the one being
    # fixed. Caught by seven existing tests when the check sat above.
    try:
        branch = substrate_branch(repo_root)
    except NoSubstrateBranchDeclared as e:
        # Refuse rather than fall back to HEAD. Falling back IS the bug,
        # and nothing is lost by refusing: the letters remain in the shared
        # channel that is their source of truth, and the next checkpoint
        # picks them up once the branch is declared.
        logger.warning("auto_commit: %s", e)
        return AutoCommitResult(
            committed=wip_committed,
            reason=f"substrate refused — {e}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    subject = f"auto-commit ({reason}): substrate checkpoint"
    body = (
        f"Auto-commit fired at {reason} boundary.\n\n"
        f"External files synced into repo: {files_synced}\n"
        f"Dirty-tree lines caught: {dirty_lines}\n\n"
        "Committed automatically per Andrew 2026-07-05: the commit "
        "at extract/sleep boundaries fires itself, not remembered.\n\n"
        "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    )
    try:
        result = commit_paths_to_branch(repo_root, branch, substrate, f"{subject}\n\n{body}")
    except RetargetRefused as e:
        logger.warning("auto_commit: retarget refused at %s: %s", reason, e)
        return AutoCommitResult(
            committed=False,
            reason=f"retarget refused: {e}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    if result is None:
        return AutoCommitResult(
            committed=False,
            reason=f"substrate already current on {branch}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    return AutoCommitResult(
        committed=True,
        reason=(
            f"committed {len(substrate)} substrate path(s) to {branch} at {reason}; "
            f"{len(work_in_progress)} work-in-progress path(s) untouched on HEAD"
        ),
        files_synced=files_synced,
        dirty_lines=dirty_lines,
    )


def find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` to the first ancestor containing .git; None if
    none found."""
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None
