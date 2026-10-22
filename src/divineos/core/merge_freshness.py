"""Refuse a merge of a pull request that is behind main, and hand over the remedy.

Aletheia 2026-10-18, on the stamp retirement (#691): the stamp used to refuse a branch that
was behind main, which was the only thing stopping a merge on checks that ran against an
older main. I said GitHub's own rule covered it, and I measured, and it does not: the
ruleset "main protection" requires `multi-party-review`, `test (3.12)` and
`test (3.12, sklearn)` but has `strict_required_status_checks_policy: false`. So the refusal
lives here, at the merge command, where nothing can merge around it.

The remedy is `gh pr update-branch N`: GitHub merges main into the PR branch and reruns the
required checks on its own servers. That costs no local test suite and no new signature,
because a review follows the change and not the floor. If main moves again before the merge,
the gate refuses again, which costs one more rerun and never a signature.

Three states, kept apart on purpose: fresh (the merge may go on), behind (refused, remedy
named), could-not-look (refused, and says so). An unreadable check is never read as a pass:
the merge itself needs the network, so a refusal here costs a retry and nothing else.

WHICH MERGES IT SEES is not decided here. ``core/merge_command.py`` reads a shell command and
returns every merge it performs, by `gh pr merge` in any spelling or by the direct API call,
and this module only asks GitHub about each one. Aria's cold read found flag-first, probing
found the chained pair, and Aletheia held #692 for the API door and the program named by a
path; those holes are closed once, in the reader, for every gate that uses it.

Not here: running `update-branch` for me. That is the automation a later doorman could add;
a gate firing is a finding, and this one names what to do.
"""

from __future__ import annotations

import json
import re
import subprocess

from divineos.core.merge_command import merge_targets

_REPO_SHAPE = re.compile(r"^(?:[\w.-]+/)?[\w.-]+/[\w.-]+$")

FRESH = "fresh"
BEHIND = "behind"
COULD_NOT_LOOK = "could-not-look"


def _ask(args: list[str], run) -> tuple[dict | None, str]:
    """(parsed answer, why not). `gh` printing JSON is the only shape accepted."""
    try:
        done = run(args, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if done.returncode != 0:
        return None, f"gh exited {done.returncode}"
    try:
        data = json.loads(done.stdout)
    except (json.JSONDecodeError, TypeError):
        return None, "gh printed something that is not JSON"
    if not isinstance(data, dict):
        return None, "gh printed JSON that is not an object"
    return data, ""


def read_state(
    selector: str, repo: str = "", run=subprocess.run
) -> tuple[str, int, str, int | None]:
    """(state, commits behind, why it could not be read, the PR's number) for ``selector``."""
    if repo and (not _REPO_SHAPE.match(repo) or {".", ".."} & set(repo.split("/"))):
        # Typed text reaches gh and an API path, so only owner/repo (or host/owner/repo) goes on.
        why = f"the repository flag names {repo!r}, which is not owner/repo"
        return COULD_NOT_LOOK, 0, why, None
    args = [
        "gh",
        "pr",
        "view",
        *([selector] if selector else []),
        *(["--repo", repo] if repo else []),
    ]
    view, why = _ask([*args, "--json", "number,baseRefName,headRefOid"], run)
    if view is None:
        return COULD_NOT_LOOK, 0, f"reading the pull request: {why}", None
    number, base, head = view.get("number"), view.get("baseRefName"), view.get("headRefOid")
    if not isinstance(number, int) or not base or not head:
        return COULD_NOT_LOOK, 0, "the pull request names no number, base branch or head", None
    where = repo or "{owner}/{repo}"
    compare, why = _ask(["gh", "api", f"repos/{where}/compare/{base}...{head}"], run)
    if compare is None:
        return COULD_NOT_LOOK, 0, f"comparing it with {base}: {why}", number
    behind = compare.get("behind_by")
    if not isinstance(behind, int) or isinstance(behind, bool):
        return (
            COULD_NOT_LOOK,
            0,
            f"the comparison with {base} carries no count of commits behind",
            number,
        )
    return (BEHIND if behind > 0 else FRESH), behind, "", number


def _refusal(number: int | None, state: str, behind: int, why: str, repo: str = "") -> str:
    which = f"PR #{number}" if number is not None else "this pull request"
    if state == COULD_NOT_LOOK:
        return (
            f"BLOCKED: could not tell whether {which} is up to date with main ({why}), "
            "and an unreadable check is not a pass. Run the merge again; if it keeps failing, "
            "look by hand: gh api repos/{owner}/{repo}/compare/main...<head> and read behind_by."
        )
    named = f" -R {repo}" if repo else ""
    return (
        f"BLOCKED: {which} is {behind} commit(s) behind main, so its required checks ran "
        "against an older main than the one this merge lands on, and GitHub will not stop it "
        "(the ruleset's strict up-to-date policy is off, measured 2026-10-18).\n\n"
        f"  Bring it up to date on GitHub, which reruns the checks there:\n"
        f"      gh pr update-branch {number}{named}\n"
        "  Then wait for the checks to go green and merge again. Your review line and "
        "Aletheia's confirm follow the change, not the floor, so they still hold."
    )


def block_reason(bash_command: str, run=subprocess.run) -> str | None:
    """A refusal if ``bash_command`` merges a pull request that is behind main, else None.

    EVERY merge in the command is asked about, not the first: `gh pr merge 1 && gh pr merge 2`
    is an ordinary way to merge two, and a stale second one must not ride behind a fresh first.
    """
    for target in merge_targets(bash_command):
        state, behind, why, number = read_state(target.selector, target.repo, run=run)
        if state != FRESH:
            return _refusal(number, state, behind, why, target.repo)
    return None
