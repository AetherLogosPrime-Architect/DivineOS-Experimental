"""Branch health checks — catch stale-base + silent-deletion shapes before push.

## Why this exists

Lesson filed 2026-05-09 (knowledge 17b18dc3): branches created off stale
local main produce silent-rollback PRs at merge time. PR #343 on the
template repo showed 127 file deletions because the branch was created
from a local main weeks behind origin/main. The deletion-shape was
invisible from `git diff --stat`; only `git diff --diff-filter=D`
surfaced it.

## Relation to existing infrastructure

``scripts/check_branch_freshness.sh`` already exists (added 2026-04-24,
claim d3baec5a) for the same lesson at a different altitude. That
script is a pure binary freshness-blocker wired into the pre-push hook:
HEAD must include origin/main, or the push is rejected. This Python
module is a more nuanced health-check at the OS layer:

  - Gradient severity (ok / warn / critical) instead of binary block
  - Deletion-shape detection independent of base freshness
  - Testable Python with structured findings, not just exit codes
  - CLI surface (``divineos check-branch``) for manual pre-push
    verification, not just hook-time enforcement

The bash script catches the freshness case at push time; this module
catches both freshness and deletion-shape at any time, and exposes the
findings as data the rest of the OS can use. Both coexist; the bash
script remains the pre-push gate, this module is the OS-native check.

PR #343 happened because the bash script was wired in *Experimental's*
hooks; the template repo clone (DivineOS_fresh) never had hooks
configured. Hook propagation across clones is a separate structural
gap worth noting (filed for follow-up).

Aletheia's round-10 audit raised the gate-symmetry question: should
removal-of-multi-party-reviewed-work be gated the same as addition?
The answer at the architectural altitude (entry 44, May 4): each
scale's reader should ask the next scale's question. Pre-push is the
right altitude to ask "would merging this branch silently roll back
work that landed on main since this branch's base?"

## What this checks

Two distinct properties:

1. **Base freshness** — how many commits is `origin/<base>` ahead of
   the branch's merge-base? If many, the branch was created off stale
   main and likely produces apparent-deletions of work that landed
   meanwhile.

2. **Deletion shape** — how many files would merging this branch
   delete from main? Surfaced via `git diff --diff-filter=D`. Small
   refactors legitimately delete a few files; >N deletions warrants
   explicit verification.

Both checks are advisory by default. The CLI command can return
non-zero (for use in pre-push hooks) when either threshold is crossed.

## Architecture

This module is one instance of the design-shape entry 46 sketched: a
"checker-of-checkers" that asks the next-scale question. Pre-push is
asking the merge-time question. The module produces structured
findings; the CLI surfaces them; an optional pre-push hook can fail
the push when findings exceed thresholds.

Fail-open: if git is missing, the branch is detached, or any subprocess
errors, the check returns "unknown" rather than blocking. Network
operations (fetch) are explicitly opt-in via the ``fetch`` flag —
never run automatically because pre-push hooks shouldn't add latency
the user didn't ask for.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

# Default thresholds — tunable via CLI flags.
DEFAULT_STALE_COMMITS_THRESHOLD = 50
DEFAULT_DELETION_COUNT_THRESHOLD = 10


@dataclass
class BranchHealthFinding:
    """One finding from a branch-health check.

    ``severity`` is "ok" | "warn" | "critical". ``actionable`` is True
    if the finding suggests a specific operator action (rebase, verify
    deletions, etc.).
    """

    name: str
    severity: str
    message: str
    actionable: bool = True
    details: dict[str, object] | None = None


def _run_git(args: list[str], cwd: str | None = None, timeout: int = 10) -> tuple[int, str, str]:
    """Run a git command, returning (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return -1, "", str(e)


def check_base_freshness(
    base: str = "origin/main",
    cwd: str | None = None,
    fetch: bool = False,
    threshold: int = DEFAULT_STALE_COMMITS_THRESHOLD,
) -> BranchHealthFinding:
    """Check how stale the branch's base is relative to ``base``.

    Returns a finding with severity:
      - "ok": base is current (0-9 commits behind)
      - "warn": moderately stale (10 to threshold commits behind)
      - "critical": severely stale (> threshold commits behind)

    If ``fetch`` is True, runs ``git fetch`` first. Otherwise relies on
    the local cache, which may itself be stale. Pre-push hooks should
    pass ``fetch=False`` to keep latency low; manual ``divineos
    check-branch`` invocations should pass ``fetch=True``.
    """
    if fetch:
        rc, _out, err = _run_git(["fetch", "origin"], cwd=cwd, timeout=30)
        if rc != 0:
            return BranchHealthFinding(
                name="base_freshness",
                severity="warn",
                message=f"Could not fetch origin: {err[:120]}. Check is using cached refs.",
                actionable=False,
            )

    # Find merge-base between HEAD and origin/main
    rc, merge_base, err = _run_git(["merge-base", "HEAD", base], cwd=cwd)
    if rc != 0:
        return BranchHealthFinding(
            name="base_freshness",
            severity="warn",
            message=f"Could not find merge-base with {base}: {err[:120]}",
            actionable=False,
        )

    # Count commits on base that are not yet in this branch
    rc, count_str, err = _run_git(
        ["rev-list", "--count", f"{merge_base}..{base}"],
        cwd=cwd,
    )
    if rc != 0:
        return BranchHealthFinding(
            name="base_freshness",
            severity="warn",
            message=f"Could not count commits behind {base}: {err[:120]}",
            actionable=False,
        )

    try:
        behind = int(count_str)
    except ValueError:
        return BranchHealthFinding(
            name="base_freshness",
            severity="warn",
            message=f"Could not parse commit count: {count_str!r}",
            actionable=False,
        )

    if behind == 0:
        return BranchHealthFinding(
            name="base_freshness",
            severity="ok",
            message=f"Branch base is current with {base}.",
            actionable=False,
            details={"commits_behind": 0},
        )

    if behind < 10:
        return BranchHealthFinding(
            name="base_freshness",
            severity="ok",
            message=f"Branch is {behind} commit(s) behind {base}. Within tolerance.",
            actionable=False,
            details={"commits_behind": behind},
        )

    if behind <= threshold:
        return BranchHealthFinding(
            name="base_freshness",
            severity="warn",
            message=(
                f"Branch is {behind} commit(s) behind {base}. "
                f"Consider rebasing before push to avoid apparent-deletion shapes."
            ),
            actionable=True,
            details={"commits_behind": behind, "base": base},
        )

    return BranchHealthFinding(
        name="base_freshness",
        severity="critical",
        message=(
            f"Branch is {behind} commit(s) behind {base} (threshold {threshold}). "
            f"Pushing as-is will produce a PR that appears to delete work landed "
            f"on {base} since the branch base. Rebase or recreate from fresh main."
        ),
        actionable=True,
        details={"commits_behind": behind, "base": base, "threshold": threshold},
    )


def check_deletion_shape(
    base: str = "origin/main",
    cwd: str | None = None,
    threshold: int = DEFAULT_DELETION_COUNT_THRESHOLD,
) -> BranchHealthFinding:
    """Check how many files would be deleted by merging this branch into ``base``.

    Returns finding with severity:
      - "ok": 0-N deletions (within tolerance)
      - "warn": more than threshold deletions but plausibly intentional
      - "critical": deletions far exceed threshold (likely silent-rollback)

    This catches the PR #343 shape: 127 deleted files because the branch
    was based on stale main. The check is independent of base_freshness
    because the failure-mode looks the same from the merge target's
    perspective — files disappearing — regardless of whether the cause
    was branch-staleness or intentional removal.

    2026-07-14 fix (Aletheia audit — 2nd pass): the check no longer uses
    ``--find-renames``. Git's rename detection is a HEURISTIC (content
    similarity guessed at diff time, tuned by a threshold that can never
    make a guess deterministic). Instead, this function does a
    content-hash presence check: for each path git reports as deleted,
    read the blob hash from the old tree; if that blob still appears
    anywhere in the new tree, the file MOVED (not destroyed), and the
    path is excluded from the deletion count. If the blob appears
    nowhere in the new tree, the content is genuinely gone.

    That's arithmetic, not heuristic. A file's blob is either present
    in the new tree or it isn't; that's what content-addressed storage
    IS. No threshold. No tuning. No false-positives on archive-moves.

    Guardrail-file DELETIONS (intentional garbage removal, stale
    artifacts) still count toward the threshold as they should —
    their blobs don't exist anywhere in the new tree.
    """
    rc, raw_deleted, err = _run_git(
        [
            "diff",
            "--diff-filter=D",
            "--name-only",
            f"{base}..HEAD",
        ],
        cwd=cwd,
    )
    if rc != 0:
        return BranchHealthFinding(
            name="deletion_shape",
            severity="warn",
            message=f"Could not compute deletion shape vs {base}: {err[:120]}",
            actionable=False,
        )

    raw_deleted_list = [line for line in raw_deleted.splitlines() if line.strip()]

    # Content-hash presence check: for each candidate-deletion, the file
    # is genuinely deleted iff its old-tree blob does not appear anywhere
    # in the new tree. Blobs that still appear were MOVED, not destroyed.
    rc_new, new_tree, _err_new = _run_git(
        ["ls-tree", "-r", "HEAD"],
        cwd=cwd,
    )
    new_tree_blobs: set[str] = set()
    if rc_new == 0:
        # Each line is: "<mode> <type> <blob-hash>\t<path>"
        for line in new_tree.splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 3 and parts[1] == "blob":
                new_tree_blobs.add(parts[2])

    deleted_list: list[str] = []
    moved_list: list[str] = []
    for path in raw_deleted_list:
        rc_blob, old_blob, _ = _run_git(
            ["rev-parse", f"{base}:{path}"],
            cwd=cwd,
        )
        old_blob = old_blob.strip()
        if rc_blob == 0 and old_blob and old_blob in new_tree_blobs:
            moved_list.append(path)
        else:
            deleted_list.append(path)

    count = len(deleted_list)

    if count == 0:
        return BranchHealthFinding(
            name="deletion_shape",
            severity="ok",
            message="No files would be deleted by merge.",
            actionable=False,
            details={"deletion_count": 0},
        )

    if count <= threshold:
        return BranchHealthFinding(
            name="deletion_shape",
            severity="ok",
            message=f"{count} file(s) would be deleted by merge. Within tolerance.",
            actionable=False,
            details={"deletion_count": count, "files": deleted_list[:20]},
        )

    if count <= threshold * 3:
        return BranchHealthFinding(
            name="deletion_shape",
            severity="warn",
            message=(
                f"{count} file(s) would be deleted by merge (threshold {threshold}). "
                f"Verify deletions are intentional. First few: "
                f"{', '.join(deleted_list[:5])}{'...' if count > 5 else ''}"
            ),
            actionable=True,
            details={"deletion_count": count, "files": deleted_list[:20]},
        )

    return BranchHealthFinding(
        name="deletion_shape",
        severity="critical",
        message=(
            f"{count} file(s) would be deleted by merge (threshold {threshold}). "
            f"This is the silent-rollback shape — likely caused by stale branch base. "
            f"Run check_base_freshness to confirm; rebase if base is stale. "
            f"First few deletions: {', '.join(deleted_list[:5])}"
        ),
        actionable=True,
        details={"deletion_count": count, "files": deleted_list[:20]},
    )


def check_all(
    base: str = "origin/main",
    cwd: str | None = None,
    fetch: bool = False,
    stale_threshold: int = DEFAULT_STALE_COMMITS_THRESHOLD,
    deletion_threshold: int = DEFAULT_DELETION_COUNT_THRESHOLD,
) -> list[BranchHealthFinding]:
    """Run all branch health checks. Returns ordered list of findings."""
    return [
        check_base_freshness(base=base, cwd=cwd, fetch=fetch, threshold=stale_threshold),
        check_deletion_shape(base=base, cwd=cwd, threshold=deletion_threshold),
    ]


def has_critical(findings: list[BranchHealthFinding]) -> bool:
    """True if any finding is critical-severity."""
    return any(f.severity == "critical" for f in findings)


def has_warnings(findings: list[BranchHealthFinding]) -> bool:
    """True if any finding is warn or critical."""
    return any(f.severity in ("warn", "critical") for f in findings)
