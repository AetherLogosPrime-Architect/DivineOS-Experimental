"""CI driver for the operator-anchored merge-review gate.

This is the INTEGRATION layer for ``divineos.core.merge_review_gate``. The
core module is a pure decision function; this script does the impure parts:

  - fetch the PR's reviews (login, state, commit_id) via ``gh api``
  - fetch the PR body + the head SHA
  - look up whether the referenced audit round is actually logged
  - call ``verify_merge(...)`` and translate the verdict to an exit code

Run by the GitHub Action (``.github/workflows/integrity-audit.yml`` adds a
job) AND runnable locally for a dry-run:

    python scripts/ci_merge_review_check.py --pr 60 \
        --repo AetherLogosPrime-Architect/DivineOS-Experimental

Scope: EVERY PR to main. There is no touches-no-guardrail exemption; see the
comment in ``main`` for why that seam was closed 2026-08-13.

Exit codes:
  0 — gate PASSES (operator approval on head + named, logged round).
  1 — gate FAILS (verdict False). The message explains why.
  2 — infrastructure error (could not fetch PR data). Fails LOUD, not silent.

## Bypass (expensive-to-game, not impossible)

This check REPORTS a verdict; branch protection decides whether a failing
verdict blocks. The sanctioned escape for a genuine emergency is an admin
merge or the ``DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS`` env var, which routes
through ``emergency_bypass.record_emergency_use`` (LOGGED, REPORTED,
ADDRESSED, FIXED) — loud and recorded, never silent. A gate with no bypass
is a cage, not a keel.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from divineos.core.merge_review_gate import (
    Review,
    load_config,
    verify_merge,
)

_EMERGENCY_ENV = "DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS"
_CONFIG_PATH = ".github/merge_reviewers.json"


def _gh_json(args: list[str]) -> object | None:
    """Run a ``gh`` command returning JSON; None on any failure."""
    try:
        out = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        return json.loads(out.stdout or "null")
    except (json.JSONDecodeError, ValueError):
        return None


def _fetch_reviews(repo: str, pr: int) -> list[Review] | None:
    data = _gh_json(["api", f"repos/{repo}/pulls/{pr}/reviews", "--paginate"])
    if not isinstance(data, list):
        return None
    reviews: list[Review] = []
    for r in data:
        if not isinstance(r, dict):
            continue
        user = r.get("user") or {}
        reviews.append(
            Review(
                author_login=str(user.get("login", "")),
                state=str(r.get("state", "")),
                commit_id=str(r.get("commit_id", "")),
            )
        )
    return reviews


_APPROVAL_MARKER = "MERGE-APPROVED"

# Andrew 2026-08-15: "this used to be so much easier all it took was me saying
# i confirm and that was enough." He is right, and the ceremony grew without
# anyone deciding it should. The word he actually uses is the one that should
# work; a coined token is my vocabulary imposed on his approval.
_APPROVAL_PHRASES = ("MERGE-APPROVED", "I CONFIRM")


def _parse_time(value: str) -> datetime | None:
    """Parse a GitHub ISO-8601 timestamp; None on anything unexpected."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _head_commit_time(repo: str, head_sha: str) -> datetime | None:
    """When the head commit was committed, for ordering a bare approval."""
    data = _gh_json(
        ["api", f"repos/{repo}/commits/{head_sha}", "--jq", ".commit.committer.date"]
    )
    return _parse_time(str(data)) if isinstance(data, str) else None


