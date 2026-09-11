"""The trace measure has to survive the ways the last two instruments died.

Each test below pins one property that, if it broke, would turn this store
back into something that flatters me: acknowledgment counting as change, a
row being rewritten after it resolved, an unreadable database reading as a
clean record, or a rate computed off a denominator that is not there.
"""

from __future__ import annotations

import pytest

from divineos.core import andrew_answer_trace as trace


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    monkeypatch.setattr(trace, "divineos_home", lambda: tmp_path)


def _opened(question: str = "which of these two should I build first?") -> int:
    return trace.ask(question)


def test_prose_consequence_is_refused_but_an_artifact_is_taken():
    row = _opened()
    trace.answered(row, "the second one")
    with pytest.raises(trace.TraceRefused):
        trace.changed(row, "I took this on board and it shaped my thinking")
    trace.changed(row, "abandoned the gate in src/divineos/core/andrew_answer_trace.py")
    assert trace.report(30).changed == 1


def test_a_resolved_row_cannot_be_reopened_or_re_resolved():
    row = _opened()
    trace.answered(row, "no, do it the other way")
    trace.no_change(row, "he confirmed the order I already had")
    with pytest.raises(trace.TraceRefused):
        trace.answered(row, "trying to answer it twice")
    with pytest.raises(trace.TraceRefused):
        trace.changed(row, "tests/test_andrew_answer_trace.py")


def test_a_row_cannot_be_resolved_before_his_answer_is_recorded():
    row = _opened()
    with pytest.raises(trace.TraceRefused):
        trace.changed(row, "src/divineos/core/andrew_answer_trace.py")
    with pytest.raises(trace.TraceRefused):
        trace.no_change(row, "nothing needed changing here at all")


def test_an_unnamed_no_change_is_refused():
    row = _opened()
    trace.answered(row, "yes")
    with pytest.raises(trace.TraceRefused):
        trace.no_change(row, "n/a")


def test_rate_is_none_with_no_denominator_and_not_zero():
    assert trace.report(30).change_rate is None
    row = _opened()
    trace.answered(row, "yes")
    # Answered but unresolved is not a resolution, so there is still no rate.
    assert trace.report(30).change_rate is None
    assert trace.report(30).oldest_unresolved_days is not None


def test_unreadable_store_reports_none_rather_than_zero(monkeypatch):
    import sqlite3

    def _broken():
        raise sqlite3.OperationalError("disk gone")

    monkeypatch.setattr(trace, "_conn", _broken)
    r = trace.report(30)
    assert r.asked is None and r.changed is None
    assert trace.list_open() == []


def test_open_rows_stay_visible_with_their_age():
    row = _opened("did the third instrument need to exist at all?")
    waiting = trace.list_open()
    assert [w["id"] for w in waiting] == [row]
    assert waiting[0]["status"] == trace.OPEN
    trace.answered(row, "no")
    assert trace.list_open()[0]["status"] == trace.ANSWERED
    trace.changed(row, "killed it before it shipped — see claim-41f0cd2b")
    assert trace.list_open() == []
