"""push_ready — automate the External-Review trailer ceremony.

Given a branch containing commits that touch guardrail files, this
module:

  1. Detects which commits are missing an ``External-Review: <round-id>``
     trailer.
  2. Opens an audit round via ``divineos audit submit-round``.
  3. Amends each needing commit's message to append the trailer.
  4. Files an aether self-CONFIRMS finding on the round.
  5. Force-pushes the rewritten branch with ``--force-with-lease``.

The module operates on commits reachable from ``branch`` but not from
``origin/main`` — i.e. the diff of unpushed / unmerged work.

It is invoked as a guard operating on guarded files (it modifies commit
messages on branches that touch the guardrail set), so it is itself
guardrail-listed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

__guardrail_required__ = True


_TRAILER_PATTERN = re.compile(r"^External-Review:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)


@dataclass
class CommitInfo:
    """A single commit on the branch under inspection."""

    sha: str
    short_sha: str
    subject: str
    touches_guardrail: bool
    guardrail_files: list[str] = field(default_factory=list)
    has_trailer: bool = False
    trailer_value: str | None = None


@dataclass
class PushReadyResult:
    """Outcome of a push-ready run."""

    branch: str
    dry_run: bool
    commits: list[CommitInfo]
    needing_trailer: list[CommitInfo]
    round_id: str | None = None
    amended_shas: list[str] = field(default_factory=list)
    confirms_finding_id: str | None = None
    pushed: bool = False
    push_stderr: str = ""
    message: str = ""


class PushReadyError(RuntimeError):
    """Raised when push-ready cannot complete safely."""


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout, raise on non-zero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PushReadyError(
            f"git {' '.join(args)} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def load_guardrail_set(repo: Path) -> set[str]:
    """Parse scripts/guardrail_files.txt from ``repo``."""
    path = repo / "scripts" / "guardrail_files.txt"
    if not path.exists():
        return set()
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        result.add(stripped)
    return result


def current_branch(repo: Path) -> str:
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).strip()


def local_vs_remote(repo: Path, branch: str) -> tuple[str, str]:
    """Does the local branch still agree with what is on the remote?

    Returns ``(verdict, detail)`` where verdict is one of:

      ``"same"``      local and origin point at the same commit.
      ``"ahead"``     local contains origin; a force-push loses nothing.
      ``"stale"``     origin contains commits local does not have.
      ``"diverged"``  each has commits the other lacks.
      ``"unknown"``   the question could not be asked.
      ``"no-remote"`` the branch has never been pushed.

    WHY THIS EXISTS, and it cost real work twice on 2026-09-05.

    ``run_push_ready`` rewrites the LOCAL branch and force-pushes it. It
    never asked whether the local ref still matched the remote. Mine was two
    commits stale -- I had pushed a fix from a second worktree, which advanced
    origin without advancing the local ref -- so the rewrite ran against old
    history and the force-push put that old history back on the server,
    discarding the newer work. Twice, the second time after I had restored it
    by hand and had every reason to expect a different outcome.

    Nothing was lost, but only because the commits survived in the object
    store and I went looking. That is recovery by luck of inspection, not by
    design, and the tool reported success both times.

    The tell was there in the failure message and pointed the wrong way: it
    guessed "the branch is checked out in another worktree, so its history
    cannot be rewritten from here." No worktree held it. The rewrite HAD
    happened -- to the wrong history. A diagnosis that names a plausible cause
    it never tested is the same fault this house keeps finding: an
    honest-sounding answer to a question nobody asked.

    UNKNOWN IS ITS OWN ANSWER. A remote that cannot be read must not resolve
    to "same", because "same" is the reading that permits the force-push. The
    caller decides what to do with not-knowing; this only refuses to guess.
    """
    try:
        local = _run_git(["rev-parse", branch], cwd=repo).strip()
    except PushReadyError as exc:
        return "unknown", f"cannot resolve local branch {branch}: {exc}"

    remote_ref = f"refs/remotes/origin/{branch}"
    try:
        remote = _run_git(["rev-parse", "--verify", remote_ref], cwd=repo).strip()
    except PushReadyError:
        return "no-remote", f"no origin/{branch}; nothing on the server to overwrite"

    if local == remote:
        return "same", local

    def _contains(ancestor: str, descendant: str) -> bool | None:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        # Any other exit is git failing to answer, not answering "no".
        return None

    remote_in_local = _contains(remote, local)
    local_in_remote = _contains(local, remote)
    if remote_in_local is None or local_in_remote is None:
        return "unknown", "git could not compare the two tips"
    if remote_in_local:
        return "ahead", f"local {local[:12]} contains origin {remote[:12]}"
    if local_in_remote:
        return "stale", f"origin {remote[:12]} contains commits local {local[:12]} lacks"
    return "diverged", f"local {local[:12]} and origin {remote[:12]} have each diverged"


def _resolve_base(repo: Path, branch: str) -> str:
    """Resolve the merge-base against origin/main (or main as fallback)."""
    for ref in ("origin/main", "main"):
        try:
            base = _run_git(["merge-base", ref, branch], cwd=repo).strip()
            if base:
                return base
        except PushReadyError:
            continue
    raise PushReadyError(
        "Could not resolve merge-base with origin/main or main. "
        "Fetch first or specify a base explicitly."
    )


def detect_commits(
    repo: Path, branch: str, guardrail_set: set[str] | None = None
) -> list[CommitInfo]:
    """Return CommitInfo for each commit on ``branch`` not on origin/main."""
    if guardrail_set is None:
        guardrail_set = load_guardrail_set(repo)

    base = _resolve_base(repo, branch)
    log_out = _run_git(["log", "--format=%H%x00%h%x00%s", f"{base}..{branch}"], cwd=repo)
    commits: list[CommitInfo] = []
    for line in log_out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) < 3:
            continue
        sha, short_sha, subject = parts[0], parts[1], parts[2]

        # Files touched by this commit.
        files_out = _run_git(["show", "--name-only", "--format=", sha], cwd=repo)
        touched = {f.strip().replace("\\", "/") for f in files_out.splitlines() if f.strip()}
        guarded = sorted(touched & guardrail_set)

        # Full commit message for trailer detection.
        msg = _run_git(["log", "-1", "--format=%B", sha], cwd=repo)
        match = _TRAILER_PATTERN.search(msg)
        has_trailer = bool(match)
        trailer_value = match.group(1).strip() if match else None

        commits.append(
            CommitInfo(
                sha=sha,
                short_sha=short_sha,
                subject=subject,
                touches_guardrail=bool(guarded),
                guardrail_files=guarded,
                has_trailer=has_trailer,
                trailer_value=trailer_value,
            )
        )
    # git log emits newest-first; reverse to chronological order.
    commits.reverse()
    return commits


def _commits_needing_trailer(commits: list[CommitInfo]) -> list[CommitInfo]:
    return [c for c in commits if c.touches_guardrail and not c.has_trailer]


def open_audit_round(branch: str, commits_needing: list[CommitInfo]) -> str:
    """Call ``divineos audit submit-round`` and return the round-id."""
    focus = (
        f"auto-opened by push-ready for branch {branch}: "
        f"{len(commits_needing)} commit(s) require External-Review trailer"
    )
    cli = shutil.which("divineos") or "divineos"
    result = subprocess.run(
        [
            cli,
            "audit",
            "submit-round",
            focus,
            "--actor",
            "user",
            "--source-ref",
            branch,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PushReadyError("divineos audit submit-round failed: " + result.stderr.strip())
    match = re.search(r"(round-[0-9a-f]+)", result.stdout + result.stderr)
    if not match:
        raise PushReadyError(
            "Could not extract round-id from submit-round output: " + result.stdout
        )
    return match.group(1)


def amend_trailers(
    repo: Path,
    commits: list[CommitInfo],
    needing: list[CommitInfo],
    round_id: str,
    branch: str | None = None,
) -> list[str]:
    """Amend the given commits by appending the trailer.

    Uses an interactive-free rebase approach: rewrite HEAD forward by
    cherry-picking or, more portably, git filter-branch --msg-filter on
    the base..HEAD range keyed on short SHA.

    Returns the list of amended commit SHAs (post-rewrite may differ;
    the returned shas are the ORIGINAL shas that were selected).

    ``branch`` names the branch the CALLER selected the commits from. It is
    checked against the checkout rather than trusted, because the rewrite
    below runs on ``HEAD`` and cannot reach any other branch: handed a branch
    that is not checked out, this function would quietly rewrite whichever
    one is. Discovered 2026-09-05 stamping a request from a checkout of a
    different branch -- the amend reported success, nothing was stamped, and
    the guard downstream blamed a worktree that was not the cause.

    A caller that passes no branch keeps the old behaviour of acting on the
    checkout, which is correct when the checkout IS the subject.
    """
    if not needing:
        return []

    checked_out = current_branch(repo)
    if branch is not None and branch != checked_out:
        raise PushReadyError(
            f"cannot stamp {branch} from a checkout of {checked_out}: the amend "
            f"rewrites HEAD, so it would act on {checked_out} instead. "
            f"Check out {branch} (or run from a worktree holding it) and re-run."
        )
    branch = checked_out
    base = _resolve_base(repo, branch)

    short_shas = " ".join(c.short_sha for c in needing)
    trailer_line = f"External-Review: {round_id}"

    # Portable POSIX msg-filter: append the trailer if the current commit's
    # short SHA is in the target set. Uses env FILTER_BRANCH_SQUELCH_WARNING
    # to suppress the deprecation warning (filter-branch remains functional
    # and is the most portable in-tree message rewriter).
    msg_filter = (
        "sha=$(git rev-parse --short=8 $GIT_COMMIT); "
        f'if echo "{short_shas}" | tr " " "\\n" | grep -qw "$sha"; then '
        'cat; echo ""; '
        f'echo "{trailer_line}"; '
        "else cat; fi"
    )

    env = {"FILTER_BRANCH_SQUELCH_WARNING": "1"}
    # Merge with current environment.
    import os

    full_env = {**os.environ, **env}

    result = subprocess.run(
        [
            "git",
            "filter-branch",
            "-f",
            "--msg-filter",
            msg_filter,
            "--",
            f"{base}..HEAD",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env=full_env,
    )
    if result.returncode != 0:
        raise PushReadyError("git filter-branch failed: " + (result.stderr or result.stdout))
    return [c.sha for c in needing]


def file_self_confirms(round_id: str, branch: str) -> str | None:
    """File an aether self-CONFIRMS finding on the round. Returns finding-id or None."""
    cli = shutil.which("divineos") or "divineos"
    desc = (
        f"push-ready amended guardrail-touching commits on {branch} with "
        f"External-Review trailer for {round_id}. Self-CONFIRMS is a "
        "structural record — Aletheia + Andrew CONFIRMS still required "
        "for merge."
    )
    result = subprocess.run(
        [
            cli,
            "audit",
            "submit",
            f"push-ready self-audit: {branch} commits amended with trailer",
            "--round",
            round_id,
            "--actor",
            "aether",
            "--severity",
            "info",
            "--category",
            "integrity",
            "--tag",
            "CONFIRMS",
            "--description",
            desc,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Non-fatal: report but do not abort the push (the trailer is what
        # the merge-time gate actually checks; the finding is a log entry).
        return None
    match = re.search(r"(find-[0-9a-f]+)", result.stdout + result.stderr)
    return match.group(1) if match else None


def force_push_branch(repo: Path, branch: str) -> tuple[bool, str]:
    """Force-push with lease. Returns (succeeded, stderr)."""
    result = subprocess.run(
        [
            "git",
            "push",
            "--force-with-lease",
            "origin",
            branch,
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0, (result.stderr or result.stdout)


def run_push_ready(
    repo: Path,
    branch: str | None = None,
    dry_run: bool = False,
    round_id: str | None = None,
) -> PushReadyResult:
    """Top-level: detect, open-round, amend, self-confirm, push.

    ``round_id`` binds the trailer to a round that already exists instead
    of opening a fresh one, and suppresses the aether self-CONFIRMS.

    Both suppressions are required together. Andrew 2026-08-13, after the
    eleven stamped PRs all went red on the server-side gate: the trailer
    has to be on each guardrail-touching COMMIT as well as in the PR body,
    and stamp-ready wrote only the body. Folding this in means one command
    does both halves against ONE round.

    Reusing the default path would have minted a second round per branch
    and attached my own signature beside Andrew's and Aletheia's real
    confirms. A self-signature next to two real ones is worse than none --
    it pads the count with something that means nothing, on the exact
    mechanism built to require signatures that do.
    """
    branch = branch or current_branch(repo)
    guardrail_set = load_guardrail_set(repo)
    commits = detect_commits(repo, branch, guardrail_set)
    needing = _commits_needing_trailer(commits)

    result = PushReadyResult(
        branch=branch,
        dry_run=dry_run,
        commits=commits,
        needing_trailer=needing,
    )

    if not needing:
        result.message = "No guardrail-touching commits without a trailer. Nothing to do."
        return result

    if dry_run:
        if round_id:
            result.message = (
                f"[dry-run] Would amend {len(needing)} commit(s) on {branch} "
                f"with trailer bound to {round_id}, then force-push. "
                "No new round, no self-CONFIRMS."
            )
        else:
            result.message = (
                f"[dry-run] Would open audit round, amend {len(needing)} commit(s) "
                f"on {branch} with trailer, file aether CONFIRMS, force-push."
            )
        return result

    # REFUSE BEFORE REWRITING, NOT AFTER. Everything below this line rewrites
    # history and force-pushes it, so a stale local ref here does not produce a
    # failed run -- it produces a successful run that puts old history back on
    # the server. Checked here rather than at the call site because the danger
    # belongs to this function: any caller reaching it is about to overwrite.
    verdict, detail = local_vs_remote(repo, branch)
    if verdict in ("stale", "diverged", "unknown"):
        raise PushReadyError(
            f"Refusing to rewrite {branch}: local and origin disagree ({verdict}).\n"
            f"  {detail}\n"
            "This function amends commits and force-pushes, so rewriting a local\n"
            "branch the server has moved past would overwrite the newer work with\n"
            "the older -- and report success doing it. Twice on 2026-09-05.\n"
            "Fetch and fast-forward the local branch, then re-run."
            if verdict != "unknown"
            else (
                f"Refusing to rewrite {branch}: could not tell whether local and\n"
                f"origin agree ({detail}).\n"
                "Not-knowing is not permission. The reading that would allow the\n"
                "force-push is the one this cannot establish, so it declines."
            )
        )

    bound_to_existing = bool(round_id)
    if not round_id:
        round_id = open_audit_round(branch, needing)
    result.round_id = round_id

    amended = amend_trailers(repo, commits, needing, round_id, branch=branch)
    result.amended_shas = amended

    # Only self-confirm when this opened its own round. A caller supplying
    # a round has real signatures on it already; adding mine would pad the
    # count with a signature that certifies nothing.
    if not bound_to_existing:
        result.confirms_finding_id = file_self_confirms(round_id, branch)

    pushed, stderr = force_push_branch(repo, branch)
    result.pushed = pushed
    result.push_stderr = stderr
    if pushed:
        result.message = (
            f"Amended {len(amended)} commit(s), opened {round_id}, force-pushed {branch}."
        )
    else:
        result.message = (
            f"Amended {len(amended)} commit(s), opened {round_id}, "
            f"but push failed: {stderr.strip()}"
        )
    return result
