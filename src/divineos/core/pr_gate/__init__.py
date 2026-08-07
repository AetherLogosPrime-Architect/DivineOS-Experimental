"""PR gates — gh-pr-create / gh-pr-merge guard logic.

FOSSIL (Andrew 2026-06-13):
PRs #190, #191, #192 modified guardrail files and were opened
ready-for-review. The integrity-audit CI fires on ready PRs (skips
drafts) so it ran immediately and marked them red on the public
activity feed before Aletheia had a chance to audit. The gate
enforces: guardrail-touching branches must open as draft, get
audited, get the External-Review trailer amended, then promote
with `gh pr ready <n>` — CI fires once with the trailer already
present.

MIGRATED 2026-06-24 (Andrew direction, per prereg-17a6ff97ba67):
Was a heredoc-Python-inside-bash hook at
`.claude/hooks/gh-pr-create-draft-gate.sh` (130 lines). Logic now
lives here so any AI substrate (not just Claude Code) can call
the same check. Hook is now a thin wrapper that imports
`check_pr_create_safe`.

FAIL-OPEN DISCIPLINE (preserved from bash):
Any error in the gate's own logic (git command failure, missing
guardrail file, parse error) allows the PR through rather than
blocking. The gate's value is catching the easy mistake; if the
gate itself errors, the human still has audit-after-the-fact
recourse via the integrity-audit workflow.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass
class GateDecision:
    """Result of a PR-gate check.

    blocked: True if the gate is refusing the action.
    reason: Human-readable explanation when blocked, empty when allowed.
    touched_guardrails: List of guardrail files the branch touches
        (only populated when blocked, for surfacing in the message).
    """

    blocked: bool
    reason: str = ""
    touched_guardrails: list[str] | None = None


_GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create(?![-\w])")
_DRAFT_FLAG_RE = re.compile(r"(^|\s)(--draft|-d)(\s|$)")

# 2026-08-07: this module guarded the way IN and not the way OUT.
#
# `check_pr_create_safe` blocks OPENING a ready PR on a guardrail
# branch. Its own block message then names the correct next step —
# "promote with `gh pr ready <n>`" — and nothing guarded that step. The
# gate was fully satisfiable by opening as draft, then walked straight
# past by promoting.
#
# That is what happened: ten PRs marked ready in one batch, none
# audited, none carrying an External-Review trailer. Andrew: "all of
# them will fail as none of them have the external trailer since
# Aletheia never audited them." Every one went red on the public feed —
# the precise outcome this module exists to prevent, reached through the
# door it did not cover.
#
# Same shape as the rest of that day's findings: presence of a check is
# not coverage of a path. The create-gate was real, tested and working,
# and the transition it protected had a second entrance.
#
# Authorized past the keyword-enforcement doorman as case (b): these are
# protocol parsers, not behavior detectors. A git trailer is a fixed
# wire format and `gh pr ready` is a fixed CLI verb — no adversary is
# varying the wording.
_GH_PR_READY_RE = re.compile(r"\bgh\s+pr\s+ready(?![-\w])")
_EXTERNAL_REVIEW_RE = re.compile(r"^External-Review:\s*\S+", re.MULTILINE)
_PR_NUMBER_RE = re.compile(r"\bgh\s+pr\s+ready\s+(\d+)")


def is_gh_pr_ready(command: str) -> bool:
    """True if `command` is a `gh pr ready` invocation.

    Same discrete-subcommand discipline as `is_gh_pr_create` — a
    hypothetical `gh pr ready-check` is a different verb and must not
    match.
    """
    return bool(_GH_PR_READY_RE.search(command))


def branch_commit_messages(repo_root: str | None = None) -> list[str]:
    """Full messages of commits on this branch ahead of origin/main.

    NUL-delimited because commit bodies contain blank lines, and any
    line-based split would fragment one message into several.

    Fail-open on git error, matching `branch_files_changed`. Note where
    that lands the caller: fail-open here ALLOWS the promotion, so this
    is the weak edge of the check. Documented rather than quietly relied
    on — if git is unreadable the gate protects nothing and must not be
    mistaken for protection.
    """
    try:
        proc = subprocess.run(
            ["git", "log", "origin/main..HEAD", "--format=%B%x00"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return [chunk for chunk in proc.stdout.split("\0") if chunk.strip()]


def pr_body(command: str, repo_root: str | None = None) -> str:
    """Body text of the PR being promoted, or "" if it can't be read.

    Load-bearing, and it exists because the substrate contradicted the
    first draft of this gate. Knowledge entry a7193bf6 (read 44 times,
    and itself a correction of an earlier wrong entry) records what
    scripts/ci_check_multi_party_review.py actually does: it passes if
    the trailer appears in the PR BODY **or** any commit message in the
    range. A gate that only scanned commits would block promotions that
    CI would have passed — a false block, which is the friction that
    gets gates switched off.

    Takes the PR number from the command when given; otherwise lets `gh`
    resolve the current branch.
    """
    match = _PR_NUMBER_RE.search(command)
    args = ["gh", "pr", "view"]
    if match:
        args.append(match.group(1))
    args += ["--json", "body", "--jq", ".body"]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, cwd=repo_root, check=False)
    except OSError:
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def check_pr_ready_safe(command: str, repo_root: str | None = None) -> GateDecision:
    """Should this `gh pr ready` promotion proceed?

    Promotion is the moment CI starts firing — the integrity-audit
    workflow skips drafts and runs on ready PRs. Promoting a guardrail
    branch with no `External-Review` trailer anywhere therefore
    schedules a red badge, immediately and publicly.

    Routing:
      - Not a `gh pr ready` invocation       → ALLOW (gate doesn't apply)
      - Branch touches no guardrail files    → ALLOW (nothing to protect)
      - Trailer in a commit OR the PR body   → ALLOW (audit happened)
      - Guardrails touched, trailer nowhere  → BLOCK

    The check reads the TRAILER, not my recollection that an audit
    happened. Andrew 2026-08-07 on why this matters beyond tidiness:
    "when they push to git the only real red marks will be from actual
    errors." A promotion that is red-by-construction is noise that hides
    the genuine failures underneath it.
    """
    if not is_gh_pr_ready(command):
        return GateDecision(blocked=False)

    changed = branch_files_changed(repo_root=repo_root)
    if not changed:
        return GateDecision(blocked=False)

    guardrail = load_guardrail_set(repo_root=repo_root)
    if not guardrail:
        return GateDecision(blocked=False)

    touched = sorted(set(changed) & guardrail)
    if not touched:
        return GateDecision(blocked=False)

    messages = branch_commit_messages(repo_root=repo_root)
    if any(_EXTERNAL_REVIEW_RE.search(msg) for msg in messages):
        return GateDecision(blocked=False)
    if _EXTERNAL_REVIEW_RE.search(pr_body(command, repo_root=repo_root)):
        return GateDecision(blocked=False)

    truncated = touched[:5]
    overflow = " ..." if len(touched) > 5 else ""
    msg = (
        "BLOCKED: promoting this PR out of draft would fire the "
        "integrity-audit workflow on a guardrail branch with no "
        "`External-Review:` trailer in any commit or in the PR body. CI "
        "skips drafts and runs on ready PRs, so this promotion schedules "
        "a red multi-party-review badge on the public feed — before any "
        "audit has happened.\n"
        f"  Guardrail files touched: {', '.join(truncated)}{overflow}\n"
        f"  Commits scanned on this branch: {len(messages)}\n\n"
        "This is the door the create-gate did not cover. Ten PRs were "
        "promoted this way in one batch and every one went red.\n\n"
        "Fix: leave it draft until the audit round files, put the "
        "External-Review trailer on the branch commit, then promote. "
        "The squash-merge body needs it too — `divineos audit "
        "prepare-merge <round-id>` generates that body."
    )
    return GateDecision(blocked=True, reason=msg, touched_guardrails=touched)


def is_gh_pr_create(command: str) -> bool:
    """True if `command` is a `gh pr create` invocation.

    Matches as a discrete subcommand sequence — NOT triggered by
    sibling commands like `gh pr create-comment` (different verb).
    """
    return bool(_GH_PR_CREATE_RE.search(command))


def has_draft_flag(command: str) -> bool:
    """True if `command` has `--draft` or `-d` as a standalone flag."""
    return bool(_DRAFT_FLAG_RE.search(command))


def branch_files_changed(repo_root: str | None = None) -> list[str]:
    """Files touched by commits on current branch ahead of origin/main.

    Returns empty list on any git error — fail-open: we'd rather let
    a legitimate PR through than block on git errors.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd=repo_root,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def load_guardrail_set(repo_root: str | None = None) -> set[str]:
    """Read scripts/guardrail_files.txt into a set of paths.

    Returns empty set on any I/O error (fail-open).
    Strips comment lines (starting with #) and blank lines.
    """
    import os

    path = "scripts/guardrail_files.txt"
    if repo_root:
        path = os.path.join(repo_root, path)
    try:
        with open(path, encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip() and not line.strip().startswith("#")}
    except OSError:
        return set()


def check_pr_create_safe(command: str, repo_root: str | None = None) -> GateDecision:
    """The gate's central decision: should this `gh pr create` proceed?

    Routing:
      - Not a `gh pr create` invocation → ALLOW (gate doesn't apply)
      - Already has --draft → ALLOW (correct shape)
      - Branch touches no guardrail files → ALLOW (nothing to protect)
      - Branch touches guardrails AND no --draft → BLOCK with reason

    Failure modes (all fail-open):
      - git diff errors → ALLOW (can't compute touched files; safer to let through)
      - Missing guardrail file → ALLOW (can't determine the protected set)
    """
    if not is_gh_pr_create(command):
        return GateDecision(blocked=False)
    if has_draft_flag(command):
        return GateDecision(blocked=False)

    changed = branch_files_changed(repo_root=repo_root)
    if not changed:
        return GateDecision(blocked=False)

    guardrail = load_guardrail_set(repo_root=repo_root)
    if not guardrail:
        return GateDecision(blocked=False)

    touched = sorted(set(changed) & guardrail)
    if not touched:
        return GateDecision(blocked=False)

    truncated = touched[:5]
    overflow = " ..." if len(touched) > 5 else ""
    msg = (
        "BLOCKED: this branch modifies guardrail file(s) and would open a "
        "ready-for-review PR. The integrity-audit workflow skips drafts but "
        "fires on ready PRs — opening ready means a red multi-party-review "
        "badge on the public activity feed before audit.\n"
        f"  Guardrail files touched: {', '.join(truncated)}{overflow}\n\n"
        "Fix: open as draft, let Aletheia audit from origin, amend the "
        "External-Review trailer after the round files, then promote with "
        "`gh pr ready <n>`. The CI fires once with the trailer present.\n\n"
        "Add --draft to the gh pr create command and retry."
    )
    return GateDecision(blocked=True, reason=msg, touched_guardrails=touched)
