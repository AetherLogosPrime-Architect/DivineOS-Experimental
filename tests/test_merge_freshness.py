"""A merge of a pull request that is behind main is refused, with the remedy.

Aletheia 2026-10-18: the stamp's refusal of a behind-main branch was the only thing
stopping a merge on checks that ran against an older main. GitHub does not stop it
either (the ruleset's strict_required_status_checks_policy is false, measured the same
night), so the refusal has to live somewhere. It lives here, at the merge command.

`gh` is the only thing stood in for: the reading, the wording and the decision are the real
code. Three states are kept apart, and could-not-look is a refusal, never a pass.
"""

from __future__ import annotations

import json
import subprocess

from divineos.core import hook_surfaces as hs
from divineos.core import merge_freshness as mf


def _done(stdout: str = "", code: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def _gh(view: subprocess.CompletedProcess, compare: subprocess.CompletedProcess):
    """A stand-in for `gh`: the first call reads the PR, the second compares it with main."""
    answers = [view, compare]
    calls: list[list[str]] = []

    def run(args, **_kwargs):
        calls.append(list(args))
        return answers.pop(0)

    run.calls = calls  # type: ignore[attr-defined]
    return run


VIEW = _done(json.dumps({"baseRefName": "main", "headRefOid": "abc123"}))


def _compare(behind_by: int) -> subprocess.CompletedProcess:
    return _done(json.dumps({"status": "diverged", "behind_by": behind_by, "ahead_by": 2}))


def test_a_pr_that_contains_main_is_fresh():
    run = _gh(VIEW, _compare(0))
    assert mf.block_reason("gh pr merge 42 --squash", run=run) is None


def test_a_pr_behind_main_is_refused_and_told_the_remedy():
    run = _gh(VIEW, _compare(3))
    reason = mf.block_reason("gh pr merge 42 --squash", run=run)
    assert reason is not None
    assert "#42" in reason and "3 commit" in reason
    assert "gh pr update-branch 42" in reason


def test_the_compare_is_asked_about_the_head_the_pr_has_now():
    run = _gh(VIEW, _compare(0))
    mf.block_reason("gh pr merge 42", run=run)
    assert "main...abc123" in " ".join(run.calls[1])


def test_when_gh_cannot_be_asked_the_merge_is_refused_and_says_so():
    run = _gh(_done("", code=1), _compare(0))
    reason = mf.block_reason("gh pr merge 42 --squash", run=run)
    assert reason is not None and "could not tell" in reason


def test_a_failed_compare_is_not_a_pass():
    run = _gh(VIEW, _done("", code=1))
    reason = mf.block_reason("gh pr merge 42", run=run)
    assert reason is not None and "could not tell" in reason


def test_an_unreadable_answer_is_not_a_pass():
    run = _gh(VIEW, _done("not json at all"))
    assert mf.block_reason("gh pr merge 42", run=run) is not None


def test_an_answer_without_the_count_is_not_a_pass():
    run = _gh(VIEW, _done(json.dumps({"status": "identical"})))
    assert mf.block_reason("gh pr merge 42", run=run) is not None


def _never(*_a, **_k):
    raise AssertionError("gh must not be asked about a command that is not a merge")


def test_a_command_that_is_not_a_merge_is_not_asked():
    for cmd in ("git status", "gh pr view 42", "gh pr list", "ls -la"):
        assert mf.block_reason(cmd, run=_never) is None, cmd


def test_prose_naming_a_merge_is_not_a_merge():
    assert mf.block_reason('echo "gh pr merge 42 --squash"', run=_never) is None


def test_the_surface_denies_through_json_and_names_the_pr(monkeypatch):
    monkeypatch.setattr(mf, "read_state", lambda pr, run=None: ("behind", 2, ""))
    out = hs.pr_merge_freshness_surface(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 42 --squash"}}
    )
    assert out.refused and out.json_deny and "#42" in out.reason


def test_the_surface_is_quiet_for_other_tools_and_fresh_prs(monkeypatch):
    monkeypatch.setattr(mf, "read_state", lambda pr, run=None: ("fresh", 0, ""))
    assert not hs.pr_merge_freshness_surface({"tool_name": "Read", "tool_input": {}}).refused
    fresh = hs.pr_merge_freshness_surface(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 42 --squash"}}
    )
    assert not fresh.refused


def test_the_surface_is_registered_beside_the_other_merge_gate():
    """The sibling gates shipped once with the function present and the registration absent."""
    from divineos.core.hook_router import registered

    hs.install()
    assert "pr_merge_freshness" in registered("PreToolUse")
