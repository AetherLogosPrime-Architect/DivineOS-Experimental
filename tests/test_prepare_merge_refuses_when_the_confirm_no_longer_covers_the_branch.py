"""`audit prepare-merge` refuses when the external confirm no longer covers the branch.

2026-11-19, Aletheia: seven of seventeen notes (#793, #794, #796, #798, #799, #818, #819) moved to new versions
after her yes and merged without coming back. Measured: every one named a round whose export was absent from
main, so CI could only say "unverifiable" and pass; and prepare-merge, the step that hands the squash text
over, validated that the confirms EXISTED but never asked whether they still covered the branch. The helper
that answers that (`anchor_state_for_round`) already existed and was used only by the build board.

Real git throughout (a bare remote, a branch, a real patch-id): the cases are Aletheia's: a branch edited after
her yes is REFUSED; a branch merely caught up with main still HOLDS (patch-id is the invariant, the tree is not,
Einstein); a confirm with no anchor WARNS (it cannot say either way); an unreadable branch WARNS as
could-not-check, which is not a pass (Hoare). Walk walk-37d51e46fa38.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.cli.audit_commands import (
    anchor_state_for_round,
    compute_branch_patch_id,
    resolve_pr_head,
)


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A bare 'origin', a clone with main pushed and a 'feature' branch pushed, cwd inside the clone."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")
    work = tmp_path / "work"
    _git(tmp_path, "clone", str(origin), str(work))
    (work / "base.txt").write_text("base\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "base")
    _git(work, "push", "origin", "HEAD:main")
    _git(work, "checkout", "-b", "feature")
    (work / "change.txt").write_text("the reviewed change\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "the change")
    _git(work, "push", "origin", "feature")
    _git(work, "fetch", "origin")
    monkeypatch.chdir(work)
    return work


@dataclass
class _Round:
    round_id: str = "round-fake12345"
    focus: str = "test round"
    created_at: float = 0.0


@dataclass
class _Finding:
    actor: str
    title: str = "CONFIRMS: the change"
    description: str = ""
    review_stance: object = None


def _anchors(work: Path) -> str:
    tree = _git(work, "rev-parse", "origin/feature^{tree}")
    pid = compute_branch_patch_id("origin/feature", "origin/main")
    return f"Tree {tree} patch-id {pid} git-version 2.45.0"


def _findings(description: str):
    return [_Finding(actor="user"), _Finding(actor="aletheia", description=description)]


def _state(findings, branch="feature"):
    with patch("divineos.core.watchmen.store.list_findings", return_value=findings):
        return anchor_state_for_round("round-fake12345", branch)


def _github_says(work: Path, branch: str = "feature", sha: str | None = None):
    """What `gh pr view` would answer for the PR whose head is `branch`: GitHub's own view.

    gh is not in a test run, so the resolver is patched. The default sha is the real tip of the
    branch on the real bare remote, which is what GitHub would report.
    """
    head = sha or _git(work, "rev-parse", f"origin/{branch}")
    return (("864", branch, head), "")


def _prepare(findings, *extra: str, github=None, work: Path | None = None):
    """Run prepare-merge with the PR resolver patched to `github` (or to the real feature head)."""
    answer = github if github is not None else _github_says(work)
    with (
        patch(
            "divineos.core.watchmen.store.get_round",
            return_value=_Round(created_at=time.time() - 3600),
        ),
        patch("divineos.core.watchmen.store.list_findings", return_value=findings),
        patch("divineos.cli.audit_commands.resolve_pr_head", return_value=answer),
    ):
        return CliRunner().invoke(cli, ["audit", "prepare-merge", "round-fake12345", *extra])


def _edit_after_the_confirm(work: Path) -> None:
    (work / "change.txt").write_text("the change, edited after her yes\n", encoding="utf-8")
    _git(work, "commit", "-am", "edit after the confirm")
    _git(work, "push", "origin", "feature")


# --- the helper's four states, on real git -----------------------------------------------------


def test_an_unchanged_branch_holds(repo):
    assert _state(_findings(_anchors(repo)))[0] == "holds"


def test_a_branch_edited_after_the_confirm_is_stale(repo):
    anchors = _anchors(repo)
    _edit_after_the_confirm(repo)
    assert _state(_findings(anchors))[0] == "stale"


def test_a_clean_catch_up_with_main_still_holds_because_the_change_is_the_same(repo):
    anchors = _anchors(repo)
    _git(repo, "checkout", "main")
    (repo / "elsewhere.txt").write_text("unrelated work on main\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "main moves")
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "feature")
    _git(repo, "merge", "main", "-m", "catch up")
    _git(repo, "push", "origin", "feature")
    _git(repo, "fetch", "origin")
    # the tree moved, the reviewed change did not
    assert _git(repo, "rev-parse", "origin/feature^{tree}") not in anchors
    assert _state(_findings(anchors))[0] == "holds"


def test_a_confirm_with_no_anchor_is_unanchored_not_stale(repo):
    assert _state(_findings("Looks right to me."))[0] == "unanchored"


def test_a_branch_that_cannot_be_read_is_cannot_check_not_a_pass(repo):
    assert _state(_findings(_anchors(repo)), branch="no-such-branch")[0] == "cannot-check"


# --- prepare-merge itself ----------------------------------------------------------------------


def test_prepare_merge_refuses_a_stale_confirm_and_names_the_remedy(repo):
    anchors = _anchors(repo)
    _edit_after_the_confirm(repo)

    result = _prepare(_findings(anchors), "--branch", "feature", work=repo)

    assert result.exit_code == 1, result.output
    assert "MOVED" in result.output
    assert "file-external-confirm" in result.output
    assert "External-Review:" not in result.output  # no merge text is handed over


def test_prepare_merge_hands_over_the_text_when_the_confirm_holds(repo):
    result = _prepare(_findings(_anchors(repo)), "--branch", "feature", work=repo)
    assert result.exit_code == 0, result.output
    assert "External-Review: round-fake12345" in result.output
    assert (
        "Reviewed PR #864 at " in result.output
    )  # the PR the text was prepared for survives the paste


def test_prepare_merge_says_so_loudly_when_the_confirm_is_not_bound_to_a_version(repo):
    result = _prepare(_findings("Looks right to me."), "--branch", "feature", work=repo)
    assert result.exit_code == 0, result.output
    assert "NOT BOUND" in result.output
    assert "External-Review: round-fake12345" in result.output


def test_the_text_says_it_does_not_see_a_hand_merge(repo):
    result = _prepare(_findings(_anchors(repo)), work=repo)
    assert result.exit_code == 0, result.output
    assert "does not see a merge written by hand" in result.output


# --- Aletheia's kicks at #864 (2026-11-19), each flipped to expect REFUSAL -----------------------


def test_ATTACK_wrong_branch_name_on_a_stale_pr_is_refused(repo):
    anchors = _anchors(repo)
    _edit_after_the_confirm(repo)
    result = _prepare(_findings(anchors), "--branch", "typo-or-on-purpose", work=repo)
    assert result.exit_code == 1, result.output
    assert "is not the head of PR #864" in result.output
    assert "External-Review:" not in result.output


def test_ATTACK_untouched_copy_branch_cannot_vouch_for_a_moved_pr(repo):
    anchors = _anchors(repo)
    _git(repo, "push", "origin", "feature:feature-as-she-saw-it")
    _edit_after_the_confirm(repo)
    # naming the copy is refused outright, and not naming it checks the PR GitHub names: also refused
    named = _prepare(_findings(anchors), "--branch", "feature-as-she-saw-it", work=repo)
    unnamed = _prepare(_findings(anchors), work=repo)
    assert named.exit_code == 1, named.output
    assert unnamed.exit_code == 1, unnamed.output
    assert "MOVED" in unnamed.output
    assert "External-Review:" not in named.output + unnamed.output


def test_ATTACK_detached_head_with_no_pr_found_is_refused(repo):
    anchors = _anchors(repo)
    _edit_after_the_confirm(repo)
    _git(repo, "checkout", "--detach")
    result = _prepare(
        _findings(anchors), github=(None, "gh could not name a pull request (detached head)")
    )
    assert result.exit_code == 1, result.output
    assert "COULD NOT NAME THE PULL REQUEST" in result.output
    assert "External-Review:" not in result.output


def test_ATTACK_edit_hidden_in_a_catch_up_merge_commit_is_refused(repo):
    anchors = _anchors(repo)
    _git(repo, "checkout", "main")
    (repo / "m.txt").write_text("main moved\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "m")
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "feature")
    _git(repo, "merge", "--no-commit", "main")
    (repo / "change.txt").write_text("smuggled edit\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Merge main")
    _git(repo, "push", "origin", "feature")
    _git(repo, "fetch", "origin")
    result = _prepare(_findings(anchors), "--branch", "feature", work=repo)
    assert result.exit_code == 1, result.output


# --- what else refuses: a check the tool cannot make is never a pass -----------------------------


def test_a_branch_that_cannot_be_read_refuses_and_hands_nothing_over(repo):
    github = (("864", "no-such-branch", "a" * 40), "")
    result = _prepare(_findings(_anchors(repo)), github=github)
    assert result.exit_code == 1, result.output
    assert "COULD NOT CHECK" in result.output
    assert "External-Review:" not in result.output


def test_the_fetched_tip_must_be_the_head_github_names(repo):
    # the confirm holds for the branch as fetched, but GitHub says the PR's head is a different commit
    github = _github_says(repo, sha="b" * 40)
    result = _prepare(_findings(_anchors(repo)), github=github)
    assert result.exit_code == 1, result.output
    assert "is not the head GitHub names" in result.output
    assert "External-Review:" not in result.output


# --- resolve_pr_head: what gh may answer, and which answers are a refusal ---------------------------


def _gh_answers(raw):
    return patch("divineos.cli.audit_commands._git_capture", return_value=raw)


def test_gh_naming_an_open_pr_is_read_as_number_branch_and_head():
    raw = (
        '{"number": 864, "headRefName": "feature", "headRefOid": "'
        + "c" * 40
        + '", "state": "OPEN"}'
    )
    with _gh_answers(raw):
        assert resolve_pr_head("864") == (("864", "feature", "c" * 40), "")


@pytest.mark.parametrize(
    "raw",
    [
        None,  # gh failed (not installed, offline, no PR, detached head)
        "",  # gh printed nothing
        "not json at all",
        '{"headRefName": "feature", "headRefOid": "'
        + "c" * 40
        + '", "state": "OPEN"}',  # no number
        '{"number": 864, "headRefName": "feature", "headRefOid": "", "state": "OPEN"}',  # no head
        '{"number": 864, "headRefName": "feature", "headRefOid": "'
        + "c" * 40
        + '", "state": "MERGED"}',
        '{"number": 864, "headRefName": "feature", "headRefOid": "'
        + "c" * 40
        + '", "state": "CLOSED"}',
    ],
)
def test_anything_that_is_not_a_clear_open_pr_is_none_never_a_pass(raw):
    with _gh_answers(raw):
        answer, why = resolve_pr_head(None)
    assert answer is None
    assert why
