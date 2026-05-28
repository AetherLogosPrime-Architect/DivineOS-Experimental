"""PR-merge gate — block `gh pr merge` on guardrail-touching PRs without
a valid External-Review audit round.

## Why this exists

PR #50 (bandit, 2026-05-28) modified moral_compass.py (a guardrail file)
and merged without an External-Review trailer, producing a permanent red
Integrity Audit badge on main. Root cause: nothing checked the PR's file
list against the guardrail registry at merge-action time. The pre-merge
CI check fired red but GitHub didn't refuse the merge button.

Andrew 2026-05-28: the fix has to ship in the OS itself, not as an
operator-side GitHub branch-protection setting a fresh DivineOS install
would have to learn to flip. Clone the repo → discipline is inherited.

## Architecture

Thin doorman, same shape as deletion_discipline. The hook
(.claude/hooks/gh-pr-merge-gate.sh) reads the Bash command and asks
``block_reason()`` here for a verdict; the verdict comes from the
underlying check ``audit_pr_for_guardrail_touches()``. Per
[code-does-not-think]: the gate enforces that the audit-round-binding
was made, not whether it was wise.

## Falsifier

The gate should NOT fire when:
* The bash command is not a `gh pr merge`.
* The PR touches no guardrail files (lookup via guardrail_files.txt).
* The `gh pr merge` command's --body or --subject contains an
  ``External-Review: <round-id>`` trailer pointing at a valid round.

The gate SHOULD fire when:
* `gh pr merge <N>` is invoked AND the PR touches at least one
  guardrail file AND no External-Review trailer is in the command.

See prereg-b6dcddd005b0 for the falsifier and 30-day review.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

__guardrail_required__ = True

_GH_PR_MERGE_PATTERN = re.compile(r"\bgh\s+pr\s+merge\s+(\d+)\b")
_TRAILER_PATTERN = re.compile(r"^External-Review:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
_GUARDRAIL_LIST_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "guardrail_files.txt"
)


def _load_guardrail_set() -> set[str]:
    if not _GUARDRAIL_LIST_PATH.exists():
        return set()
    out: set[str] = set()
    for line in _GUARDRAIL_LIST_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.add(s)
    return out


def _pr_files(pr_number: int) -> list[str] | None:
    """Return the list of files in the PR via `gh pr view`.

    Returns None on any failure (gh missing, network error, bad PR
    number) — caller treats None as "cannot verify, fail-open".
    """
    try:
        proc = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "files"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    files = data.get("files") or []
    return [
        (f.get("path") or "").replace("\\", "/")
        for f in files
        if isinstance(f, dict) and f.get("path")
    ]


def audit_pr_for_guardrail_touches(pr_number: int) -> tuple[bool, list[str]]:
    """Return (touches_guardrail, touched_file_list).

    ``touches_guardrail=False`` means either the PR is clean OR the file
    list could not be fetched (fail-open at the audit-data layer; the
    gate's job is to enforce the binding when it CAN see a touch, not
    to invent touches it can't observe).
    """
    files = _pr_files(pr_number)
    if not files:
        return False, []
    guardrails = _load_guardrail_set()
    touched = sorted(set(files) & guardrails)
    return bool(touched), touched


def _command_has_external_review_trailer(command: str) -> bool:
    """True if the bash command body contains an External-Review trailer.

    Looks at the whole command (which for a `gh pr merge ... --body
    "..."` invocation includes the body text). Pragmatic v1: we don't
    try to perfectly parse shell quoting; the trailer pattern is
    distinctive enough that regex on the raw command suffices.
    """
    return bool(_TRAILER_PATTERN.search(command))


def block_reason(bash_command: str) -> str | None:
    """Verdict for the PreToolUse hook.

    Returns a denial message if the command is a guardrail-violating
    `gh pr merge`, else None. Fail-open on any error.
    """
    if not isinstance(bash_command, str) or not bash_command.strip():
        return None
    match = _GH_PR_MERGE_PATTERN.search(bash_command)
    if not match:
        return None
    try:
        pr_number = int(match.group(1))
    except ValueError:
        return None
    try:
        touches, touched_files = audit_pr_for_guardrail_touches(pr_number)
    except Exception:  # noqa: BLE001
        return None
    if not touches:
        return None
    if _command_has_external_review_trailer(bash_command):
        return None
    file_list = "\n".join(f"      - {p}" for p in touched_files)
    return (
        f"BLOCKED: PR #{pr_number} modifies guardrail file(s) but the merge "
        f"command carries no External-Review trailer.\n\n"
        f"  Guardrail files touched:\n{file_list}\n\n"
        f"  Guardrail-touching PRs require multi-party External-Review "
        f"before merging into main. This gate enforces the binding at the "
        f"merge-action layer, structurally — so a fresh DivineOS install "
        f"inherits guardrail protection without operator-side configuration.\n\n"
        f"  Here is the way:\n"
        f"    1. File an audit round: divineos audit submit-round '...' "
        f"--actor user --source-ref <sha>\n"
        f"    2. Submit user-CONFIRMS finding (actor=user, severity=info, "
        f"stance=CONFIRMS).\n"
        f"    3. Submit external-AI-CONFIRMS finding (actor=aletheia / grok "
        f"/ gemini, stance=CONFIRMS).\n"
        f"    4. Run: divineos audit pr-merge-check {pr_number} "
        f"--audit-round <round-id>\n"
        f"       That command validates the round and emits the merge "
        f"body with the trailer.\n"
        f'    5. Paste the emitted body into your gh pr merge --body "..."\n\n'
        f"  See prereg-b6dcddd005b0 for the falsifier and review schedule."
    )