def _fetch_comment_approvals(repo: str, pr: int, head_sha: str) -> list[Review]:
    """Operator approvals expressed as a PR comment, for the self-authored case.

    GITHUB DOES NOT LET YOU APPROVE YOUR OWN PULL REQUEST. The Approve button
    is not rendered for the author. Every PR in this repo is authored by the
    same account the gate requires an approval FROM, so ``verify_merge`` asked
    for a review that could not be created by anyone -- twelve PRs sat blocked
    for two weeks on a door with no handle, and the failure message
    ("No APPROVED operator review on head <sha>") read like work left undone
    rather than an impossibility. Same shape as the round-export fix above,
    one layer out.

    A comment is the channel GitHub leaves open to the author. The approval
    must NAME THE HEAD SHA, which preserves the property the review-based
    path had and is the whole point of the gate: approval is of a specific
    commit, so pushing new work invalidates it rather than inheriting it.

    Accepts a >= 7 char prefix, because that is what the operator sees in the
    UI and in ``git log --oneline``. Only comments from a login the config
    already trusts are considered, so this widens the CHANNEL, not the set of
    people who can approve.
    """
    data = _gh_json(["api", f"repos/{repo}/issues/{pr}/comments", "--paginate"])
    if not isinstance(data, list) or not head_sha:
        return []
    head_time = _head_commit_time(repo, head_sha)
    approvals: list[Review] = []
    for c in data:
        if not isinstance(c, dict):
            continue
        body = str(c.get("body") or "")
        upper = body.upper()
        marker, phrase = -1, ""
        for candidate in _APPROVAL_PHRASES:
            found = upper.find(candidate)
            if found >= 0 and (marker < 0 or found < marker):
                marker, phrase = found, candidate
        if marker < 0:
            continue
        marker += len(phrase) - len(_APPROVAL_MARKER)
        # Take the first hex run after the marker, not the first whitespace
        # token. The first real approval comment was rejected on a trailing
        # double-quote: the operator pasted the whole shell command --
        #
        #   gh pr comment 428 --body "MERGE-APPROVED: 654827a6"
        #
        # -- so the token was `654827a6"` and the prefix match failed on
        # punctuation while the approval itself was entirely genuine. A gate
        # that rejects a real approval over a quote character is friction with
        # no security value; anyone who can post the marker can post it clean.
        # Scanning for hex accepts the sha wrapped in quotes, backticks, code
        # fences or trailing commas, and still requires the operator to name
        # the actual commit.
        m = re.search(r"[0-9a-fA-F]{7,40}", body[marker + len(_APPROVAL_MARKER) :])
        if m:
            sha = m.group(0).lower()
            if not head_sha.lower().startswith(sha):
                continue
        else:
            # NO SHA NAMED. Accept the bare marker when the comment was
            # written AFTER the head commit existed.
            #
            # Andrew 2026-08-14: "i cant copy paste anything." Requiring him
            # to reproduce a commit id by hand is the same trap as requiring
            # a pasted trailer, one size smaller -- and a mistyped character
            # rejects a genuine approval, which is what already happened once
            # today over a stray quote.
            #
            # The property worth keeping is not the TEXT of the sha, it is
            # that approval cannot silently inherit onto work the operator
            # never saw. A timestamp gives that directly: a comment written
            # before the head commit existed cannot be approving it, and any
            # push after the comment moves the head past it again. Same
            # invariant, nothing to type.
            #
            # If either timestamp is unavailable the bare marker is REFUSED
            # and the sha form remains the only path -- unverifiable ordering
            # must not read as approval.
            when = _parse_time(str(c.get("created_at") or ""))
            if head_time is None or when is None or when < head_time:
                continue
        user = c.get("user") or {}
        approvals.append(
            Review(
                author_login=str(user.get("login", "")),
                state="APPROVED",
                commit_id=head_sha,
            )
        )
    return approvals


def _fetch_pr_meta(repo: str, pr: int) -> tuple[str, str] | None:
    """Return (head_sha, body_plus_commit_messages) or None on failure."""
    data = _gh_json(["api", f"repos/{repo}/pulls/{pr}", "--jq", "{head: .head.sha, body: .body}"])
    if not isinstance(data, dict):
        return None
    head = str(data.get("head", ""))
    body = str(data.get("body") or "")
    commits = _gh_json(
        [
            "api",
            f"repos/{repo}/pulls/{pr}/commits",
            "--jq",
            '[.[].commit.message] | join("\\n")',
        ]
    )
    commit_text = commits if isinstance(commits, str) else ""
    return head, body + "\n" + commit_text


