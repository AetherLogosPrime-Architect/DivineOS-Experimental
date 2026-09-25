"""stamp-ready's freshness preflight must measure the PR's branch, not HEAD.

CAUGHT 2026-08-21 on PR #412, by hand, after the gate refused to stamp a
branch that was zero commits behind origin/main. It had just been merged
forward and pushed, and both facts were verified against the remote. The
refusal said "3 commit(s) behind origin/main".

The preflight compared ``HEAD..origin/main``. HEAD is whatever branch the
invoking checkout happens to be standing on -- and for a PR command that is
almost never the PR's branch. The main checkout sat on an unrelated branch
that genuinely was 3 behind, so the gate reported a true number about the
wrong subject and blocked a merge on it. Measured side by side at the time:

    HEAD..origin/main                                      3   <- used
    origin/split/ci-merge-review-visibility..origin/main    0   <- correct

tests/test_merge_stamp.py passed throughout and contains no mention of
_commits_behind_base, "behind" or "freshness" -- the preflight had no
coverage at all. That is the third instance this session of a guard that
still runs, still passes its tests, and no longer guards what its name
claims, after the monitor's discarded mutex handle and the read-gate's
disarmed throttle.

It is also a second instance of claim-795eacd8: a verdict that comes from the
checkout rather than from the data.

These tests build a real repository with a real remote, because the function
under test shells out to git and the whole defect is about which ref it names.
A mock would assert my model of git rather than git.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.cli.stamp_ready_command import _commits_behind_base


def _git(cwd, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def _commit(cwd, message: str, name: str, body: str) -> None:
    (cwd / name).write_text(body, encoding="utf-8")
    _git(cwd, "add", name)
    _git(cwd, "commit", "-q", "-m", message)


@pytest.fixture
def repo_with_remote(tmp_path, monkeypatch):
    """A clone whose origin has main ahead, and a feature branch fully caught up.

    The shape that exposed the defect: the FEATURE branch contains everything
    on main, while the checkout's HEAD sits on a different branch that does not.
    """
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--quiet", "--bare", "--initial-branch=main")

    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "--quiet", "--initial-branch=main")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _git(work, "remote", "add", "origin", str(origin))

    _commit(work, "base", "a.txt", "1")
    _git(work, "push", "--quiet", "-u", "origin", "main")

    # feature: branches from main, then merges main forward -> 0 behind.
    _git(work, "checkout", "--quiet", "-b", "feature")
    _commit(work, "feature work", "b.txt", "1")
    _git(work, "checkout", "--quiet", "main")
    _commit(work, "main moves on", "c.txt", "1")
    _git(work, "push", "--quiet", "origin", "main")
    _git(work, "checkout", "--quiet", "feature")
    _git(work, "merge", "--quiet", "--no-edit", "main")
    _git(work, "push", "--quiet", "-u", "origin", "feature")

    # stale: the branch the checkout is left standing on. Genuinely behind.
    _git(work, "checkout", "--quiet", "-b", "stale", "main~1")
    _git(work, "push", "--quiet", "-u", "origin", "stale")

    _git(work, "fetch", "--quiet", "origin")
    monkeypatch.chdir(work)
    return work


def test_a_caught_up_branch_reads_zero_even_from_a_stale_checkout(repo_with_remote):
    """The exact #412 failure. HEAD is behind; the PR's branch is not."""
    head_branch = _git(repo_with_remote, "branch", "--show-current")
    assert head_branch == "stale", "fixture must leave HEAD on the stale branch"

    head_behind = int(_git(repo_with_remote, "rev-list", "--count", "HEAD..origin/main"))
    assert head_behind > 0, "fixture must have HEAD genuinely behind, or it proves nothing"

    behind, why = _commits_behind_base("feature")

    assert why == "", f"should have been determinable: {why}"
    assert behind == 0, (
        "the preflight measured the checkout's HEAD rather than the PR's branch. "
        f"HEAD is {head_behind} behind and 'feature' is 0 behind; it returned {behind}. "
        "A true number about the wrong subject still blocks the wrong merge."
    )


def test_a_genuinely_behind_branch_still_reports_behind(repo_with_remote):
    """The narrowing removes no coverage: a real stale branch must still block."""
    behind, why = _commits_behind_base("stale")

    assert why == "", f"should have been determinable: {why}"
    assert behind > 0, "a branch that really is behind must still be reported behind"


def test_an_unpushed_branch_is_unknown_rather_than_zero(repo_with_remote):
    """Unknown must not read as safe when the next step rewrites history.

    Returning 0 here would let stamping proceed on a branch whose freshness was
    never established -- the could-not-check / would-be-refused collapse this
    function's docstring already warns about.
    """
    behind, why = _commits_behind_base("no-such-branch")

    assert behind == 0
    assert why, "an unresolvable branch must come back with a reason, not a clean zero"


def test_an_empty_branch_name_is_unknown(repo_with_remote):
    """Guards the caller passing through an unresolved branch."""
    behind, why = _commits_behind_base("")

    assert behind == 0
    assert why
