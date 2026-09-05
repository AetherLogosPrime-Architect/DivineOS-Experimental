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
  - `git add -A` — includes untracked. Substrate letters are often
    untracked new files.
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
    """What the checkpoint actually did, in fields rather than in prose.

    THE HALVES REPORT SEPARATELY, merged 2026-09-04 from Aria's branch onto
    Aether's split. Every outcome below used to arrive through one boolean
    and a sentence, and a sentence is not parseable -- so a checkpoint that
    saved the work and deferred the letters read the same, to any caller, as
    one that did both. The prose said which; nothing could act on it.

    HIS ONE DEFENCE, and it is the reason ``split_failed`` exists rather
    than being folded into ``committed``: could-not-SPLIT and could-not-SAVE
    have opposite severities. The first costs a manual tidy. The second
    costs the work. Collapsing them is the failure this whole pair of
    branches was built to stop.

    His invariant is untouched: every failure path degrades toward
    committing MORE, never toward committing nothing.
    """

    committed: bool  # every half that was attempted actually landed
    reason: str  # human-readable outcome (for CLI surfacing)
    work_committed: bool = False  # the work-in-progress half landed
    substrate_committed: bool = False  # the substrate half landed
    split_failed: bool = False  # a split was wanted and could not be made
    files_synced: int = 0  # external files copied into repo_mirror
    dirty_lines: int = 0  # git status --porcelain lines seen


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

    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("auto_commit: git add failed: %s", e.stderr)
        return AutoCommitResult(
            committed=False,
            reason=f"git add failed: {e.stderr.strip()[:200]}",
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
    _unstage_self_invalidating(repo_root)

    staged_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if staged_check.returncode == 0:
        return AutoCommitResult(
            committed=False,
            reason="nothing staged after add",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    # SPLIT THE SAVE BY KIND, so nobody has to take it apart afterwards.
    #
    # ``substrate_paths.partition`` was written for exactly this call and then
    # never called. Aria built the declaration half on 2026-08-27 and its own
    # docstring says "Aether takes the mechanism"; measured 2026-09-03, the
    # module was imported by nothing but its own test, while a second copy of
    # the same logic grew in scripts/check_branch_scope.py. Built, correct,
    # tested, unwired -- the class this repository keeps rediscovering.
    #
    # What it costs unwired: on 2026-09-03 a checkpoint swept eighteen letters
    # onto a branch carrying nothing but an anchor fix. The push gate refused
    # it, correctly, and the cure was a manual three-branch rebuild in which
    # the tempting shortcut -- drop the checkpoint commits, trust the reflog --
    # risked the only copies of those letters in the tree.
    #
    # Two commits instead of one. Nothing is excluded, nothing is refused, the
    # tree still goes clean: the save-work contract is untouched. What changes
    # is that the separation happens HERE, while the information is present,
    # rather than being reconstructed later by someone reading a diff.
    #
    # WHAT THIS DELIBERATELY DOES NOT DO, because the limit is real rather than
    # skipped: the designed mechanism sends substrate to its own branch by
    # plumbing, never touching the code branch at all. That version leaves the
    # letters permanently dirty in the working tree of the code branch --
    # committed on a ref this branch cannot see -- so every later checkpoint
    # finds them again. Making the tree go clean and keeping substrate off the
    # branch are in tension, and I have not resolved it. This is the half that
    # is safe under either answer.
    return _commit_in_two_parts(repo_root, reason, files_synced, dirty_lines, channels)


def _staged_paths(repo_root: Path) -> list[str] | None:
    """Repo-relative staged paths, or None when the list could not be read.

    None is not an empty list. A caller that treats "could not look" as
    "nothing there" would silently fall back to the single-commit path and
    report a split that never happened.
    """
    try:
        listed = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("auto_commit: could not list staged paths: %s", exc)
        return None
    if listed.returncode != 0:
        logger.warning("auto_commit: could not list staged paths (git error)")
        return None  # both-empty: git refusing and git being unreachable are the
        # same answer to the caller -- the list could not be read -- and the only
        # move either licenses is the unsplit commit. An empty list is a DIFFERENT
        # answer and is returned as one below.
    return [line.strip() for line in (listed.stdout or "").splitlines() if line.strip()]


def _run_pathspec(repo_root: Path, args: list[str], paths: list[str]) -> bool:
    """Run a git command over ``paths`` fed on stdin, not on the command line.

    A session can stage hundreds of letters, and a path list spliced into argv
    hits the platform's argument limit -- which fails as a git error carrying
    no hint that LENGTH was the problem.

    ``args`` must NOT end in ``--``. The first version passed ``git add --``
    and the flags landed after it, so git read ``--pathspec-from-file=-`` as a
    literal filename and failed with "did not match any files" -- an error
    naming the paths when the fault was the separator.
    """
    try:
        done = subprocess.run(
            [*args, "--pathspec-from-file=-", "--pathspec-file-nul"],
            cwd=repo_root,
            input="\0".join(paths) + "\0",
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("auto_commit: %s failed: %s", " ".join(args), exc)
        return False
    if done.returncode != 0:
        logger.warning("auto_commit: %s failed: %s", " ".join(args), done.stderr.strip()[:200])
        return False  # both-empty: git refusing the pathspec and git failing to
        # start are the same answer here -- the staging did not happen -- and the
        # caller's response is identical either way: abandon the split and save
        # everything in one commit. The distinction lives in the log, where a
        # person debugging it can see which occurred.
    return True


def _commit_staged(repo_root: Path, subject: str, body: str) -> bool:
    try:
        subprocess.run(
            ["git", "commit", "-m", subject, "-m", body],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("auto_commit: git commit failed: %s", e.stderr)
        return False
    return True


def _commit_in_two_parts(
    repo_root: Path,
    reason: str,
    files_synced: int,
    dirty_lines: int,
    channels: tuple[ExternalChannel, ...],
) -> AutoCommitResult:
    """Commit the staged tree as one commit per kind when both kinds are present.

    Falls back to the single commit on ANY failure of the split, because the
    single commit is what this did before and losing the split costs a manual
    cleanup, while losing the save costs the work itself.

    ``channels`` is threaded from the caller rather than defaulted. The first
    version called ``partition`` with no channels, so it classified against the
    module defaults while the surrounding function synced and reported against
    whatever it had been handed -- and a caller passing an empty set, meaning
    "classify nothing", got a split anyway. One function, two disagreeing
    notions of what substrate is, and neither of them the caller's.
    """
    from divineos.core.substrate_paths import NoChannelsDeclared, partition

    footer = (
        f"Auto-commit fired at {reason} boundary.\n\n"
        f"External files synced into repo: {files_synced}\n"
        f"Dirty-tree lines caught: {dirty_lines}\n\n"
        "Committed automatically per Andrew 2026-07-05: the commit "
        "at extract/sleep boundaries fires itself, not remembered.\n\n"
        "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
    )

    staged = _staged_paths(repo_root)
    substrate: list[str] = []
    work: list[str] = []
    if staged:
        try:
            substrate, work = partition(staged, channels)
        except NoChannelsDeclared:
            # A broken channel configuration must not silently classify the
            # whole tree as work and commit it as one lump wearing a split's
            # name. Fall through to the honest single commit.
            logger.warning("auto_commit: no channels declared; committing without a split")
            substrate, work = [], []

    if not (substrate and work):
        kind = "substrate checkpoint"
        if staged is None:
            kind = "checkpoint (kind unknown -- staged list unreadable)"
        elif substrate and not work:
            kind = "substrate checkpoint"
        elif work and not substrate:
            kind = "work in progress"
        ok = _commit_staged(repo_root, f"auto-commit ({reason}): {kind}", footer)
        # Only one kind is present, so no split was ever wanted and its
        # absence is not a failure. The half that exists reports; the half
        # that does not stays False because nothing of it was attempted --
        # which is a different fact from an attempt that failed.
        return AutoCommitResult(
            committed=ok,
            work_committed=ok and bool(work),
            substrate_committed=ok and bool(substrate),
            reason=f"committed at {reason}" if ok else "git commit failed",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    # Work first, substrate second. A code branch that has picked up letters is
    # then trimmed by dropping the tip rather than by rebuilding the branch.
    if not _run_pathspec(repo_root, ["git", "reset", "--quiet"], substrate):
        ok = _commit_staged(repo_root, f"auto-commit ({reason}): substrate checkpoint", footer)
        # COULD-NOT-SPLIT, NOT COULD-NOT-SAVE. Both kinds are in this one
        # commit, so nothing is lost and both halves report true; what failed
        # is the separation. The whole reason split_failed is its own field is
        # that this line and the save-failure line used to be one boolean and
        # a sentence, and their severities are opposite.
        return AutoCommitResult(
            committed=ok,
            work_committed=ok,
            substrate_committed=ok,
            split_failed=True,
            reason=f"committed at {reason} (unsplit -- could not unstage substrate)",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    work_ok = _commit_staged(
        repo_root,
        f"auto-commit ({reason}): work in progress, {len(work)} path(s)",
        f"Split from the substrate written at the same checkpoint.\n\n{footer}",
    )

    # Restage the substrate whether or not the work commit succeeded. If it
    # failed, the work is still staged and both kinds land together -- which is
    # the old behaviour, and better than leaving the letters out of the save.
    if not _run_pathspec(repo_root, ["git", "add"], substrate):
        logger.warning(
            "auto_commit: could not restage substrate after splitting. The files "
            "remain on disk and unstaged; the next checkpoint will find them."
        )
        # The work landed; the substrate is DEFERRED, not lost and not
        # refused -- it sits on disk for the next checkpoint. That is a third
        # thing, and it is exactly the state a single boolean could not say:
        # committed reads true because every half attempted succeeded, and
        # substrate_committed reads false because that half never got to try.
        return AutoCommitResult(
            committed=work_ok,
            work_committed=work_ok,
            substrate_committed=False,
            split_failed=True,
            reason=f"committed work at {reason}; substrate left for the next checkpoint",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    sub_ok = _commit_staged(
        repo_root,
        f"auto-commit ({reason}): substrate checkpoint, {len(substrate)} path(s)",
        f"Split from the work in progress written at the same checkpoint.\n\n{footer}",
    )
    # The split happened. `committed` now means EVERY half attempted landed,
    # not "at least one did" -- a partial save reporting plain success is the
    # shape that sent a refused substrate half out under a true-looking
    # boolean on 2026-09-02. The or-form survives in the halves, which is
    # where a caller can act on it.
    return AutoCommitResult(
        committed=work_ok and sub_ok,
        work_committed=work_ok,
        substrate_committed=sub_ok,
        reason=(
            f"committed at {reason} in two parts: {len(work)} work, {len(substrate)} substrate"
        ),
        files_synced=files_synced,
        dirty_lines=dirty_lines,
    )


def checkpoint_report(result: AutoCommitResult, boundary: str) -> list[tuple[str, str]]:
    """What the operator should be told, as (text, colour) pairs.

    A FUNCTION BECAUSE THE SILENCE HAD NOWHERE TO BE TESTED. Aether, on the
    repair for his own finding, hours after making it:

        "The boolean was wrong and tested; you fixed it and tested it. The
         printing was silent and untested; you fixed it and it is still
         untested. If it regresses it will regress the way it failed the
         first time -- quietly."

    The earlier repairs were reachable from a test because they were VALUES.
    This one lived in `elif` branches inside command handlers, where the only
    way to reach it was to run a whole extract -- so the untestability is why
    it stayed silent, and why fixing it silently would have been so easy.

    The decision becomes a value. The call sites print what this returns and
    decide nothing.

    REWRITTEN 2026-09-04 onto Aether's two-commit split, which superseded the
    off-branch routing this originally reported on. The states it names are
    now his four exit paths rather than a retarget refusal -- but the reason
    it exists is unchanged, and so is the rule underneath: an empty list must
    mean nothing happened, never that something happened and went unsaid.
    """
    if result.committed and not result.split_failed:
        return [
            (
                f"[+] Auto-commit ({boundary}): {result.dirty_lines} dirty lines, "
                f"{result.files_synced} external files synced.",
                "green",
            )
        ]

    # COULD-NOT-SPLIT IS NOT COULD-NOT-SAVE, and they must not print alike.
    # Aether's own defence of his design, and he is right that the severities
    # are opposite: one costs a manual tidy, the other costs the work.
    if result.split_failed:
        lines = [(f"[!] Auto-commit ({boundary}): {result.reason}", "yellow")]
        if result.work_committed and not result.substrate_committed:
            lines.append(
                ("    The work IS saved. The substrate waits for the next checkpoint.", "yellow")
            )
        elif result.work_committed and result.substrate_committed:
            lines.append(("    Everything IS saved -- in one commit rather than two.", "yellow"))
        return lines

    lines = [(f"[!] Auto-commit ({boundary}): {result.reason}", "yellow")]
    if result.work_committed:
        lines.append(("    Unfinished work IS saved. The substrate is not.", "yellow"))
    return lines


def find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` to the first ancestor containing .git; None if
    none found."""
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None
