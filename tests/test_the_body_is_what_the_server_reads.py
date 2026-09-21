"""Unstamped branch commits must not abort a stamp; an unwritten body must.

THE DEFECT, 2026-09-21. Andrew confirmed a piece of work for merge and it
could not be taken out of draft. The stamping command refused because two old
commits on the branch carried no External-Review trailer, tried to rewrite
them to add it, the rewrite silently did nothing, and the command correctly
declined to go further rather than mark something ready over work it believed
unstamped.

WHY THE REFUSAL WAS WRONG, from this repository's own record rather than my
judgement. The per-commit requirement was added 2026-08-13 after eleven
stamped requests went red on the server check. It was then REMOVED from that
server check, and the workflow says why in its own margin: the branch
satisfies the check through the request body, which is editable and fetched
live -- and per-commit trailers were "unmeetable on a branch (amend,
force-push, worktrees where filter-branch cannot rewrite history)". That is
this incident, predicted, in the file that stopped requiring it. The server
moved; the stamping command did not.

A squash merge makes this decisive: main receives ONE commit whose message is
the request title and body. The branch commits never reach main individually,
so a trailer on them is read by nobody. The body is what the server reads.

WHAT MUST NOT BE LOST. The refusal existed to stop a request going ready with
no review anywhere. That protection moves rather than disappears: an unwritten
body, or a round without both confirms, still aborts. Only the commit-level
demand is dropped.

THE TEST THAT CARRIES THE CLAIM is the last one. Every case above it passes if
the decision simply stops aborting for any reason at all -- which would be the
over-correction that trades a too-strict gate for no gate. Asserting the
outcomes stay DISTINCT is what keeps four states four.
"""

from __future__ import annotations

from divineos.cli.stamp_ready_command import stamp_abort_reason


class TestWhatAbortsAStamp:
    def test_unstamped_commits_alone_do_not_abort(self) -> None:
        """The incident. Two commits without the trailer, everything else fine."""
        assert (
            stamp_abort_reason(round_confirmed=True, body_written=True, commits_unstamped=2) is None
        )

    def test_a_great_many_unstamped_commits_still_do_not_abort(self) -> None:
        """The count was never the question -- who reads them was."""
        assert (
            stamp_abort_reason(round_confirmed=True, body_written=True, commits_unstamped=99)
            is None
        )

    def test_an_unwritten_body_aborts(self) -> None:
        """The body IS the review as far as the server is concerned.

        Clearing draft without it leaves a request that can be merged with no
        review reachable by anyone -- the exact state this command exists to
        prevent.
        """
        reason = stamp_abort_reason(round_confirmed=True, body_written=False, commits_unstamped=0)
        assert reason is not None
        assert "body" in reason.lower()

    def test_an_unconfirmed_round_aborts(self) -> None:
        """Both signatures are required before anything is marked ready."""
        reason = stamp_abort_reason(round_confirmed=False, body_written=True, commits_unstamped=0)
        assert reason is not None
        assert "confirm" in reason.lower()

    def test_an_unconfirmed_round_is_named_ahead_of_an_unwritten_body(self) -> None:
        """When both are wrong, say the one that is upstream.

        Writing a body for a round nobody signed is the deeper fault, and a
        reader told only about the body would go and write one.
        """
        reason = stamp_abort_reason(round_confirmed=False, body_written=False, commits_unstamped=3)
        assert reason is not None
        assert "confirm" in reason.lower()

    def test_the_three_outcomes_stay_distinct(self) -> None:
        """THE CLAIM, and the reason the cases above are not enough.

        Every case above passes if the decision returns None unconditionally,
        which is the over-correction: a gate replaced by nothing. It also
        passes if every failure returns one identical string, which is the
        fault this whole session has been about -- distinct states sharing one
        output. Both are refused here.
        """
        permitted = stamp_abort_reason(round_confirmed=True, body_written=True, commits_unstamped=5)
        no_body = stamp_abort_reason(round_confirmed=True, body_written=False, commits_unstamped=0)
        no_confirm = stamp_abort_reason(
            round_confirmed=False, body_written=True, commits_unstamped=0
        )

        assert permitted is None, "unstamped commits still abort the stamp"
        assert no_body is not None, "a request can go ready with no review written"
        assert no_confirm is not None, "a request can go ready with nobody signing"
        assert no_body != no_confirm, (
            "two different failures produce the same message, so the reader "
            "cannot tell which happened"
        )
