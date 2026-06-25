"""Audit-visibility check — warn when auditable work is committed
locally but not yet on origin.

FOSSIL (Andrew 2026-06-02):
A sweep found ~55 local branches with only 3 on origin: committing is
not publishing, and nothing in the flow crossed that gap. The external
auditor (Aletheia) reviews via GitHub — local-only work is invisible
to her. This is the fail-loud half of the cure (claim 47ee9ab8,
surface 6).

MIGRATED 2026-06-24 (per prereg-69507d1a38db, hook-migration arc):
Was 66-line bash hook .claude/hooks/post-commit-audit-visibility.sh.
Logic moved here so any AI substrate can call the same check via
`divineos audit-visibility check`. Bash hook is now the thin
PostCommit event-adapter.

NOTE on the ls-remote choice:
Asks origin DIRECTLY via `git ls-remote`, NOT the local
remote-tracking ref. The tracking ref is a cache that goes stale
(a branch deleted on origin still leaves refs/remotes/origin/<b>
pointing at the old SHA, which would make this checker falsely
report "published"). A visibility-checker that trusts a stale cache
fails the exact way it is meant to catch. Network round-trip per
auditable commit is the cost of correctness.

FAIL-OPEN: ls-remote failure (offline, auth, etc.) warns
CONSERVATIVELY rather than assuming-published.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

# Path prefixes that count as "auditable" — work Aletheia needs to see.
# Pure docs/letters churn doesn't trigger the warning.
AUDITABLE_PREFIXES = (
    "src/divineos/",
    "scripts/",
    ".github/workflows/",
    "setup/",
    ".claude/hooks/",
)


@dataclass
class VisibilityResult:
    """Result of `check_visibility`.

    should_warn: True if the warning banner should fire.
    banner: The full banner text (empty if no warn).
    branch: Current branch name (for surfacing in callers).
    reason: Human-readable explanation of the decision (for logs).
    """

    should_warn: bool
    banner: str = ""
    branch: str = ""
    reason: str = ""


def _git(args: list[str], repo_root: str | None = None, timeout: int = 10) -> tuple[int, str]:
    """Helper for the small git calls. Returns (exit_code, stdout-stripped)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=repo_root,
        )
        return (result.returncode, (result.stdout or "").strip())
    except (subprocess.SubprocessError, OSError):
        return (1, "")


def _current_branch(repo_root: str | None = None) -> str:
    _, out = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return out


def _files_in_head(repo_root: str | None = None) -> list[str]:
    rc, out = _git(["show", "--name-only", "--format=", "HEAD"], repo_root)
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_auditable_path(path: str) -> bool:
    """True if the path is under one of AUDITABLE_PREFIXES."""
    return any(path.startswith(prefix) for prefix in AUDITABLE_PREFIXES)


def _local_head_sha(repo_root: str | None = None) -> str:
    _, out = _git(["rev-parse", "HEAD"], repo_root)
    return out


def _remote_head_sha(branch: str, repo_root: str | None = None) -> tuple[int, str]:
    """Returns (exit_code, sha). exit_code != 0 = ls-remote failed."""
    rc, out = _git(["ls-remote", "--heads", "origin", branch], repo_root, timeout=15)
    if rc != 0:
        return (rc, "")
    first = (out or "").splitlines()[0:1]
    if not first:
        return (0, "")
    sha = first[0].split()[0] if first[0].split() else ""
    return (0, sha)


def _format_banner(branch: str, repo_root: str | None = None) -> str:
    """The exact loud banner the bash hook produced — preserved verbatim."""
    rc, log_line = _git(["log", "-1", "--format=%h %s"], repo_root)
    if rc != 0 or not log_line:
        log_line = "(unknown)"

    return (
        "\n"
        "  ============================================================\n"
        "  ⚠  AUDITABLE WORK NOT VISIBLE TO ALETHEIA\n"
        "  ------------------------------------------------------------\n"
        f"  Branch  : {branch}\n"
        f"  Commit  : {log_line}\n"
        "  Problem : committed locally, NOT on origin. The auditor reviews\n"
        "            via GitHub — local-only work is invisible to her.\n"
        f"  Fix     : git push -u origin {branch}\n"
        "            (the pre-push gate runs the test suite; let it finish)\n"
        "  Root    : claim 47ee9ab8 surface 6 — commit is not publish.\n"
        "  ============================================================\n"
    )


def check_visibility(repo_root: str | None = None) -> VisibilityResult:
    """Should the post-commit visibility-warning fire?

    Logic:
      1. On main / detached / no-branch → no warn (main is published by def)
      2. If HEAD commit touches NO auditable paths → no warn
      3. ls-remote origin for current branch
         - If clean exit AND remote SHA matches local HEAD → no warn (published)
         - Otherwise → WARN (local-only OR ls-remote failed, fail-loud)
    """
    branch = _current_branch(repo_root)
    if not branch or branch in ("HEAD", "main"):
        return VisibilityResult(
            should_warn=False,
            branch=branch,
            reason="main / detached / empty — nothing to warn about",
        )

    changed = _files_in_head(repo_root)
    if not any(is_auditable_path(p) for p in changed):
        return VisibilityResult(
            should_warn=False,
            branch=branch,
            reason="HEAD touches no auditable paths",
        )

    local_sha = _local_head_sha(repo_root)
    if not local_sha:
        return VisibilityResult(
            should_warn=False,
            branch=branch,
            reason="local HEAD not resolvable",
        )

    ls_exit, remote_sha = _remote_head_sha(branch, repo_root)
    if ls_exit == 0 and remote_sha and remote_sha == local_sha:
        return VisibilityResult(
            should_warn=False,
            branch=branch,
            reason="local HEAD matches origin — published",
        )

    banner = _format_banner(branch, repo_root)
    if ls_exit != 0:
        reason = f"ls-remote failed (exit {ls_exit}) — warning conservatively"
    elif not remote_sha:
        reason = "branch not on origin"
    else:
        reason = f"local {local_sha[:7]} != origin {remote_sha[:7]}"
    return VisibilityResult(
        should_warn=True,
        banner=banner,
        branch=branch,
        reason=reason,
    )
