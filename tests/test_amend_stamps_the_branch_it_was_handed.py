"""The amend rewrites HEAD, so it can only honestly act on the checkout.

Written 2026-09-05, after stamping a request from a checkout of a different
branch. The caller selected commits from one branch and handed them to an
amend that recomputed the branch from the working tree, so the rewrite ran
against whichever branch happened to be checked out. Nothing was stamped,
the amend reported success, and the guard downstream named a worktree that
was not the cause.

The repair is a refusal rather than a redirection. A rewrite of HEAD cannot
reach another branch, so silently retargeting would be the same wrong-subject
fault wearing a fix. Naming the mismatch tells the caller what to do instead.

Same shape as the day's other five: an operation that CAN complete,
completing, on a subject narrower or simply other than the one asked about.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import push_ready
from divineos.core.push_ready import CommitInfo, PushReadyError, amend_trailers


def _commit(sha: str = "aaaaaaaa") -> CommitInfo:
    return CommitInfo(
        sha=sha * 5,
        short_sha=sha,
        subject="a change",
        touches_guardrail=True,
        guardrail_files=["src/divineos/core/push_ready.py"],
        has_trailer=False,
    )


def test_a_branch_that_is_not_checked_out_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(push_ready, "current_branch", lambda repo: "some/other-branch")
    with pytest.raises(PushReadyError) as exc:
        amend_trailers(Path("."), [], [_commit()], "round-abc", branch="the/target-branch")
    message = str(exc.value)
    assert "the/target-branch" in message
    assert "some/other-branch" in message


def test_the_refusal_names_both_branches_not_just_the_failure() -> None:
    """A caller told only that it failed cannot tell which branch to check out.

    Asserted separately from the raise because the useful half of this
    refusal is the diagnosis, and a message that said only 'cannot stamp'
    would pass a test that checked only for the exception.
    """
    with pytest.raises(PushReadyError) as exc:
        amend_trailers(
            Path("."),
            [],
            [_commit()],
            "round-abc",
            branch="definitely/not-checked-out-xyz",
        )
    assert "re-run" in str(exc.value).lower()


def test_no_branch_argument_keeps_acting_on_the_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old call shape stays valid: no branch means the checkout is the subject.

    Guarded because the repair must not turn every existing caller into a
    refusal — the fault was a MISMATCH going unnoticed, not the use of the
    checkout.
    """
    monkeypatch.setattr(push_ready, "current_branch", lambda repo: "whatever")
    monkeypatch.setattr(push_ready, "_resolve_base", lambda repo, branch: "base")
    seen: dict[str, object] = {}

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        seen["cmd"] = cmd

        class R:
            returncode = 0
            stderr = ""
            stdout = ""

        return R()

    monkeypatch.setattr(push_ready.subprocess, "run", fake_run)
    out = amend_trailers(Path("."), [], [_commit()], "round-abc")
    assert out  # it proceeded rather than refusing
    assert "filter-branch" in seen["cmd"]


def test_a_matching_branch_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """The check must not block the case it was built to protect."""
    monkeypatch.setattr(push_ready, "current_branch", lambda repo: "the/target-branch")
    monkeypatch.setattr(push_ready, "_resolve_base", lambda repo, branch: "base")

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        class R:
            returncode = 0
            stderr = ""
            stdout = ""

        return R()

    monkeypatch.setattr(push_ready.subprocess, "run", fake_run)
    out = amend_trailers(Path("."), [], [_commit()], "round-abc", branch="the/target-branch")
    assert out


def test_nothing_needing_a_trailer_short_circuits_before_the_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty list is not a mismatch. Refusing there would block a no-op."""
    monkeypatch.setattr(push_ready, "current_branch", lambda repo: "some/other-branch")
    assert amend_trailers(Path("."), [], [], "round-abc", branch="the/target") == []
