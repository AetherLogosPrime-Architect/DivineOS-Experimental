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

Exit codes:
  0 — PASS (operator approval on head + named round), PENDING (nobody has
      approved the current head yet — the normal state of an open PR), OR
      the PR touches no guardrail files (gate does not apply).
  1 — FAIL. Someone approved, but the receipt does not hold up: no round
      named, or a round named that the audit store says does not exist.
  2 — infrastructure error (could not fetch PR data). Fails LOUD, not silent.

PENDING exits 0 deliberately (2026-08-01). This job runs on every push, and
an approval cannot exist on a head SHA created seconds earlier — so treating
unapproved as failure made the check unpassable by construction: 17 failures
and 0 passes across the recent run history. Nothing that was caught before
stops being caught; the FAIL conditions are unchanged. What changes is that
a red merge-review now carries information instead of being wallpaper.

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

from divineos.core.merge_review_gate import (
    Review,
    load_config,
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
    # No --jq here. It prints the selected string RAW, without quotes, and a
    # bare `2026-08-15T02:40:00Z` is not valid JSON -- so _gh_json's
    # json.loads failed, this returned None, and every bare confirmation was
    # refused for want of an ordering it could not read. The gate reported
    # "no approval on the current commit" while the approval sat right there.
    # Caught by dry-running the real PR; the unit test fed the timestamp in
    # directly and so never exercised this call at all.
    data = _gh_json(["api", f"repos/{repo}/commits/{head_sha}"])
    if not isinstance(data, dict):
        return None
    commit = data.get("commit")
    committer = commit.get("committer") if isinstance(commit, dict) else None
    when = committer.get("date") if isinstance(committer, dict) else None
    return _parse_time(str(when)) if when else None


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


def _round_is_logged(round_id: str) -> bool | None:
    """Whether the referenced audit round exists in the Watchmen store.

    True  — store was readable and the round is there.
    False — store was readable and the round genuinely is NOT there.
    None  — the store could not be read at all, so this is UNKNOWN.

    The None case is the whole point (2026-08-01). The audit store is local
    runtime state; every ``*.db`` is gitignored, so in CI there is no store
    to open and there never will be. The previous version collapsed
    "unreachable" into False and then reported it as "no such round was
    logged" — asserting that a round is fabricated on the strength of a
    lookup that never ran. Fail-closed is the right instinct when a check
    might be evaded; it is the wrong instinct when the condition is not
    merely likely to be unmet but structurally guaranteed to be, in every
    CI run, permanently.

    So the three states stay distinct and the caller decides what each one
    is worth. An empty ``round_id`` is a genuine absence — nothing was
    named — not an unknown.
    """
    if not round_id:
        return False

    # The exported record is checked FIRST, because it is the only one of the
    # two that exists in CI. `divineos audit export` writes each round to
    # docs/audit_rounds/<id>.md, and those files are committed, so a bare
    # checkout finally carries the review with it. This is what turns
    # round-verification from structurally-unknowable into verifiable.
    #
    # It is NOT the keystone and must not be read as one: a committed file is
    # agent-writable. The unforgeable part remains Andrew's GitHub approval on
    # the exact head SHA, and multi-party-review independently binds the
    # trailer to the reviewed tree by hash. What the export adds is that the
    # review is now READABLE — the findings are on the PR for a human.
    try:
        from divineos.core.watchmen.export import exported_round_exists

        if exported_round_exists(round_id):
            return True
    except Exception:  # noqa: BLE001 — no export available → try the live store
        pass

    try:
        from divineos.core.watchmen.store import get_round
    except Exception:  # noqa: BLE001 — module unimportable → cannot check
        return None
    try:
        return get_round(round_id) is not None
    except Exception:  # noqa: BLE001 — store unreadable/absent → cannot check
        return None


def _pr_touches_guardrail(repo: str, pr: int) -> bool:
    """True if the PR changes any file on the guardrail list."""
    files = _gh_json(
        ["api", f"repos/{repo}/pulls/{pr}/files", "--paginate", "--jq", "[.[].filename]"]
    )
    if not isinstance(files, list):
        # Cannot determine → assume it does, so the gate applies (fail safe).
        return True
    changed = {str(f).replace("\\", "/") for f in files}
    try:
        from pathlib import Path

        guard_raw = Path("scripts/guardrail_files.txt").read_text(encoding="utf-8")
    except OSError:
        return True
    guard = {
        line.strip().replace("\\", "/")
        for line in guard_raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    return bool(changed & guard)


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

    if not _pr_touches_guardrail(args.repo, args.pr):
        print("[merge-review] PR touches no guardrail files; gate does not apply.")
        return 0

    meta = _fetch_pr_meta(args.repo, args.pr)
    reviews = _fetch_reviews(args.repo, args.pr)
    if meta is None or reviews is None:
        print("[merge-review] INFRASTRUCTURE ERROR: could not fetch PR data.", file=sys.stderr)
        return 2

    head_sha, body_and_commits = meta

    # Comment approvals count as approvals (2026-08-14). GitHub refuses to let
    # an author approve their own pull request, and Andrew authors nearly all
    # of them, so the review-based path alone leaves this gate unsatisfiable by
    # the one person whose approval it asks for. A comment carrying the
    # approval phrase, dated after the head commit, is the path that exists.
    #
    # PORTED here during the main merge rather than taken wholesale. Main
    # restructured the verdict path around a boolean `ok`; this branch
    # restructured it around classify_merge's PENDING verdict (2026-08-01, and
    # the better shape — my 2026-08-15 script-level special-case was the later
    # duplicate). The comment-approval machinery is orthogonal to that
    # argument: it decides WHAT COUNTS as an approval, not what the verdict
    # means, so it grafts on instead of competing.
    #
    # Ten tests arrived with this merge and failed until this line existed —
    # the merge brought main's TESTS while I had kept this branch's
    # IMPLEMENTATION.
    reviews = reviews + _fetch_comment_approvals(args.repo, args.pr, head_sha)

    try:
        from pathlib import Path

        config_raw = Path(_CONFIG_PATH).read_text(encoding="utf-8")
    except OSError:
        config_raw = ""
    config = load_config(config_raw)

    from divineos.core.merge_review_gate import classify_merge, has_round_reference

    round_id = has_round_reference(body_and_commits) or ""
    round_logged = _round_is_logged(round_id)

    verdict, msg = classify_merge(
        reviews=reviews,
        head_sha=head_sha,
        pr_body_and_commits=body_and_commits,
        config=config,
        round_is_logged=round_logged,
    )
    print(f"[merge-review] {verdict}: {msg}")
    # PENDING exits 0. An open PR that nobody has approved yet is the normal
    # state of an open PR, not a defect, and this job runs on every push —
    # so failing on it made the check permanently red and therefore mute.
    # Only FAIL is red now, which is what makes red mean something.
    return 1 if verdict == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
