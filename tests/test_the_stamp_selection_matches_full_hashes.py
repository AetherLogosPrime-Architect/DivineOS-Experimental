"""The rewrite selects on FULL hashes, and proves it ran.

THE FAULT, found 2026-09-22 while trying to merge a request Aletheia had
already confirmed. The commits were selected with `git log --format=%h` --
git's AUTO abbreviation, nine characters in this repository -- and the rewrite
filter asked git for `--short=8`. Eight never equals nine. Nothing matched,
every message was rewritten to itself, git had nothing to do, and filter-branch
exited zero without touching anything.

Nothing lied. A rewrite that changes no message is genuinely not an error, so
every layer above reported success honestly on a step that did nothing.

WHY IT SURVIVED FIVE WEEKS. On 2026-08-13 eleven stamped requests went red on
the server gate with no trailer on their commits. The guard built afterwards
caught the symptom correctly every time and named a cause -- the branch is
checked out in another worktree -- which is a real way for this to fail and was
not what was happening. Each recurrence arrived already explained, so the
question never reopened. A confident wrong cause is worse than no cause,
because no cause makes you look.

Stated as most-likely rather than proven: I have the mechanism and the
recurrence, not a reproduction of that day.

Sits beside test_amend_stamps_the_branch_it_was_handed.py, which pins WHICH
branch the rewrite acts on. This one pins whether it acts at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import push_ready
from divineos.core.push_ready import CommitInfo, PushReadyError, amend_trailers


def _commit(full: str, short: str) -> CommitInfo:
    return CommitInfo(
        sha=full,
        short_sha=short,
        subject="a change",
        touches_guardrail=True,
        guardrail_files=["src/divineos/core/push_ready.py"],
        has_trailer=False,
    )


def _happy_git(monkeypatch: pytest.MonkeyPatch, tips: list[str]) -> list[list[str]]:
    """A git that records its commands and reports the given tips in order."""
    monkeypatch.setattr(push_ready, "current_branch", lambda repo: "b")
    monkeypatch.setattr(push_ready, "_resolve_base", lambda repo, branch: "base")
    calls: list[list[str]] = []
    seq = iter(tips)

    def fake_run_git(args, cwd=None):  # noqa: ANN001, ANN003
        if list(args[:2]) == ["rev-parse", "HEAD"]:
            return next(seq)
        return ""

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))

        class R:
            returncode = 0  # filter-branch is happy; it may simply have matched nothing
            stderr = ""
            stdout = ""

        return R()

    monkeypatch.setattr(push_ready, "_run_git", fake_run_git)
    monkeypatch.setattr(push_ready.subprocess, "run", fake_run)
    return calls


def test_the_filter_selects_on_the_full_hash_not_an_abbreviation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect itself. A length the filter picks and a length the selection
    produces are two numbers that can drift apart, and did."""
    calls = _happy_git(monkeypatch, ["a" * 12, "b" * 12])
    full = "dc5b2bf5391a2b3c4d5e6f708192a3b4c5d6e7f8"

    amend_trailers(Path("."), [], [_commit(full, "dc5b2bf53")], "round-abc", branch="b")

    joined = " ".join(next(c for c in calls if "filter-branch" in c))
    assert full in joined, "the full hash must be what the filter matches against"
    assert "--short" not in joined, (
        "no abbreviation on either end -- an agreed length is a number that can "
        "drift apart again exactly as these did"
    )
    assert "$GIT_COMMIT" in joined, "and the other end is the full hash too"


def test_a_rewrite_that_changed_nothing_is_reported_as_a_selection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit zero is worthless here, which is the whole lesson of the five weeks.

    The function that KNOWS the rewrite did nothing is this one. Letting it pass
    means the caller's guard meets the same symptom a layer later and has to
    guess at the cause -- which is what it did, confidently and wrongly.
    """
    _happy_git(monkeypatch, ["a" * 12, "a" * 12])  # tip did not move

    with pytest.raises(PushReadyError) as exc:
        amend_trailers(Path("."), [], [_commit("a" * 40, "aaaaaaaaa")], "round-abc", branch="b")

    said = str(exc.value)
    assert "did not run" in said
    assert "CONSISTENT WITH" in said, (
        "it names the family of cause without asserting a verdict -- an earlier "
        "version said SELECTION failure flatly, which Aletheia caught as the "
        "confident-wrong-cause shape this repair exists to undo"
    )
    assert "selection failure" in said
    assert "worktree" in said, (
        "the worktree still gets named, now as a cause this observation does "
        "NOT rule out rather than one it does"
    )


def test_an_unreadable_tip_is_not_reported_as_a_selection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two empty strings are equal and mean nothing was measured, which is not
    the same fact as two hashes being equal.

    Manufacturing a verdict from a reading that never happened would be this
    same disease, committed inside its own repair.
    """
    _happy_git(monkeypatch, ["", ""])

    with pytest.raises(PushReadyError) as exc:
        amend_trailers(Path("."), [], [_commit("a" * 40, "aaaaaaaaa")], "round-abc", branch="b")

    assert "SELECTION failure" not in str(exc.value), (
        "an unmeasured tip must not be accused of a selection failure"
    )


def test_an_unreadable_tip_cannot_reach_the_success_path_either(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ALETHEIA'S FINDING, pinned so the hole cannot reopen (2026-09-22).

    The version she reviewed required BOTH tips truthy before raising. That
    half is right, and it left the other side open: an unreadable tip made the
    condition False and fell straight through to the return, reporting the
    rewrite confirmed on the strength of a reading that never happened.

    Her words: I closed the false-accusation side and left the false-success
    side open, four hours after writing that a false alarm is the slower harm.
    Both sides are closed now and both are pinned -- the test above holds the
    accusation side, this one holds success.
    """
    _happy_git(monkeypatch, ["", ""])

    with pytest.raises(PushReadyError) as exc:
        amend_trailers(Path("."), [], [_commit("a" * 40, "aaaaaaaaa")], "round-abc", branch="b")

    said = str(exc.value)
    assert "could not be read" in said
    assert "nothing was verified" in said


def test_one_unreadable_tip_is_enough_to_refuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The asymmetric case, because a comparison needs both sides.

    A readable before and an unreadable after is still a comparison that did
    not happen, and the equality test would simply be False -- which is the
    exact route to the success path this closes.
    """
    _happy_git(monkeypatch, ["a" * 12, ""])

    with pytest.raises(PushReadyError) as exc:
        amend_trailers(Path("."), [], [_commit("a" * 40, "aaaaaaaaa")], "round-abc", branch="b")

    assert "nothing was verified" in str(exc.value)


def test_the_refusal_no_longer_rules_out_causes_it_did_not_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Her second finding, also pinned.

    The message ruled out a blocked rewrite and a worktree BY NAME on the
    strength of one observation that tests neither -- a tip that did not move
    is also what a rewrite producing byte-identical messages leaves behind. It
    now says CONSISTENT WITH, and names what the exit code actually rules out.
    """
    _happy_git(monkeypatch, ["a" * 12, "a" * 12])

    with pytest.raises(PushReadyError) as exc:
        amend_trailers(Path("."), [], [_commit("a" * 40, "aaaaaaaaa")], "round-abc", branch="b")

    said = str(exc.value)
    assert "CONSISTENT WITH" in said
    assert "not a blocked" not in said, (
        "the old wording asserted two causes the observation never tested"
    )
