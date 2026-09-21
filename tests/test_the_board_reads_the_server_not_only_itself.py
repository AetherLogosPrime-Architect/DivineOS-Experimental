"""The board reported every station proven on requests the server was failing.

2026-09-21. Andrew pasted four failing checks off the actions page while I was
reporting a green suite. Both statements were true and they were about
different things: the suite I ran was green on the one object I ran it against,
and the server was red on branches I had never asked about. The board I read
every turn reads every open request's stations and had never once read their
checks — so a request could show every station proven, print the word that
means finished, and be unmergeable on the server with nothing on the page
saying so. Six of seven were in exactly that state when this was added.

A station list says whether the PROCESS was followed. The checks say whether
the CODE runs. Reporting the first while silent on the second is the same
population fault as every other one today: measure one set, speak about
another.

THREE STATES, and the third is why this file exists at all. Could-not-tell
must never render as nothing-failing, because that collapse lands here as a
green board over a red server — which is the precise thing being repaired.
"""

from __future__ import annotations

from divineos.cli.build_flow_commands import _check_state


def _pr(*states: str) -> dict:
    return {"statusCheckRollup": [{"conclusion": s} for s in states]}


def test_a_failing_check_is_named_as_failing():
    assert _check_state(_pr("SUCCESS", "FAILURE")) == "CHECKS FAILING"


def test_one_failure_outweighs_any_number_of_passes():
    assert _check_state(_pr(*(["SUCCESS"] * 20), "FAILURE")) == "CHECKS FAILING"


def test_all_passing_says_so():
    assert _check_state(_pr("SUCCESS", "SUCCESS")) == "checks passing"


def test_still_running_is_its_own_answer():
    """Not yet failed is not passed, and the board used to have no way to say
    the difference."""
    assert _check_state(_pr("SUCCESS", "")) == "checks still running"


def test_a_missing_rollup_is_could_not_tell_not_all_clear():
    """THE CARRYING TEST. If this ever returns a passing-shaped answer, the
    board goes green over a server nobody asked."""
    assert _check_state({}) is None
    assert _check_state({"statusCheckRollup": None}) is None
    assert _check_state({"statusCheckRollup": []}) is None


def test_an_unrecognised_shape_is_could_not_tell():
    """A payload that is present but not what this reader understands must not
    be read as silence-means-fine."""
    assert _check_state({"statusCheckRollup": ["not a dict"]}) is None


def test_the_three_answers_stay_distinct():
    """One report with one possible value is not a report. Each of the three
    situations must produce a different answer."""
    answers = {
        _check_state(_pr("FAILURE")),
        _check_state(_pr("SUCCESS")),
        _check_state({}),
    }
    assert len(answers) == 3
