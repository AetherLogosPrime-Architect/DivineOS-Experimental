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

from divineos.core.command_match import at_command_position, strip_quoted


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

# Shell separators after which a new command begins, allowing for leading
# environment assignments (FOO=bar cmd ...).
# The mention-vs-use helpers live in command_match, shared with pr_merge_gate
# and gh-pr-ready-gate. They were duplicated here first; the duplication is
# exactly how the sibling gates kept the bug after one of them fixed it.


_DRAFT_FLAG_RE = re.compile(r"(^|\s)(--draft|-d)(\s|$)")


def is_gh_pr_create(command: str) -> bool:
    """True if `command` is a `gh pr create` invocation.

    Matches as a discrete subcommand sequence — NOT triggered by
    sibling commands like `gh pr create-comment` (different verb).

    TWO FURTHER GUARDS, added 2026-08-22 after this gate blocked a read-only
    statistics script whose only offence was containing the phrase inside a
    dict literal, then blocked the grep that tried to read the gate, then
    blocked the patch that fixes it. Three refusals in one turn, not one of
    them an invocation.

      - quoted spans are scrubbed first, because a quoted occurrence is DATA
        and not an invocation;
      - the match must sit at a COMMAND POSITION -- start of string, or after
        a shell separator, optionally behind env assignments -- so
        ``grep <phrase> file`` does not fire, since there the command being
        run is grep.

    The defect class is mention-read-as-use. A gate that fires on its own name
    is the wall-shape the sibling read-gate warns about in its own header:
    the cure sits behind the gate.
    """
    scrubbed = strip_quoted(command)
    for m in _GH_PR_CREATE_RE.finditer(scrubbed):
        if at_command_position(scrubbed, m.start()):
            return True
    return False


def has_draft_flag(command: str) -> bool:
    """True if `command` has `--draft` or `-d` as a standalone flag.

    QUOTE-SCRUBBED, and the DIRECTION of the bug is why this matters more than
    the one above it. `is_gh_pr_create` is an ENTRY: a mention read as a use
    BLOCKS, which is noisy but safe. This is an ESCAPE: finding the flag makes
    the gate STAND DOWN, so a mention read as a use is a FALSE NEGATIVE.

    Measured 2026-08-22 with the guardrail lookup mocked:

        gh pr create --title "see --draft docs"

    carries no draft flag, the raw search found one, and the decision came
    back blocked=False -- a guardrail-touching PR opening READY, which is
    exactly the red audit badge on the public feed this gate exists to stop.

    Found by sweeping for survivors of the shape removed from
    `is_gh_pr_create` an hour earlier, IN THIS SAME FILE. The entry predicate
    was repaired and the escape predicate was not, because nothing asked where
    else that shape lived. scripts/sibling_sweep.py is that question, made
    mechanical.
    """
    return bool(_DRAFT_FLAG_RE.search(strip_quoted(command)))


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
