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

# Shell separators after which a new command begins, allowing for leading
# environment assignments (FOO=bar cmd ...).
_CMD_POSITION_RE = re.compile(r"(?:^|[;&|(){}\n]|&&|\|\|)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*$")


def strip_quoted(command: str) -> str:
    """Blank out single- and double-quoted spans, preserving length.

    A gate that searches the raw command string cannot tell INVOKING a thing
    from MENTIONING it. Quoted spans are data -- a grep pattern, a dict value,
    prose inside an echo -- and a gate that fires on them blocks reading about
    itself.

    Length is preserved rather than spans removed, so offsets computed against
    the result still index the original string.
    """
    out = list(command)
    quote: str | None = None
    i = 0
    while i < len(command):
        ch = command[i]
        if quote is None and ch in ("'", '"'):
            quote = ch
        elif quote is not None:
            if ch == "\\" and quote == '"' and i + 1 < len(command):
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch == quote:
                quote = None
            else:
                out[i] = " "
        i += 1
    return "".join(out)


def _at_command_position(command: str, match_start: int) -> bool:
    """True if a match at ``match_start`` sits where a command may begin."""
    return bool(_CMD_POSITION_RE.search(command[:match_start]))


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
        if _at_command_position(scrubbed, m.start()):
            return True
    return False


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
