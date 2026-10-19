"""The one reader of what a shell command merges, shared by every gate that guards a merge.

Aletheia 2026-10-18 held #692 for two doors the first reader did not watch: the GitHub API's
direct merge call (`gh api -X PUT repos/o/r/pulls/N/merge`) and the program typed with a path
(`/usr/bin/gh pr merge N`). Aria had found flag-first (`gh pr merge --squash N`) and the
chained pair came from probing. Three gates on one hole is the reason this is one module:
each gate asks "what does this command merge?" and none of them parses a command itself.
"""

from __future__ import annotations

import pytest

from divineos.core.merge_command import MergeTarget, merge_targets


def _one(command: str) -> MergeTarget:
    found = merge_targets(command)
    assert len(found) == 1, (command, found)
    return found[0]


@pytest.mark.parametrize(
    "command, selector, repo",
    [
        ("gh pr merge 42", "42", ""),
        ("gh pr merge 42 --squash", "42", ""),
        ("gh pr merge --squash 42", "42", ""),
        ("gh pr merge -s 42", "42", ""),
        ("gh pr merge --subject fix 42", "42", ""),
        ("gh pr merge #42", "42", ""),
        ("gh pr merge https://github.com/o/r/pull/42", "https://github.com/o/r/pull/42", ""),
        ("gh pr merge my-branch --squash", "my-branch", ""),
        ("gh pr merge --squash", "", ""),
        ("gh pr merge -R o/r 42", "42", "o/r"),
        ("gh pr merge 42 --repo o/r", "42", "o/r"),
        ("gh pr merge --repo=o/r 42", "42", "o/r"),
        ('gh pr merge -R "o/r" 42', "42", "o/r"),
        ("cd x && gh pr merge --squash 42", "42", ""),
        ("GH_TOKEN=x gh pr merge 42", "42", ""),
        ("env gh pr merge 42", "42", ""),
        ("command gh pr merge 42", "42", ""),
    ],
)
def test_a_pr_merge_names_its_pull_request_and_repository(command, selector, repo):
    target = _one(command)
    assert (target.selector, target.repo, target.via) == (selector, repo, "pr"), command


@pytest.mark.parametrize(
    "command",
    [
        "/usr/bin/gh pr merge 42",
        "/c/Program/gh.exe pr merge 42",
        "C:\\tools\\gh.exe pr merge 42",
        "./gh pr merge 42",
        "cd x && /usr/bin/gh pr merge --squash 42",
    ],
)
def test_the_program_may_be_named_by_a_path(command):
    """Aletheia's second door: `/usr/bin/gh pr merge N` was let through."""
    assert _one(command).selector == "42", command


@pytest.mark.parametrize(
    "command, repo",
    [
        ("gh api -X PUT repos/o/r/pulls/692/merge", "o/r"),
        ("gh api -X put repos/o/r/pulls/692/merge", "o/r"),
        ("gh api --method PUT repos/o/r/pulls/692/merge", "o/r"),
        ("gh api --method=PUT repos/o/r/pulls/692/merge", "o/r"),
        ("gh api -XPUT repos/o/r/pulls/692/merge", "o/r"),
        ("gh api -X PUT /repos/o/r/pulls/692/merge", "o/r"),
        ("gh api repos/o/r/pulls/692/merge -X PUT", "o/r"),
        ("gh api -X PUT repos/o/r/pulls/692/merge -f merge_method=squash", "o/r"),
        ("gh api --method PUT -f merge_method=squash repos/o/r/pulls/692/merge", "o/r"),
        ("gh api -X PUT repos/{owner}/{repo}/pulls/692/merge", ""),
        ("/usr/bin/gh api -X PUT repos/o/r/pulls/692/merge", "o/r"),
    ],
)
def test_the_api_route_to_a_merge_is_a_merge(command, repo):
    """Aletheia's first door: the API merges directly, so `gh pr merge` never appears."""
    target = _one(command)
    assert (target.selector, target.repo, target.via) == ("692", repo, "api"), command


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "gh pr view 42",
        "gh pr list",
        "gh api repos/o/r/pulls/692",
        "gh api -X PUT repos/o/r/pulls/692/merge-queue",
        "gh api -X PUT repos/o/r/pulls/692/labels",
        "gh api -X GET repos/o/r/pulls/692/merge",
        "gh api -X PUT repos/o/r/issues/5/merge",
        "gh api user",
        'echo "gh pr merge 42"',
        "echo gh pr merge 42",
        "git log --grep 'gh pr merge 5'",
        'echo "gh api -X PUT repos/o/r/pulls/9/merge"',
    ],
)
def test_commands_that_do_not_merge_are_not_merges(command):
    assert merge_targets(command) == [], command


@pytest.mark.parametrize(
    "command, selector, via",
    [
        ('bash -c "gh pr merge 692 --squash"', "692", "pr"),
        ("sh -c 'gh pr merge 692 --squash'", "692", "pr"),
        ('bash -c "gh pr merge --squash 692"', "692", "pr"),
        ('bash -c "gh api -X PUT repos/o/r/pulls/692/merge"', "692", "api"),
        (
            "sh -c 'gh api --method PUT repos/o/r/pulls/692/merge -f merge_method=squash'",
            "692",
            "api",
        ),
        ('bash -lc "gh pr merge --squash 692"', "692", "pr"),
        ('bash -c "gh pr merge 692" && echo done', "692", "pr"),
        ("(gh pr merge 692)", "692", "pr"),
        ("(cd x && gh pr merge --squash 692)", "692", "pr"),
    ],
)
def test_a_merge_typed_inside_a_shell_wrapper_is_still_a_merge(command, selector, via):
    """Probing the shared reader: the closing quote of a -c body stuck to the last word, and
    `bash -lc` and a subshell were not recognised, so the API route hid inside `bash -c`."""
    target = _one(command)
    assert (target.selector, target.via) == (selector, via), command


def test_every_merge_in_a_chained_command_is_found_in_order():
    found = merge_targets(
        "gh pr merge 1 --squash && gh api -X PUT repos/o/r/pulls/2/merge; gh pr merge 3"
    )
    assert [(t.selector, t.via) for t in found] == [("1", "pr"), ("2", "api"), ("3", "pr")]


def test_a_flag_inside_a_quoted_body_is_text_and_not_a_flag():
    target = _one('gh pr merge --body "-R evil/repo" 42')
    assert (target.selector, target.repo) == ("42", "")


def test_an_unbalanced_quote_still_yields_a_target_for_gh_to_refuse():
    assert merge_targets('gh pr merge "42') != []
