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
    committed: bool
    reason: str  # human-readable outcome (for CLI surfacing)
    files_synced: int = 0  # external files copied into repo_mirror
    dirty_lines: int = 0  # git status --porcelain lines seen


#: Where substrate goes when it is staged on a branch that does not own it.
#: The same branch channel_letter_capture already writes to, deliberately not a
#: second declaration -- two names for the writing branch would drift, and the
#: drift would be silent.
SUBSTRATE_BRANCH = "substrate/aether"


def _retarget_staged_substrate(repo_root: Path) -> None:
    """Send staged substrate to its own branch instead of to whatever is checked out.

    THE PREVENTION HALF, and Aletheia named the gap in exactly these terms:
    the scope station added this same day reports the mixture on every READ and
    does nothing about the WRITE. Her evidence was the cleanest available -- I
    removed one letter by hand from the branch whose entire purpose is refusing
    that mixture, and a checkpoint put two hundred and forty-four back two
    minutes later, while I was writing to her about having fixed it.

    THE TENSION A PRIOR SESSION COULD NOT RESOLVE, quoted from its own note
    further down this file: committing substrate to its branch by plumbing
    "leaves the letters permanently dirty in the working tree of the code
    branch... so every later checkpoint finds them again. Making the tree go
    clean and keeping substrate off the branch are in tension, and I have not
    resolved it."

    It is resolved now, by two pieces that did not exist when that was written.
    The sync repair above means the bulk never arrives in the tree at all, so
    what remains is the handful genuinely written this session. And
    ``_remove_scaffolding`` takes those down once it can PROVE they are
    redundant -- same bytes on the branch by blob id, and untracked here --
    refusing to delete on either check failing.

    NO FALLBACK, and that is the whole contract of the mechanism this calls.
    When the branch will not resolve, the paths are unstaged and left on disk
    rather than committed here: committing them to HEAD is the defect, so a
    fallback would reintroduce it on the rare path where it is hardest to
    notice. The letter survives in the shared channel either way, which is
    where the crossing actually happens.
    """
    staged = _staged_paths(repo_root)
    if staged is None:
        logger.warning(
            "auto_commit: could NOT list staged paths, so substrate cannot be "
            "separated from code. Nothing retargeted -- this is a could-not-look, "
            "not a clean tree."
        )
        return

    try:
        from divineos.core.substrate_paths import NoChannelsDeclared, partition
    except ImportError:
        logger.warning("auto_commit: substrate declaration unavailable; nothing retargeted")
        return

    try:
        # Returns (substrate, code) as plain lists. Checked against the live
        # signature rather than assumed -- an attribute access here would have
        # thrown inside a checkpoint, where the failure surfaces as a lost save
        # rather than as an error anybody reads.
        substrate, _code = partition(staged)
    except NoChannelsDeclared:
        logger.warning("auto_commit: no substrate channels declared; nothing retargeted")
        return

    if not substrate:
        return

    current = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if current.returncode == 0 and current.stdout.strip() == SUBSTRATE_BRANCH:
        return  # Already the branch that owns writing; committing here is correct.

    # NO DESTINATION MEANS NO RETARGET, AND THAT IS NOT THE FALLBACK THE
    # MECHANISM FORBIDS. Its refusal exists so substrate never lands on HEAD
    # *instead of* its own branch. Where no such branch exists at all -- a fresh
    # clone, a test fixture, somebody else's checkout -- there is no contamination
    # question to answer, only a save question, and the two-commit split below
    # already answers that correctly and is already tested.
    #
    # Checked here rather than caught from the refusal, because the difference
    # matters: a branch that is MISSING is a repo without a writing home, and a
    # retarget that FAILS on a repo that has one is a fault worth shouting about.
    # Collapsing them would turn every fresh clone into a warning and teach me to
    # ignore the shout.
    exists = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{SUBSTRATE_BRANCH}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if exists.returncode != 0:
        logger.info(
            "auto_commit: no %s branch here, so substrate stays with the split "
            "commit -- nothing to route it to.",
            SUBSTRATE_BRANCH,
        )
        return

    try:
        from divineos.core.channel_letter_capture import _remove_scaffolding
        from divineos.core.substrate_retarget import RetargetRefused, commit_paths_to_branch
    except ImportError:
        logger.warning("auto_commit: retarget mechanism unavailable; nothing retargeted")
        return

    try:
        commit_paths_to_branch(
            repo_root,
            SUBSTRATE_BRANCH,
            substrate,
            f"substrate(checkpoint): {len(substrate)} path(s) routed off a code branch",
        )
    except RetargetRefused as exc:
        logger.warning(
            "auto_commit: REFUSING to commit %d substrate path(s) here -- %s. "
            "They stay on disk and in the shared channel. Committing them to the "
            "checked-out branch is the defect this avoids, so there is no fallback.",
            len(substrate),
            exc,
        )

    # Unstaged either way. A retarget that refused must not leave them staged to
    # be swept into the very commit this is keeping them out of.
    _run_pathspec(repo_root, ["git", "restore", "--staged"], substrate)
    for rel in substrate:
        _remove_scaffolding(repo_root, repo_root / rel, rel, SUBSTRATE_BRANCH)


