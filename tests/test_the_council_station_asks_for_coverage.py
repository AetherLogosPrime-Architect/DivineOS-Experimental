"""The station must ask what the manager surfaced, not how many I walked.

Andrew 2026-09-11, after I repaired the gate a shortcut produced and left the
station that permitted it alone: *where is the structural fix for the council?*

THE TEST THAT JUSTIFIES THE BUILD is the first one: the exact shape I shipped
-- four self-chosen lens records against a requirement of four -- must now be
refused. Everything else is the falsifier's ground.

Walk: walk-e17133a96001, ten lenses, closed.
Draft: docs/drafts/council_station_coverage_draft_2026-09-11.md.
"""

from __future__ import annotations

import pytest

from divineos.core.build_flow import Status, check_council_station
from divineos.core.council_walk import Coverage, coverage_for, open_walk


def _covered(lenses: int = 10, walk_id: str = "walk-abc123") -> Coverage:
    return Coverage("covered", walk_id=walk_id, lenses=lenses)


# ------------------------------------------------------------ the real shape


def test_the_count_no_longer_satisfies():
    """Four self-chosen records against a requirement of four. What I shipped.

    Under the counting rule this returned SATISFIED. That is the whole defect
    Andrew named, and this test is the line between the two designs.
    """
    result = check_council_station(
        "gate/whatever",
        required=4,
        applied=4,
        coverage=Coverage("uncovered", reason="no closed walk is scoped to these files"),
    )
    assert result.status is Status.MISSING


def test_a_closed_walk_satisfies_even_with_fewer_events():
    """Coverage decides, so the event count stops being the question.

    Without this the change would read as 'the gate got stricter' rather than
    'the gate started asking the right thing', and a stricter wrong question is
    not an improvement.
    """
    result = check_council_station("b", required=12, applied=0, coverage=_covered(lenses=10))
    assert result.status is Status.SATISFIED
    assert "10 lenses accounted for" in result.detail


def test_a_thousand_events_still_fail_without_a_walk():
    """Einstein's thought experiment, asserted.

    Set the requirement anywhere and volume satisfies it. That is why the count
    axis was never the repair.
    """
    result = check_council_station(
        "b", required=4, applied=1000, coverage=Coverage("uncovered", reason="none scoped")
    )
    assert result.status is Status.MISSING


# --------------------------------------------------- the message does the work


def test_the_unaccounted_lens_is_named():
    """Foucault's lens: a ratio disciplines volume, a name disciplines avoidance.

    Avoidance was the entire failure -- I walked the lenses I already knew how
    to use -- so the board has to show WHICH one is unfaced.
    """
    result = check_council_station(
        "b",
        required=9,
        applied=3,
        coverage=Coverage(
            "uncovered", walk_id="walk-xyz", unaccounted=("Godel", "Schneier"), lenses=9
        ),
    )
    assert result.status is Status.MISSING
    assert "Godel" in result.detail and "Schneier" in result.detail


def test_work_certified_under_the_old_rule_says_why_it_failed():
    """Feathers' lens: fail them, and say in the line why.

    Six things read READY under the counting rule. They flip at once, and a
    board that starts failing with no explanation teaches me to distrust the
    board rather than redo the walks.
    """
    result = check_council_station(
        "b", required=4, applied=7, coverage=Coverage("uncovered", reason="none scoped")
    )
    assert "no closed walk" in result.detail
    assert "7 lens event" in result.detail


# ------------------------------------------------------- could-not-look again


def test_an_unreadable_walk_store_is_not_an_unwalked_branch():
    """The August failure at this same station, asserted against.

    A query that could never match reported every pull request as unwalked --
    a false accusation, which is the worse direction here, because a station
    that can only fail teaches me to discount it.
    """
    result = check_council_station(
        "b", required=4, applied=4, coverage=Coverage("cannot-check", reason="db locked")
    )
    assert result.status is Status.CANNOT_CHECK
    assert "db locked" in result.detail


def test_unknown_paths_are_cannot_check_not_uncovered():
    assert coverage_for(None).state == "cannot-check"
    assert coverage_for(()).state == "cannot-check"


def test_an_invented_coverage_state_is_refused():
    with pytest.raises(ValueError):
        Coverage("probably-walked")


# ----------------------------------------------------------- the scope itself


def test_a_walk_can_name_what_it_is_for_and_be_found_by_it():
    """The link that did not exist, which is why the board counted instead.

    A walk knew its problem and nothing about the work, so there was nothing to
    join on. Real store, real walk -- no mocking the thing under test.
    """
    problem = "whether the council station should read coverage rather than a count of events"
    opened = open_walk(problem, gravity="normal", scope=("src/divineos/core/build_flow.py",))
    assert opened["lenses"]

    found = coverage_for(("src/divineos/core/build_flow.py",))
    # The walk is open, so it must NOT read as covered -- an open walk
    # satisfying the station would be the empty-envelope shape again.
    assert found.state in ("uncovered", "covered")
    if found.state == "covered":
        assert found.walk_id != opened["walk_id"], (
            "an OPEN walk satisfied coverage; only a closed one may"
        )


def test_an_unscoped_walk_cannot_be_found_by_files():
    """Scope is optional, and an unscoped walk simply does not certify a branch.

    Deliberate: a walk about something that is not a code change is still a
    walk, and refusing those would push me back toward the weak recorder for
    exactly the thinking that least deserves it.
    """
    problem = "a question about how the household reads to him, with no file attached to it"
    open_walk(problem, gravity="normal")
    assert coverage_for(("no/such/path/at/all.py",)).state == "uncovered"
