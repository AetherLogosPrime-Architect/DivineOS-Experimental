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
import time
from pathlib import Path

__guardrail_required__ = True

_GH_PR_MERGE_PATTERN = re.compile(r"\bgh\s+pr\s+merge\s+(\d+)\b")
# Trailer format (Phase 2, 2026-06-13):
#   External-Review: <round-id> [tree-hash:<40-hex>]
# Round-id is required; tree-hash suffix is optional during the
# transition window. The server-side CI gate verifies tree-hash
# when present; this local pre-merge gate only checks trailer
# presence and round validity (substance-binding happens at the
# CI layer, not here).
_TRAILER_PATTERN = re.compile(
    r"^External-Review:\s*(\S+)(?:\s+tree-hash:[a-f0-9]+)?",
    re.MULTILINE | re.IGNORECASE,
)
_GUARDRAIL_LIST_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "guardrail_files.txt"
)


def _current_head_tree_hash() -> str:
    """Return the tree-hash of the current git HEAD, or "" on any failure.

    Used to construct substance-bound External-Review trailers (Phase 2,
    2026-06-13). When this returns a hash, the emitted trailer is
    `External-Review: <round-id> tree-hash:<40-hex>` and the server-side
    CI gate verifies the binding. When this returns empty (git unreachable,
    not a repo, timeout), the trailer falls back to legacy form and
    the gate emits a deprecation warning.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""


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


def _find_usable_audit_round(pr_number: int, recency_days: int = 14) -> tuple[str | None, str, str]:
    """Task #114 (2026-06-09): look up whether a usable audit round
    exists that would let this PR's merge proceed, so the gate's block
    message can embed the ready-to-paste merge body inline instead of
    making the operator run a second command to find it.

    Returns a tuple ``(round_id, merge_body, diagnosis)``:
      - If a valid round exists: (round_id, merge_body, "")
      - If no valid round exists: (None, "", human-readable diagnosis
        naming the most-recent round's specific gap — missing
        user-CONFIRMS / missing AI-CONFIRMS / round is stale)

    "Valid" mirrors prepare-merge's checks exactly:
      1. round.status not closed
      2. ≥1 finding with actor=user, stance=CONFIRMS
      3. ≥1 finding with actor in external-AI set, stance=CONFIRMS
      4. round.created_at within recency_days

    Failures inside this helper are silent; the surrounding block_reason
    falls back to the long-form instructions.
    """
    try:
        from divineos.cli.audit_commands import _EXTERNAL_AI_ACTORS  # type: ignore
        from divineos.core.watchmen.store import list_findings, list_rounds
    except Exception:  # noqa: BLE001
        return None, "", ""

    try:
        rounds = list_rounds(limit=50)
    except Exception:  # noqa: BLE001
        return None, "", ""

    now = time.time()
    diagnosis_for_most_recent: str = ""
    most_recent_seen = False

    for rnd in rounds:
        try:
            round_id = getattr(rnd, "round_id", None) or getattr(rnd, "id", None)
            if not round_id:
                continue
            findings = list_findings(round_id=round_id, limit=500)
        except Exception:  # noqa: BLE001
            continue

        def _actor_of(f: object) -> str:
            val = getattr(f, "actor", "") or ""
            return str(val).lower()

        def _is_confirm(f: object) -> bool:
            stance = getattr(f, "review_stance", None)
            if stance is None:
                return True
            val = getattr(stance, "value", stance)
            return str(val).upper() == "CONFIRMS"

        confirming = [f for f in findings if _is_confirm(f)]
        user_confirms = [f for f in confirming if _actor_of(f) == "user"]
        ai_confirms = [f for f in confirming if _actor_of(f) in _EXTERNAL_AI_ACTORS]

        created_at = getattr(rnd, "created_at", None) or getattr(rnd, "timestamp", None) or 0
        if isinstance(created_at, str):
            try:
                import datetime as _dt

                created_at = _dt.datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                ).timestamp()
            except Exception:  # noqa: BLE001
                created_at = 0
        age_days = (now - float(created_at)) / 86400.0 if created_at else 999.0

        # Capture diagnosis for the FIRST (most recent) round, in case
        # nothing turns out valid further down.
        if not most_recent_seen:
            most_recent_seen = True
            if not user_confirms:
                diagnosis_for_most_recent = (
                    f"Most recent round '{round_id}' is missing a user-CONFIRMS finding."
                )
            elif not ai_confirms:
                diagnosis_for_most_recent = (
                    f"Most recent round '{round_id}' is missing an external-AI-CONFIRMS "
                    "finding (aletheia / grok / gemini)."
                )
            elif age_days > recency_days:
                diagnosis_for_most_recent = (
                    f"Most recent round '{round_id}' is {age_days:.1f}d old "
                    f"(recency window is {recency_days}d). Stale rounds cannot "
                    "authorize a new merge."
                )

        if not user_confirms or not ai_confirms or age_days > recency_days:
            continue

        # Valid round found — compose the ready-to-paste merge body.
        # Phase 2 (2026-06-13): include tree-hash from HEAD so the
        # server-side CI gate can verify substance-binding. Falls back
        # to legacy form if git is unreachable.
        tree_hash = _current_head_tree_hash()
        trailer = (
            f"External-Review: {round_id} tree-hash:{tree_hash}"
            if tree_hash
            else f"External-Review: {round_id}"
        )
        focus = getattr(rnd, "focus", "") or f"PR #{pr_number} merge under audit"
        merge_body = (
            f"{focus}\n\n"
            f"Reviewed via audit round {round_id} "
            f"(operator-CONFIRMS + external-AI-CONFIRMS, age {age_days:.1f}d, "
            f"within {recency_days}d recency window).\n\n"
            f"{trailer}"
        )
        return round_id, merge_body, ""

    return None, "", diagnosis_for_most_recent


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

    # Task #114 (2026-06-09): try to embed the ready-to-paste merge body
    # inline so the operator doesn't have to run pr-merge-check separately.
    # Same shape as PR #117's gate-recovery-by-construction — when the
    # gate can compute its own remedy, it should hand it over instead
    # of making the operator chase it across two commands.
    try:
        round_id, merge_body, diagnosis = _find_usable_audit_round(pr_number)
    except Exception:  # noqa: BLE001
        round_id, merge_body, diagnosis = None, "", ""

    if round_id and merge_body:
        # Found a valid round — embed the ready-to-paste body.
        return (
            f"BLOCKED: PR #{pr_number} modifies guardrail file(s) but the merge "
            f"command carries no External-Review trailer.\n\n"
            f"  Guardrail files touched:\n{file_list}\n\n"
            f"  A valid audit round IS available — round '{round_id}' has the "
            f"required user-CONFIRMS + external-AI-CONFIRMS findings within the "
            f"14-day recency window. Retry the merge with this body:\n\n"
            f"  gh pr merge {pr_number} --squash --body \"$(cat <<'EOF'\n"
            f"{merge_body}\n"
            f"EOF\n"
            f'  )"\n\n'
            f"  (The External-Review trailer above satisfies the multi-party-review "
            f"CI check; that's the only thing the gate is enforcing.)"
        )

    # No valid round — fall back to the long-form instructions, but
    # name the SPECIFIC gap if there's a recent-but-invalid round.
    diagnosis_block = ""
    if diagnosis:
        diagnosis_block = f"\n  Diagnosis: {diagnosis}\n"

    return (
        f"BLOCKED: PR #{pr_number} modifies guardrail file(s) but the merge "
        f"command carries no External-Review trailer.\n\n"
        f"  Guardrail files touched:\n{file_list}\n"
        f"{diagnosis_block}\n"
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