def _names_anywhere_in_history(repo_root: Path, mirror_rel: Path | str) -> set[str] | None:
    """Every filename this mirror path has EVER held, across all refs.

    None means the question could not be asked -- which is not the same as
    "nothing is in history", and the caller must not read it that way.

    One walk over all refs rather than a per-file probe: measured at well under
    a second across three thousand paths, because the alternative is a git call
    per candidate and there are hundreds of candidates every checkpoint.
    """
    # POSIX separators both ways. git emits forward slashes in --name-only
    # regardless of platform, so a Windows-flavoured prefix would match nothing
    # and every file would read as at-risk -- the sweep restored in its worst
    # form, by a path separator.
    rel = Path(mirror_rel).as_posix().rstrip("/")

    # ASK THE REPOSITORY I MEAN, NOT WHICHEVER ONE GIT FINDS. Without this,
    # a directory that is not itself a repo but sits inside one gets git's
    # answer about the ENCLOSING repo -- a confident reply about the wrong
    # tree, which is worse than a refusal. Caught by the could-not-read test,
    # which asserted None and got an empty set: history saying "never held"
    # about a path it was never asked about, and every file then reading as
    # at-risk. That is the sweep restored, by a working-directory accident.
    if not (repo_root / ".git").exists():
        logger.warning("auto_commit: %s is not a repository root -- cannot read history", repo_root)
        return None  # both-empty: this and the git-failure return below both mean COULD NOT ASK, and the caller's honest action is identical either way -- copy nothing, say so. They are deliberately indistinguishable to the caller and distinguished only in the log line each writes, because a caller branching on which kind of blindness it hit would be acting on a difference that changes nothing.

    try:
        proc = subprocess.run(
            ["git", "log", "--all", "--name-only", "--pretty=format:", "--", rel],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("auto_commit: could NOT read channel history for %s", mirror_rel)
        return None
    prefix = rel + "/"
    return {line[len(prefix) :] for line in proc.stdout.splitlines() if line.startswith(prefix)}


def _sync_external_channels(
    channels: tuple[ExternalChannel, ...],
    repo_root: Path,
) -> int:
    """Copy external-channel files that exist NOWHERE in the repository yet.

    THE SWEEP, DIAGNOSED 2026-09-15 AFTER DOING IT ALL DAY. This compared the
    shared channel against ``mirror.glob()`` -- the CURRENT BRANCH's working
    tree. On the branch that keeps writing, that tree already holds every
    letter, so nothing copied and nothing went wrong. On a code branch it holds
    almost none, so every letter in the channel read as missing and got copied
    in; ``git add -A`` then staged them and the checkpoint committed them.

    Hundreds, deterministically, every checkpoint fired while a code branch was
    checked out. Predicted from the branch's tracked set before reproducing it:
    246 letters. The sweep that had just landed carried 246.

    MISSING FROM THIS BRANCH IS NOT MISSING FROM THE REPOSITORY, and that is the
    whole confusion. The rescue this function exists for is real -- a letter
    living only in the shared directory is one disk failure from gone -- but a
    letter already committed on the writing branch is SAFE, and copying it onto
    a code branch rescues nothing while contaminating a branch whose one claim
    is that it carries no writing.

    So the comparison moves from "is it in this tree" to "has this repository
    ever held it, on any ref". Measured at the time of the fix: of the whole
    shared channel, the number genuinely at risk was ZERO -- every one was
    already on a branch that keeps writing. The old rule would have copied
    hundreds anyway.

    A history walk that FAILS is not an empty history. When the question cannot
    be asked, nothing is copied and the caller is told, because the alternative
    is treating an unreadable answer as permission to sweep -- which is the
    absence-becomes-value collapse this house keeps finding.
    """
    copied = 0
    for channel in channels:
        if not channel.source.is_dir():
            continue
        mirror = repo_root / channel.repo_mirror
        mirror.mkdir(parents=True, exist_ok=True)

        ever_held = _names_anywhere_in_history(repo_root, channel.repo_mirror)
        if ever_held is None:
            logger.warning(
                "auto_commit: SKIPPING channel %s -- could not read its history, "
                "so a file's absence here cannot be told from its absence "
                "everywhere. Nothing copied; this is a could-not-check, not a "
                "clean channel.",
                channel.name,
            )
            continue

        present_here = {p.name for p in mirror.glob(channel.pattern)}
        safe_elsewhere = 0
        for src_file in channel.source.glob(channel.pattern):
            if src_file.name in present_here:
                continue
            if src_file.name in ever_held:
                # Already committed somewhere. Copying it HERE would put writing
                # on whatever branch happens to be checked out.
                safe_elsewhere += 1
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
        if safe_elsewhere:
            logger.info(
                "auto_commit: %s -- %d file(s) absent from this branch and "
                "already held on another ref; left alone rather than swept in.",
                channel.name,
                safe_elsewhere,
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
    _retarget_staged_substrate(repo_root)

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
        return AutoCommitResult(
            committed=ok,
            reason=f"committed at {reason}" if ok else "git commit failed",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    # Work first, substrate second. A code branch that has picked up letters is
    # then trimmed by dropping the tip rather than by rebuilding the branch.
    if not _run_pathspec(repo_root, ["git", "reset", "--quiet"], substrate):
        ok = _commit_staged(repo_root, f"auto-commit ({reason}): substrate checkpoint", footer)
        return AutoCommitResult(
            committed=ok,
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
        return AutoCommitResult(
            committed=work_ok,
            reason=f"committed work at {reason}; substrate left for the next checkpoint",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    sub_ok = _commit_staged(
        repo_root,
        f"auto-commit ({reason}): substrate checkpoint, {len(substrate)} path(s)",
        f"Split from the work in progress written at the same checkpoint.\n\n{footer}",
    )
    return AutoCommitResult(
        committed=work_ok or sub_ok,
        reason=(
            f"committed at {reason} in two parts: {len(work)} work, {len(substrate)} substrate"
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