def _round_is_logged(round_id: str) -> bool:
    """True if the referenced audit round is verifiably logged.

    Two sources, checked in that order:

    1. ``docs/audit_rounds/<round-id>.json`` -- committed, so it travels with
       the PR and lands in the diff the operator approves.
    2. The local Watchmen store, for someone running this on the machine that
       holds the audit.

    Source 1 exists because source 2 alone made this requirement impossible
    to satisfy anywhere but that one machine. The store lives at
    ``DIVINEOS_HOME/data/event_ledger.db``, which is gitignored; on a GitHub
    runner the ``audit_rounds`` table is not even created, ``get_round``
    raises, and the ``except`` below returned False. Every run. Confirmed
    2026-08-14 against an empty DIVINEOS_HOME: ``no such table:
    audit_rounds``. The gate was not strict, it was unsatisfiable -- and it
    reported that as an ordinary failure, so it read like work left undone
    rather than a door with no handle.

    Still fails toward False: a round nobody can confirm counts as absent.
    """
    if not round_id:
        return False
    try:
        from divineos.core.watchmen.round_export import exported_round_exists

        if exported_round_exists(Path.cwd(), round_id):
            return True
    except Exception:  # noqa: BLE001 — export unreadable → fall through to the store
        pass
    try:
        from divineos.core.watchmen.store import get_round

        return get_round(round_id) is not None
    except Exception:  # noqa: BLE001 — unknown/unreachable round → not logged
        return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args(argv)

    # Emergency bypass — expensive, logged, never silent.
    #
    # The env var triggers the bypass attempt, but `record_emergency_use`
    # enforces the cost: the operator MUST supply a substantive REASON
    # (>= 20 chars naming the malfunction / hotfix context). Without
    # that, the bypass refuses to fire.
    #
    # Prior shape (2026-06-08 fix, task #97): a broad `except Exception`
    # caught the ValueError that record_emergency_use raises for short
    # reasons, printed "logging failed", and `return 0`'d ANYWAY — so
    # `DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS=x` was a free silent escape.
    # New shape splits exceptions: ValueError (reason rejected) fails the
    # gate with a clear message; other exceptions (infra failure) keep
    # the bypass firing but report loudly so post-incident cleanup can
    # file the missed artifacts manually.
    bypass_reason = os.environ.get(_EMERGENCY_ENV, "").strip()
    if bypass_reason:
        try:
            from divineos.core.emergency_bypass import record_emergency_use

            report = record_emergency_use(
                gate_name="merge-review",
                env_var=_EMERGENCY_ENV,
                reason=bypass_reason,
            )
            print(
                f"[merge-review] EMERGENCY BYPASS fired — logged "
                f"(claim={report.claim_id}, psf={report.psf_id}). "
                "Gate passes under bypass; obligation surfaces until fixed."
            )
            return 0
        except ValueError as exc:
            # Reason rejected (too short / missing). Per task #97:
            # bypass-cost-must-exceed-tool-use. Setting the env var to
            # `x` should NOT be a free escape — the cost is naming WHY.
            # Gate FAILS as if the bypass weren't set, with a visible
            # diagnostic naming the rejection.
            print(
                f"[merge-review] EMERGENCY BYPASS REJECTED: {exc}\n"
                f"  Set {_EMERGENCY_ENV} to a substantive reason "
                f"(>= 20 chars) naming the malfunction or hotfix "
                f"context. One-word or empty reasons are not accepted — "
                f"the bypass cost is naming WHY this emergency was real.\n"
                f"  Gate FAILS until either a valid reason is supplied "
                f"or the underlying audit is completed.",
                file=sys.stderr,
            )
            return 1
        except Exception as exc:  # noqa: BLE001 — infra failures: stay loud, don't crash CI
            # Genuine logging-infrastructure failure (DB unavailable,
            # import error, etc). The operator supplied a valid reason,
            # so the bypass still fires — but the failed-to-log condition
            # is REPORTED loudly so post-incident cleanup can manually
            # file the claim + structural-fix obligation.
            print(
                f"[merge-review] EMERGENCY BYPASS fired but LOGGING FAILED: {exc}\n"
                f"  Reason recorded only in CI output: {bypass_reason[:200]}\n"
                f"  Manually file the emergency-bypass claim + "
                f"structural-fix obligation post-incident, because the "
                f"automated LOGGED/REPORTED/ADDRESSED chain did not complete."
            )
            return 0

    # No guardrail scoping. Andrew 2026-08-13: "all PR's merging to main must
    # have an audit... i notice the optimizer uses that as a metric to do
    # things that dont touch guardrail files to bypass it.. so there is no
    # more bypass."
    #
    # The guardrail list was a routable metric: whether the gate applied was a
    # property of which files a change happened to touch, which is a property
    # I control while writing the change. Every merge to main is now in scope.
    # Letters and docs need an audit too, and those are the cheap ones to
    # confirm -- the cost of the blanket rule is small and it has no seam.

    meta = _fetch_pr_meta(args.repo, args.pr)
    reviews = _fetch_reviews(args.repo, args.pr)
    if meta is None or reviews is None:
        print("[merge-review] INFRASTRUCTURE ERROR: could not fetch PR data.", file=sys.stderr)
        return 2

    head_sha, body_and_commits = meta
    reviews = reviews + _fetch_comment_approvals(args.repo, args.pr, head_sha)

    try:
        config_raw = Path(_CONFIG_PATH).read_text(encoding="utf-8")
    except OSError:
        config_raw = ""
    config = load_config(config_raw)

    from divineos.core.merge_review_gate import has_round_reference

    round_id = has_round_reference(body_and_commits) or ""
    round_logged = _round_is_logged(round_id)

    ok, msg = verify_merge(
        reviews=reviews,
        head_sha=head_sha,
        pr_body_and_commits=body_and_commits,
        config=config,
        round_is_logged=round_logged,
    )
    prefix = "[merge-review] PASS:" if ok else "[merge-review] FAIL:"
    print(f"{prefix} {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
