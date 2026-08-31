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
import shlex
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


def is_gh_pr_create(command: str) -> bool:
    """True if `command` is a `gh pr create` invocation.

    Matches as a discrete subcommand sequence — NOT triggered by
    sibling commands like `gh pr create-comment` (different verb).
    """
    return bool(_GH_PR_CREATE_RE.search(command))


def has_draft_flag(command: str) -> bool:
    """True if `command` has `--draft` or `-d` as a standalone flag."""
    return bool(_DRAFT_FLAG_RE.search(command))


def head_ref_of(command: str) -> str:
    """The branch this `gh pr create` opens a PR FOR.

    THE GATE USED TO ASK ABOUT THE WRONG BRANCH. It measured
    ``origin/main...HEAD`` unconditionally — whichever branch the caller
    happened to be standing in — while ``gh pr create --head <other>``
    opens a PR for a branch that may share nothing with the checkout.

    Caught 2026-08-29 opening a letters-only PR from a code branch. The
    gate refused it for touching four code files, named all four, and
    every one of them lived on the checkout rather than on the branch
    under review. Its advice happened to be right, which is one input
    away from being wrong the same way.

    PARSED WITH THE REAL TOKENISER, NOT A PATTERN. The keyword-doorman
    refused a regex here and was right to: shlex already knows what a
    command-line argument is, including the quoting my pattern fumbled,
    and a token comparison is auditable by eye in a way a character
    class is not.

    ``gh`` itself defaults ``--head`` to the current branch, so falling
    back to HEAD matches its behaviour rather than inventing one.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        # Unbalanced quotes: the caller's command will not run either, so
        # answering about HEAD costs nothing and guessing costs precision.
        return "HEAD"
    for i, token in enumerate(tokens):
        if token.startswith("--head="):
            return token[len("--head=") :] or "HEAD"
        if token in ("--head", "-H") and i + 1 < len(tokens):
            return tokens[i + 1]
    return "HEAD"


def branch_files_changed(repo_root: str | None = None, ref: str = "HEAD") -> list[str]:
    """Files touched by commits on ``ref`` ahead of origin/main.

    Returns empty list on any git error — fail-open: we'd rather let
    a legitimate PR through than block on git errors. An unresolvable
    ``ref`` lands here too, so a PR for a branch this checkout cannot
    see opens ready rather than being refused. That is this gate's
    existing bias rather than a new one — its whole failure posture is
    allow, and the cost of a wrong allow here is a missing draft flag,
    never a merge.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"origin/main...{ref}"],
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

    head = head_ref_of(command)
    changed = branch_files_changed(repo_root=repo_root, ref=head)
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
