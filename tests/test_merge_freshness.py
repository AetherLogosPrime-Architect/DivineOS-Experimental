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

import pytest

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


VIEW = _done(json.dumps({"number": 42, "baseRefName": "main", "headRefOid": "abc123"}))


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


@pytest.mark.parametrize(
    "command, selector",
    [
        ("gh pr merge --squash 42", "42"),
        ("gh pr merge --admin --squash 42", "42"),
        ("gh pr merge -s 42", "42"),
        ("gh pr merge --subject fix 42", "42"),
        ("gh pr merge --body-file notes.txt 42", "42"),
        ("gh pr merge #42", "42"),
        ("gh pr merge https://github.com/o/r/pull/42", "https://github.com/o/r/pull/42"),
        ("gh pr merge my-branch --squash", "my-branch"),
        ("cd x && gh pr merge --squash 42", "42"),
        ("GH_TOKEN=x gh pr merge --squash 42", "42"),
    ],
)
def test_every_ordinary_way_of_naming_the_pr_is_asked_about(command, selector):
    """Aria's cold read of #692: `gh pr merge --squash 42` named the PR and was not asked."""
    run = _gh(VIEW, _compare(3))
    assert mf.block_reason(command, run=run) is not None, command
    assert run.calls[0][3] == selector, run.calls[0]


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge -R o/r 42",
        "gh pr merge --repo o/r --squash 42",
        "gh pr merge 42 -R o/r",
        "gh pr merge --squash 42 --repo o/r",
        "gh pr merge --repo=o/r 42",
    ],
)
def test_a_repo_flag_names_the_repository_and_is_not_mistaken_for_the_pr(command):
    """Aria's second read of #692: `-R o/r` was read as the pull request, `42 -R o/r` ignored it."""
    run = _gh(VIEW, _compare(3))
    assert mf.block_reason(command, run=run) is not None, command
    view, compare = run.calls
    assert view[3] == "42", view
    assert "--repo" in view and view[view.index("--repo") + 1] == "o/r", view
    assert "repos/o/r/compare/main...abc123" in " ".join(compare), compare


def test_a_quoted_repository_name_is_read_not_blanked():
    """Probing for the walk: the quote scrubber blanked `-R "o/r"` into spaces, which gh refused."""
    run = _gh(VIEW, _compare(3))
    assert mf.block_reason('gh pr merge -R "o/r" 42', run=run) is not None
    assert run.calls[0][run.calls[0].index("--repo") + 1] == "o/r"


@pytest.mark.parametrize("name", ["../x", "o/r/../../z", "o r", "o/r;ls", "$(id)/r", "o"])
def test_a_repository_name_that_is_not_owner_slash_repo_never_reaches_gh(name):
    reason = mf.block_reason(f"gh pr merge 42 -R '{name}'", run=_never)
    assert reason is not None and "could not tell" in reason


def test_a_flag_inside_a_quoted_body_is_not_a_flag():
    run = _gh(VIEW, _compare(3))
    assert mf.block_reason('gh pr merge --body "-R evil/repo" 42', run=run) is not None
    assert "--repo" not in run.calls[0]


def _queue(*answers):
    """A stand-in for `gh` that answers in order, for a command that asks about several PRs."""
    left = list(answers)
    calls: list[list[str]] = []

    def run(args, **_kwargs):
        calls.append(list(args))
        return left.pop(0)

    run.calls = calls  # type: ignore[attr-defined]
    return run


def _view(number: int) -> subprocess.CompletedProcess:
    return _done(
        json.dumps({"number": number, "baseRefName": "main", "headRefOid": f"sha{number}"})
    )


def test_a_stale_second_merge_cannot_ride_behind_a_fresh_first_one():
    """Found probing the parser: only the first `gh pr merge` in a chained command was read."""
    run = _queue(_view(1), _compare(0), _view(2), _compare(4))
    reason = mf.block_reason("gh pr merge 1 --squash && gh pr merge 2 --squash", run=run)
    assert reason is not None and "#2" in reason and "gh pr update-branch 2" in reason


def test_two_fresh_merges_in_one_command_both_pass():
    run = _queue(_view(1), _compare(0), _view(2), _compare(0))
    assert mf.block_reason("gh pr merge 1 --squash; gh pr merge 2 --squash", run=run) is None
    assert len(run.calls) == 4


def test_the_first_stale_merge_stops_the_chain_without_asking_about_the_rest():
    run = _queue(_view(1), _compare(2))
    reason = mf.block_reason("gh pr merge 1 && gh pr merge 2", run=run)
    assert "#1" in reason and len(run.calls) == 2


def test_a_bare_merge_asks_about_the_pr_of_the_checked_out_branch():
    run = _gh(VIEW, _compare(3))
    assert mf.block_reason("gh pr merge --squash", run=run) is not None
    assert run.calls[0][3] == "--json", run.calls[0]  # no selector, so gh reads the current branch


def test_the_pr_is_named_by_the_number_github_returns_not_by_the_text_typed():
    run = _gh(
        _done(json.dumps({"number": 7, "baseRefName": "main", "headRefOid": "abc"})), _compare(1)
    )
    reason = mf.block_reason("gh pr merge my-branch", run=run)
    assert "#7" in reason and "gh pr update-branch 7" in reason


def _never(*_a, **_k):
    raise AssertionError("gh must not be asked about a command that is not a merge")


def test_a_command_that_is_not_a_merge_is_not_asked():
    for cmd in ("git status", "gh pr view 42", "gh pr list", "ls -la"):
        assert mf.block_reason(cmd, run=_never) is None, cmd


def test_prose_naming_a_merge_is_not_a_merge():
    assert mf.block_reason('echo "gh pr merge 42 --squash"', run=_never) is None


def test_the_surface_denies_through_json_and_names_the_pr(monkeypatch):
    monkeypatch.setattr(mf, "read_state", lambda sel, repo="", run=None: ("behind", 2, "", 42))
    out = hs.pr_merge_freshness_surface(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 42 --squash"}}
    )
    assert out.refused and out.json_deny and "#42" in out.reason


def test_the_surface_is_quiet_for_other_tools_and_fresh_prs(monkeypatch):
    monkeypatch.setattr(mf, "read_state", lambda sel, repo="", run=None: ("fresh", 0, "", 42))
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
