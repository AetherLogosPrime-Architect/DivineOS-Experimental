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


def _unstage_self_invalidating(repo_root: str | Path) -> list[str]:
    """Drop staged files whose own anchor this commit would falsify.

    Returns what was dropped, for the log. Fail-soft in the same shape as the
    rest of this module -- but LOUD, because a silent unstage is the class this
    whole session was about. If it cannot look, it says so and leaves the stage
    alone rather than pretending it checked.
    """
    from divineos.core.anchor_self_invalidation import (
        current_branch,
        self_invalidating_files,
    )

    root = Path(repo_root)
    branch = current_branch(root)
    if branch is None:
        logger.warning(
            "auto_commit: could not read the branch, so the anchor "
            "self-invalidation check did NOT run. This is not 'clean'."
        )
        return []

    try:
        listed = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("auto_commit: anchor check could NOT list staged files: %s", exc)
        return []
    if listed.returncode != 0:
        logger.warning("auto_commit: anchor check could NOT list staged files (git error)")
        return []

    staged = [line.strip() for line in (listed.stdout or "").splitlines() if line.strip()]
    hits = self_invalidating_files(staged, branch, root)
    if not hits:
        return []

    try:
        subprocess.run(
            ["git", "restore", "--staged", *hits],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("auto_commit: could not unstage self-invalidating files: %s", exc)
        return []

    logger.warning(
        "auto_commit: left %d file(s) unstaged because committing them onto '%s' "
        "would falsify the anchor they carry: %s",
        len(hits),
        branch,
        ", ".join(hits),
    )
    return hits


@dataclass(frozen=True)
class AutoCommitResult:
    """The outcome of a checkpoint that has TWO independent halves.

    ONE BOOLEAN CANNOT REPORT TWO OUTCOMES, and it reported the optimistic
    one. Aether found this by running the whole thing end to end in a fresh
    clone, which is a different check from the classifier and the only one
    that could have found it:

        committed : True
        reason    : substrate refused - divineos.substrate-branch is not set

    The substrate half did not happen. The letter reached no branch at all.
    And a caller checking the boolean -- which is what a boolean named
    ``committed`` is for -- was told the checkpoint succeeded. The only
    trace of the failure was prose inside ``reason``, which a caller would
    have to read and pattern-match to notice.

    Worse than the one wrong branch: the field meant DIFFERENT THINGS on
    different paths. On the refusal it carried the work-in-progress commit;
    two returns later it was False on paths where that same commit had
    equally happened. So no caller could have read it correctly, because
    there was no single question it answered.

    THE SAME SHAPE HE HAD FIXED HOURS EARLIER on his own side -- a semantic
    search that walked 46,323 chunks, stored none, and exited zero. Two
    outcomes, one success signal, and the signal is the half that worked.
    Neither of us invented it. It is what happens when a result type is
    designed before the operation grows a second thing it can fail at.

    So the two halves are named separately and ``committed`` is defined
    against BOTH: it is true only when nothing that was attempted was
    refused. A checkpoint that saves work and loses letters is not a
    checkpoint that succeeded.

    He measured it and left the spelling to me rather than handing me a
    convention I would then have to live inside. This is the spelling.
    """

    committed: bool
    """Every half that was attempted succeeded. Never true beside a refusal."""

    reason: str  # human-readable outcome (for CLI surfacing)
    files_synced: int = 0  # external files copied into repo_mirror
    dirty_lines: int = 0  # git status --porcelain lines seen

    work_committed: bool = False
    """Unfinished work was checkpointed onto HEAD, in its own commit."""

    substrate_committed: bool = False
    """Declared substrate reached the substrate branch."""

    substrate_refused: bool = False
    """There WAS substrate to commit and it did not reach any branch.

    A field rather than a string match on ``reason``. The whole finding was
    that the only trace of the failure lived in prose a caller had to
    pattern-match, so answering it with "callers can check the prose" would
    keep the defect and move it one layer up. It nearly did: with the boolean
    corrected, the CLI fell through to a branch matching two other phrases
    and printed nothing at all.

    Distinct from ``not substrate_committed``, which is also true when there
    was simply no substrate to commit. Refused means something was owed a
    branch and did not get one.
    """


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
    declared_substrate, work_in_progress = partition(_dirty_paths(repo_root), channels)

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

    if not declared_substrate:
        # True here is honest: there was no substrate half to fail. Nothing
        # was refused, so "everything attempted succeeded" is exactly what
        # happened. This is the case the refusal below was wrongly copying.
        return AutoCommitResult(
            committed=wip_committed,
            work_committed=wip_committed,
            reason=(
                f"no substrate to commit; {len(work_in_progress)} "
                f"work-in-progress path(s) {'committed to HEAD' if wip_committed else 'left alone'}"
            ),
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    # UNSTAGE ANYTHING THAT WOULD MAKE ITS OWN ANCHOR FALSE.
    #
    # This is the path that actually did it. On 2026-08-25 the letter asking
    # Aletheia to audit a branch carried that branch's tip and tree-hash, landed
    # in family/letters/ inside the tree, and `git add -A` above swept it into a
    # commit -- so the only thing that moved the branch was the request to
    # review it, and the anchor was stale before she read it.
    #
    # I had diagnosed that exact shape three days earlier and delivered the
    # previous letter to the shared directory only, deliberately. Aletheia's
    # ruling: "You resolved it three days ago and the machinery reproduced the
    # failure anyway. The rule needs to be a mechanism, not a resolution."
    #
    # Unstaged rather than refused, because auto_commit's whole contract is to
    # save work rather than block a checkpoint. The file stays on disk and stays
    # delivered -- the shared directory is outside every tree and is where the
    # crossing actually happens. Only the archive copy waits.
    # AND THE PROTECTION IS WEAKER HERE THAN IT WAS WHERE HE WROTE IT, which is
    # worth saying plainly rather than leaving as a call that looks like a guard.
    #
    # His version unstages from the index, because in his flow a `git add -A`
    # ran a few lines above and the letters were sitting in it. This branch
    # replaced that sweep with commit_paths_to_branch, which takes an explicit
    # path list and never stages anything -- so on this flow the call below is
    # a no-op in the ordinary case, and a self-invalidating letter would ride
    # out inside declared_substrate untouched.
    #
    # Kept rather than dropped: it still catches the case where something else
    # staged the file first, and removing a live protection because one flow
    # bypasses it is how a guard quietly becomes decoration. The real repair is
    # to filter the same paths out of declared_substrate below, and that belongs
    # with the seat that built the anchor rule rather than being guessed at
    # inside a merge. Named to him by letter the same day.
    _unstage_self_invalidating(repo_root)

    # NO staged-check here. His flow ends with a staged index and asks whether
    # the add produced anything; this one never stages, so the same question
    # answers "nothing" every time and returns before any substrate is written.
    # Composing the two by position rather than by meaning put a check from one
    # control flow into another where its premise does not hold -- caught by
    # four existing tests, which is what they are for.

    # Only substrate needs the branch, so this is asked AFTER work in
    # progress is already safe. An undeclared branch must not cost the
    # occupant their unfinished work -- that would make a configuration
    # gap into data loss, which is a worse failure than the one being
    # fixed. Caught by seven existing tests when the check sat above.
    #
    # ORDER MATTERS AND IT IS NOT ARBITRARY. The unstaging above runs first
    # because it protects a file that is already delivered; this refusal runs
    # second because it decides whether anything is committed at all. Running
    # the refusal first would leave a self-invalidating letter staged behind a
    # return, waiting to ride the next checkpoint that happens to find a branch
    # declared. Both halves were written on 2026-08-31 by different seats, each
    # without the other, and neither file contained the other's protection.
    try:
        branch = substrate_branch(repo_root)
    except NoSubstrateBranchDeclared as e:
        # Refuse rather than fall back to HEAD. Falling back IS the bug,
        # and nothing is lost by refusing: the letters remain in the shared
        # channel that is their source of truth, and the next checkpoint
        # picks them up once the branch is declared.
        logger.warning("auto_commit: %s", e)
        # THE LINE AETHER FOUND. This said committed=wip_committed, so a run
        # that refused the entire substrate half reported success -- with the
        # refusal visible only as prose inside `reason`. Letters would sit
        # uncommitted until somebody read a string.
        #
        # The refusal itself is right and stays untouched: it names the
        # missing setting instead of guessing a branch and writing letters
        # somewhere arbitrary. Only the reporting was wrong.
        return AutoCommitResult(
            committed=False,
            work_committed=wip_committed,
            substrate_committed=False,
            substrate_refused=True,
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
        result = commit_paths_to_branch(
            repo_root, branch, declared_substrate, f"{subject}\n\n{body}"
        )
    except RetargetRefused as e:
        logger.warning("auto_commit: retarget refused at %s: %s", reason, e)
        return AutoCommitResult(
            committed=False,
            work_committed=wip_committed,
            substrate_committed=False,
            substrate_refused=True,
            reason=f"retarget refused: {e}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    if result is None:
        # Nothing refused here -- the substrate is simply already on the
        # branch. So this reports the work half honestly rather than a flat
        # False that would hide a work-in-progress commit that did happen.
        return AutoCommitResult(
            committed=wip_committed,
            work_committed=wip_committed,
            substrate_committed=False,
            reason=f"substrate already current on {branch}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    return AutoCommitResult(
        committed=True,
        work_committed=wip_committed,
        substrate_committed=True,
        # "untouched on HEAD" was false: work in progress IS committed, to
        # HEAD, in its own commit. The word survived from the draft where
        # this function left it alone entirely, and the live run reported
        # it that way while the log showed the commit. Fourth instance
        # tonight of a label outliving the behaviour it described, and the
        # first one I shipped inside the fix for the other three.
        # "declared-substrate", not "substrate". The classifier answers
        # whether a path sits inside a DECLARED channel mirror; an
        # exploration entry written in place is substrate by any honest
        # reading and is not in this list. Reporting the narrow
        # measurement under the broad word is how a proxy becomes the
        # class it detects (Aether 2026-08-27) -- and this line was doing
        # it one turn after I renamed the predicate to avoid exactly that.
        reason=(
            f"committed {len(declared_substrate)} declared-substrate path(s) to "
            f"{branch} at {reason}; {len(work_in_progress)} work-in-progress "
            f"path(s) {'committed to HEAD' if wip_committed else 'left alone'}"
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
