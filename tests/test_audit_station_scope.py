"""Station eight must say what it looked at before it says it found nothing.

WHY THESE EXIST. On 2026-08-28 Aria went to verify an audit round I had filed
and her own tools told her twice that it did not exist. Both readings were true
and both were about the wrong thing: her store is not the one I wrote to.

Then she measured the board's own lookup and found a second narrowing stacked
under the first -- ``list_rounds`` defaults to twenty rows and the board called
it with no argument, so every pull request was compared against the twenty most
recent rounds out of three hundred and twenty-one.

Neither narrowing produced CANNOT_CHECK. Both produced a confident MISS, at the
last gate before a merge.

Third instance of this class in the same file, and its own docstrings carry the
other two: the changed-files list silently capping at a hundred, and before that
the lens key being wrong. My own sentence there -- *the data was present and the
query could not reach it. A station that can only fail teaches me to discount
it, and a discounted gate is a dead gate.*

Nothing tested this function before today, which is part of why two truncations
could live inside it.
"""

from __future__ import annotations

from divineos.core.build_flow import Status, check_audit_station


def test_a_miss_names_the_store_it_looked_in():
    """An unqualified negative cannot be checked by the person reading it."""
    result = check_audit_station(447, "instruments/clean", ("round-x names other",), "/path/to.db")
    assert result.status is Status.MISSING
    assert "/path/to.db" in result.detail


def test_a_miss_names_how_many_rounds_it_compared_against():
    """The row cap was invisible until the count was printed beside the verdict.

    Aria found it because the number came back matching neither store. A count
    in the output is what makes the next silent truncation visible without
    anyone going looking for it.
    """
    result = check_audit_station(447, "b", ("r1", "r2", "r3"), "/s.db")
    assert "3 round(s)" in result.detail


def test_an_unidentified_store_says_so_rather_than_guessing():
    """Naming a store this did not query would be the error being fixed.

    The label must come from the connection the rounds were read through. When
    it cannot, the honest output is that the scope is unknown -- not a
    plausible path assembled from configuration.
    """
    result = check_audit_station(447, "b", ("r1",), None)
    assert "not identified" in result.detail
    assert ".db" not in result.detail


def test_a_satisfied_verdict_still_names_what_satisfied_it():
    """The positive direction, so the scope work did not break the pass."""
    by_pr = check_audit_station(447, "b", ("round names PR #447",), "/s.db")
    assert by_pr.status is Status.SATISFIED
    by_branch = check_audit_station(999, "instruments/clean", ("names instruments/clean",), "/s.db")
    assert by_branch.status is Status.SATISFIED
    assert "instruments/clean" in by_branch.detail


def test_an_unreachable_lookup_is_still_cannot_check_not_a_miss():
    """The pre-existing distinction must survive the change.

    None arrives when the lookup did not complete. Turning that into a scoped
    MISS would convert an honest unknown into a confident negative, which is
    the whole disease.
    """
    result = check_audit_station(447, "b", None, None)
    assert result.status is Status.CANNOT_CHECK
