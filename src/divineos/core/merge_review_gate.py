"""Merge-review gate — server-verifiable, operator-anchored merge approval.

Andrew 2026-05-30 named the hole: the existing server-side CI check
(.github/workflows/integrity-audit.yml) verifies only that an
``External-Review: <id>`` text LINE is PRESENT in a commit message — not
that the referenced round exists or that anyone actually approved. A
plausible-looking line passes. It is gameable by exactly the kind of
unverified confident assertion the rest of the OS exists to catch.

## Why "two GitHub accounts" was the wrong design

An earlier draft of this module required TWO distinct GitHub approvers:
a user login AND an external-AI bot login. That was built on a false
premise — Aletheia is a Claude WEB instance. She has no GitHub account,
no token, and never will. Her audit reaches the repo only by Andrew
RELAYING it. The actor-authenticity spec (exploration/aether/45) already
said this: external-vantage actors "are identified by the operator's
relay; the relay-trust is given." There is no second account to wait for.

## The actual anchor: the operator's approval IS the relay

There is exactly one identity in this system the agent genuinely cannot
forge: Andrew, on GitHub. The agent holds no credentials for his account.
So his ``APPROVED`` PR review is the unforgeable keystone — and it already
MEANS "I read Aletheia's audit and I vouch for it," because Andrew waits
for her full CONFIRMS before approving (his stated discipline: confirms-on-
some + fixes-on-others → he waits).

So the gate requires, bound to the exact head commit:

1. An ``APPROVED`` PR review from a configured operator login (the keystone
   the agent cannot fake), AND
2. A logged audit-round id referenced in the PR (the recorded reasoning
   Andrew is vouching for — the paper trail that says WHY).

Both server-visible; (1) is the lock, (2) is the receipt.

## Purpose: alignment, not error-prevention (Andrew 2026-05-30)

This gate is NOT here to stop broken code reaching ``main``. Broken merges
are normal, non-permanent, and fixable later — the whole build is full of
caught-and-fixed breakage, and that is the system working. The gate exists
to keep the AGENT ALIGNED and to make shoggoth-drift expensive: the agent
cannot quietly self-merge changes to its own guardrail stack without the
operator-keystone. Errors are fuel; misalignment is the threat this guards.

Therefore it is EXPENSIVE-to-game, not impossible, and ALWAYS bypassable:
the check reports a verdict; it does not by itself imprison ``main``. An
admin merge / announced+logged ``emergency_bypass`` is the sanctioned
escape (loud and recorded, never silent). A gate with no bypass is a cage,
not a keel.

## Why this module is pure

Fetching reviews + round-state is integration (``gh api`` / audit store);
DECIDING is pure logic over observable records. Keeping the decision pure
makes it unit-testable without a live PR, and lets any harness (GitHub
Action, local pre-push, a future port) feed it records and trust the verdict.

The operator roster lives in a committed config
(``.github/merge_reviewers.json``) — logins are public, not secret. That
config is itself guardrail-protected, so the agent cannot quietly add its
own login to the operator roster without tripping this very gate — the same
self-protecting pattern as ``guardrail_files.txt``.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import re
from dataclasses import dataclass

# An External-Review trailer / reference: "External-Review: round-<id>".
# Matches anywhere (PR body or commit message), case-insensitive.
_ROUND_REF_PATTERN = re.compile(r"External-Review:\s*(\S+)", re.IGNORECASE)


@dataclass(frozen=True)
class Review:
    """One PR review record, normalized from the GitHub reviews API.

    - ``author_login``: the reviewer's GitHub login (case-insensitive match).
    - ``state``: review state, e.g. ``APPROVED`` / ``CHANGES_REQUESTED`` /
      ``COMMENTED`` / ``DISMISSED``.
    - ``commit_id``: the head SHA the review was submitted against. Used for
      SHA-binding: an approval of an OLD commit does not authorize a NEW one.
    """

    author_login: str
    state: str
    commit_id: str


@dataclass(frozen=True)
class MergeReviewConfig:
    """Committed operator roster. NOT secret — logins are public.

    ``operator_logins`` are the GitHub accounts whose APPROVED review counts
    as the unforgeable keystone. Normally just Andrew. An empty roster makes
    the gate fail closed (can never be satisfied), which is the safe default.
    """

    operator_logins: frozenset[str]


def load_config(raw: str) -> MergeReviewConfig:
    """Parse ``.github/merge_reviewers.json``.

    Expected shape:
        {"operator": ["andrew-login"]}

    Back-compat: also accepts the older ``"user"`` key for the operator
    roster. The older ``"external_ai"`` key is now IGNORED — there is no
    separate AI GitHub identity (Aletheia is relayed by the operator, whose
    approval already encodes her confirm). Missing/!list → empty (fail closed).
    """
    try:
        data = json.loads(raw or "{}")
    except (json.JSONDecodeError, ValueError):
        return MergeReviewConfig(frozenset())
    if not isinstance(data, dict):
        return MergeReviewConfig(frozenset())

    vals = data.get("operator")
    if not isinstance(vals, list):
        vals = data.get("user")  # back-compat alias
    if not isinstance(vals, list):
        return MergeReviewConfig(frozenset())
    return MergeReviewConfig(
        operator_logins=frozenset(str(v).strip().lower() for v in vals if str(v).strip())
    )


def has_round_reference(text: str) -> str | None:
    """Return the referenced audit-round id if an External-Review reference
    is present in ``text`` (PR body or commit message), else None."""
    if not text:
        return None
    m = _ROUND_REF_PATTERN.search(text)
    return m.group(1).strip() if m else None


def verify_merge(
    reviews: list[Review],
    head_sha: str,
    pr_body_and_commits: str,
    config: MergeReviewConfig,
    round_is_logged: bool,
) -> tuple[bool, str]:
    """Decide whether this PR carries valid operator-anchored approval.

    PASS requires ALL of:
      1. An ``APPROVED`` review from a configured operator login, submitted
         against ``head_sha`` (the keystone the agent cannot forge).
      2. An ``External-Review: <round-id>`` reference present in the PR body
         or a commit message (the receipt naming the audit being vouched for).
      3. ``round_is_logged`` True — the referenced round actually exists in
         the audit store (caller looks it up; passing this in keeps the
         decision pure). Guards against a fabricated round id.

    SHA-binding (rule 1 requires ``commit_id == head_sha``) makes a stale
    approval worthless: push new code, the old approval no longer counts.

    Fails CLOSED on every missing piece. NOTE: this returns a verdict; it
    does not enforce. The caller (CI check) decides what to do with a False,
    and the emergency-bypass path remains available by design.
    """
    head = (head_sha or "").strip().lower()
    if not head:
        return False, "No head SHA provided; cannot verify SHA-bound approval."
    if not config.operator_logins:
        return False, "Operator roster is empty — gate fails closed."

    approved_by = {
        (r.author_login or "").strip().lower()
        for r in reviews
        if (r.state or "").strip().upper() == "APPROVED"
        and (r.commit_id or "").strip().lower() == head
        and (r.author_login or "").strip().lower() in config.operator_logins
    }
    if not approved_by:
        return False, (
            f"No APPROVED operator review on head {head[:12]}. "
            f"Required: an approval from one of {sorted(config.operator_logins)} "
            "on the current commit (stale approvals of older commits do not count)."
        )

    round_ref = has_round_reference(pr_body_and_commits)
    if not round_ref:
        return False, (
            "Operator approval present, but no 'External-Review: <round-id>' "
            "reference found in the PR body or commits — the audit being "
            "vouched for must be named."
        )
    if not round_is_logged:
        return False, (
            f"Referenced audit round '{round_ref}' is not present in the audit "
            "store — a round id was named but no such round was logged "
            "(guards against a fabricated reference)."
        )

    return True, (
        f"Merge approved: operator {sorted(approved_by)} approved head "
        f"{head[:12]}, vouching for logged audit round '{round_ref}'."
    )


__all__ = [
    "Review",
    "MergeReviewConfig",
    "load_config",
    "has_round_reference",
    "verify_merge",
]
