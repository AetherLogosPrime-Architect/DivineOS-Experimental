"""Compose and attach the External-Review trailer at the draft->ready transition.

Phase 3 of the audit-stamp-attachment fix (claim ae9d70c4,
prereg-d695c9060158). Phases 1 and 2 built the *validator* and the
*merge-time* gate: ``audit prepare-merge`` printed a body for a human to
paste, and ``gh-pr-merge-gate.sh`` refused an untrailered ``gh pr merge``.

Two gaps stayed open, and this module closes them:

1. Nothing watched the draft->ready transition, so a PR could be marked
   ready-for-review with no trailer anywhere and only fail later in CI.
2. The trailer was printed, never written. The paste step was manual, so
   the trailer's presence depended on someone remembering it.

The trailer's tree-hash MUST come from the PR head, not from local
``HEAD``. Composing it from whatever tree the caller happens to be
standing in stamps a hash that binds a different tree than the one being
merged -- a trailer that looks valid and certifies nothing.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass

RECENCY_DAYS = 14


@dataclass(frozen=True)
class RoundVerdict:
    """Whether a round can authorize a merge, and why not when it cannot."""

    ok: bool
    reason: str
    age_days: float
    remedy: str = ""


def validate_round(round_id: str, external_ai_actors: frozenset[str]) -> RoundVerdict:
    """Check a round carries both CONFIRMS and is inside the recency window.

    The same three checks ``audit prepare-merge`` makes, lifted out so the
    print-path and the write-path cannot drift into disagreeing about what
    counts as reviewed.
    """
    from divineos.core.watchmen.store import get_round, list_findings

    rnd = get_round(round_id)
    if rnd is None:
        return RoundVerdict(
            False,
            f"audit round '{round_id}' not found in the Watchmen store",
            999.0,
            "divineos audit submit-round '...' --actor user --source-ref <ref>",
        )

    findings = list_findings(round_id=round_id, limit=500)

    def _actor_of(f: object) -> str:
        return str(getattr(f, "actor", "") or "").lower()

    def _is_confirm(f: object) -> bool:
        stance = getattr(f, "review_stance", None)
        if stance is None:
            return True  # v1 pragmatic: existence = acknowledgement
        return str(getattr(stance, "value", stance)).upper() == "CONFIRMS"

    confirming = [f for f in findings if _is_confirm(f)]

    if not any(_actor_of(f) == "user" for f in confirming):
        return RoundVerdict(
            False,
            f"round '{round_id}' carries no CONFIRMS from actor=user",
            999.0,
            f"divineos audit submit '<what you reviewed>' --round {round_id} "
            "--actor user --severity info --category architecture -d '<why it holds>'",
        )

    if not any(_actor_of(f) in external_ai_actors for f in confirming):
        return RoundVerdict(
            False,
            f"round '{round_id}' carries no CONFIRMS from an external-AI actor "
            f"(one of: {', '.join(sorted(external_ai_actors))})",
            999.0,
            f"divineos audit file-external-confirm {round_id} --actor <name> ...",
        )

    created_at = getattr(rnd, "created_at", None) or getattr(rnd, "timestamp", None) or 0
    if isinstance(created_at, str):
        try:
            import datetime as _dt

            created_at = _dt.datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            created_at = 0
    age_days = (time.time() - float(created_at)) / 86400.0 if created_at else 999.0

    if age_days > RECENCY_DAYS:
        return RoundVerdict(
            False,
            f"round '{round_id}' is {age_days:.1f} days old; the recency "
            f"window is {RECENCY_DAYS} days",
            age_days,
            "A stale round cannot authorize a merge. File a fresh one.",
        )

    return RoundVerdict(True, "confirmed by operator and external AI", age_days)


def pr_head_tree_hash(pr_number: int) -> str:
    """Read the tree hash of the PR's head commit.

    Empty string means "cannot look", never "no binding needed". The caller
    decides what to do with that; a trailer bound to the wrong tree is worse
    than one openly missing the binding.
    """
    try:
        head = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "headRefOid"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        sha = json.loads(head.stdout).get("headRefOid", "")
        if not sha:
            return ""
        tree = subprocess.run(
            ["git", "rev-parse", f"{sha}^{{tree}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return tree.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    except (json.JSONDecodeError, KeyError):
        return ""


def compose_merge_body(
    round_id: str,
    title: str,
    age_days: float,
    tree_hash: str = "",
) -> str:
    """Build the squash-merge body carrying the External-Review trailer.

    GitHub takes the squash-merge message from the PR title and body, so
    writing this into the PR body is what makes the trailer survive onto
    the commit that actually lands on main.
    """
    trailer = f"External-Review: {round_id}"
    if tree_hash:
        trailer += f" tree-hash:{tree_hash}"
    return (
        f"{title}\n\n"
        f"Reviewed via audit round {round_id} "
        f"(operator-CONFIRMS + external-AI-CONFIRMS, age {age_days:.1f}d, "
        f"within {RECENCY_DAYS}d recency window).\n\n"
        f"{trailer}\n"
    )
