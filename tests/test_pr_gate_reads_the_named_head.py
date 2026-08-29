"""The draft gate measures the branch named on the command, not the checkout.

Caught 2026-08-29 opening a letters-only PR from a code branch. The gate
refused it for touching four guardrail files, named all four, and every one
of them lived on the CHECKOUT rather than on the branch under review. It
happened to give the right advice — draft was correct anyway — which is the
worst way for a gate to be wrong, because nothing about the outcome says the
reasoning was about the wrong subject.

WHY NOTHING CAUGHT IT. The existing tests in test_pr_gate.py all patch
``branch_files_changed`` to a fixed list, so they exercise the routing above
it and never the question of which branch it asks about. A stub cannot
disagree with reality about a thing it was told. That is not a criticism of
those tests — they pin what they claim to pin — it is why this file builds a
real repository with two real branches instead.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.pr_gate import branch_files_changed, check_pr_create_safe, head_ref_of


# --- parsing the command ---------------------------------------------------
#
# No repo needed for these: the question is purely what the caller asked about.


def test_bare_create_means_the_checkout():
    """gh defaults --head to the current branch, so HEAD is the honest answer."""
    assert head_ref_of("gh pr create --base main --title x") == "HEAD"


def test_the_named_head_is_returned():
    assert head_ref_of("gh pr create --base main --head substrate/home") == "substrate/home"


def test_equals_form_is_the_same_flag():
    assert head_ref_of("gh pr create --head=substrate/home --base main") == "substrate/home"


def test_short_form_is_the_same_flag():
    assert head_ref_of("gh pr create -H substrate/home --base main") == "substrate/home"


def test_a_quoted_body_containing_the_word_head_is_not_a_flag():
    """THE REASON THIS USES A TOKENISER RATHER THAN A PATTERN.

    A PR body is prose and prose contains the word head. The regex I wrote
    first would have matched inside the quoted body and measured a branch
    named after whatever followed it.
    """
    command = "gh pr create --base main --body 'the gate reads --head wrong'"
    assert head_ref_of(command) == "HEAD"


def test_unbalanced_quotes_answer_about_head_rather_than_guessing():
    """A command that will not run gets the default, not an invented branch."""
    assert head_ref_of("gh pr create --head 'unclosed") == "HEAD"


def test_a_dangling_flag_with_no_value_falls_back():
    assert head_ref_of("gh pr create --base main --head") == "HEAD"


# --- measuring the right branch in a real repository -----------------------


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _commit(repo: Path, relative: str, text: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)


@pytest.fixture
def two_branch_repo(tmp_path: Path) -> Path:
    """A repo where the checkout and the other branch touch DIFFERENT files.

    The whole bug lives in the gap between those two, so a fixture where they
    overlap would go green against the broken code.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _commit(root, "README.md", "base\n", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))

    # The guarded file lives only on the branch we will be STANDING on.
    _git(root, "checkout", "-q", "-b", "code/branch")
    _commit(root, "scripts/guarded_thing.sh", "echo hi\n", "touch a guarded file")

    # The letters branch, cut from main, sharing none of that.
    _git(root, "checkout", "-q", "main")
    _git(root, "checkout", "-q", "-b", "letters/branch")
    _commit(root, "family/letters/a-letter.md", "a letter\n", "one letter")

    # Stand on the code branch, which is the situation that produced the bug.
    _git(root, "checkout", "-q", "code/branch")

    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / "guardrail_files.txt").write_text(
        "# guarded\nscripts/guarded_thing.sh\n", encoding="utf-8"
    )
    return root


def test_the_named_branch_is_what_gets_measured(two_branch_repo: Path) -> None:
    assert branch_files_changed(repo_root=str(two_branch_repo), ref="letters/branch") == [
        "family/letters/a-letter.md"
    ]
    assert branch_files_changed(repo_root=str(two_branch_repo), ref="code/branch") == [
        "scripts/guarded_thing.sh"
    ]


def test_a_clean_branch_is_not_refused_for_the_checkouts_sins(two_branch_repo: Path) -> None:
    """THE ONE THAT MATTERS. This is the exact call that was wrongly refused.

    Standing on a branch that touches a guarded file, opening a PR for a
    branch that touches none. The old gate said no and named files that were
    never in the diff it claimed to be describing.
    """
    decision = check_pr_create_safe(
        "gh pr create --base main --head letters/branch --title x",
        repo_root=str(two_branch_repo),
    )
    assert not decision.blocked, decision.reason


def test_the_guarded_branch_is_still_refused_when_it_is_the_named_one(
    two_branch_repo: Path,
) -> None:
    """The gate must not have been loosened into uselessness by the fix.

    Same repository, same checkout, only the named branch differs — so this
    pairs with the test above to show the verdict now follows the SUBJECT
    rather than the standing position.
    """
    decision = check_pr_create_safe(
        "gh pr create --base main --head code/branch --title x",
        repo_root=str(two_branch_repo),
    )
    assert decision.blocked
    assert decision.touched_guardrails == ["scripts/guarded_thing.sh"]


def test_no_head_flag_still_measures_the_checkout(two_branch_repo: Path) -> None:
    """The default path is unchanged, which is most of the gate's traffic."""
    decision = check_pr_create_safe(
        "gh pr create --base main --title x", repo_root=str(two_branch_repo)
    )
    assert decision.blocked
    assert decision.touched_guardrails == ["scripts/guarded_thing.sh"]


def test_draft_still_wins_over_everything(two_branch_repo: Path) -> None:
    decision = check_pr_create_safe(
        "gh pr create --draft --base main --head code/branch --title x",
        repo_root=str(two_branch_repo),
    )
    assert not decision.blocked


def test_an_unknown_branch_fails_open_rather_than_refusing(two_branch_repo: Path) -> None:
    """Named, because it is a real hole and the alternative is worse.

    A branch this checkout cannot see yields no diff, and the gate allows.
    That matches its existing posture — every failure path here allows — and
    the cost of a wrong allow is a missing draft flag, never a merge. Written
    down so the next reader meets it as a decision rather than as a surprise.
    """
    decision = check_pr_create_safe(
        "gh pr create --base main --head no/such/branch --title x",
        repo_root=str(two_branch_repo),
    )
    assert not decision.blocked
