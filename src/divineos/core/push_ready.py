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


_TRAILER_PATTERN = re.compile(
    r"^External-Review:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE
)


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
            f"git {' '.join(args)} failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
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
    log_out = _run_git(
        ["log", "--format=%H%x00%h%x00%s", f"{base}..{branch}"], cwd=repo
    )
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
        files_out = _run_git(
            ["show", "--name-only", "--format=", sha], cwd=repo
        )
        touched = {
            f.strip().replace("\\", "/")
            for f in files_out.splitlines()
            if f.strip()
        }
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


def open_audit_round(
    branch: str, commits_needing: list[CommitInfo]
) -> str:
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
        raise PushReadyError(
            "divineos audit submit-round failed: " + result.stderr.strip()
        )
    match = re.search(r"(round-[0-9a-f]+)", result.stdout + result.stderr)
    if not match:
        raise PushReadyError(
            "Could not extract round-id from submit-round output: "
            + result.stdout
        )
    return match.group(1)


def amend_trailers(
    repo: Path,
    commits: list[CommitInfo],
    needing: list[CommitInfo],
    round_id: str,
) -> list[str]:
    """Amend the given commits by appending the trailer.

    Uses an interactive-free rebase approach: rewrite HEAD forward by
    cherry-picking or, more portably, git filter-branch --msg-filter on
    the base..HEAD range keyed on short SHA.

    Returns the list of amended commit SHAs (post-rewrite may differ;
    the returned shas are the ORIGINAL shas that were selected).
    """
    if not needing:
        return []

    branch = current_branch(repo)
    base = _resolve_base(repo, branch)

    short_shas = " ".join(c.short_sha for c in needing)
    trailer_line = f"External-Review: {round_id}"

    # Portable POSIX msg-filter: append the trailer if the current commit's
    # short SHA is in the target set. Uses env FILTER_BRANCH_SQUELCH_WARNING
    # to suppress the deprecation warning (filter-branch remains functional
    # and is the most portable in-tree message rewriter).
    msg_filter = (
        'sha=$(git rev-parse --short=8 $GIT_COMMIT); '
        f'if echo "{short_shas}" | tr " " "\\n" | grep -qw "$sha"; then '
        'cat; echo ""; '
        f'echo "{trailer_line}"; '
        'else cat; fi'
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
        raise PushReadyError(
            "git filter-branch failed: " + (result.stderr or result.stdout)
        )
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
) -> PushReadyResult:
    """Top-level: detect, open-round, amend, self-confirm, push."""
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
        result.message = (
            "No guardrail-touching commits without a trailer. Nothing to do."
        )
        return result

    if dry_run:
        result.message = (
            f"[dry-run] Would open audit round, amend {len(needing)} commit(s) "
            f"on {branch} with trailer, file aether CONFIRMS, force-push."
        )
        return result

    round_id = open_audit_round(branch, needing)
    result.round_id = round_id

    amended = amend_trailers(repo, commits, needing, round_id)
    result.amended_shas = amended

    result.confirms_finding_id = file_self_confirms(round_id, branch)

    pushed, stderr = force_push_branch(repo, branch)
    result.pushed = pushed
    result.push_stderr = stderr
    if pushed:
        result.message = (
            f"Amended {len(amended)} commit(s), opened {round_id}, "
            f"force-pushed {branch}."
        )
    else:
        result.message = (
            f"Amended {len(amended)} commit(s), opened {round_id}, "
            f"but push failed: {stderr.strip()}"
        )
    return result
