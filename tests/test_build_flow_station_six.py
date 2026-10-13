"""Station 6 answered "cannot check" for its whole life, and nothing noticed.

The station asks whether a council walk landed after the branch's last commit.
It called a ledger function with a parameter that function does not have, so
every invocation raised and was swallowed into the third state. The board
printed "commit or walk timestamps unreadable" and that read as caution rather
than as a dead instrument.

These tests hold the two things that broke: the ledger call has to be real,
and an unreadable timestamp must not be reported as a stale walk.
"""

from __future__ import annotations

import inspect

from divineos.cli import build_flow_commands as bf


def test_the_ledger_function_actually_takes_the_arguments_we_pass():
    """The original defect: search_events has no event_type parameter."""
    from divineos.core.ledger import get_events

    params = inspect.signature(get_events).parameters
    assert "event_type" in params
    assert "order" in params

    source = inspect.getsource(bf._walk_postdates_build)
    assert "get_events(" in source
    assert "search_events(" not in source
    # Without desc the 28k-row ledger hands back its oldest history.
    assert 'order="desc"' in source


def test_epoch_seconds_reads_floats_and_iso_strings():
    assert bf._epoch_seconds(1788760279.889) == 1788760279.889
    assert bf._epoch_seconds("1788760279.889") == 1788760279.889
    assert bf._epoch_seconds("2026-09-07T12:00:00+00:00") is not None


def test_epoch_seconds_refuses_to_guess():
    assert bf._epoch_seconds(None) is None
    assert bf._epoch_seconds("last tuesday") is None
    assert bf._epoch_seconds(object()) is None


def test_unreadable_timestamps_report_cannot_check_not_stale(monkeypatch):
    """An unreadable walk is not a walk that happened too early."""
    monkeypatch.setattr(bf, "_run_git", lambda args: "1788000000\n")
    monkeypatch.setattr(
        "divineos.core.ledger.get_events",
        lambda **kw: [{"timestamp": "not a time"}],
    )
    assert bf._walk_postdates_build("some-branch") is None


def test_no_walks_at_all_is_a_real_no(monkeypatch):
    monkeypatch.setattr(bf, "_run_git", lambda args: "1788000000\n")
    monkeypatch.setattr("divineos.core.ledger.get_events", lambda **kw: [])
    assert bf._walk_postdates_build("some-branch") is False


def test_a_later_walk_is_a_yes(monkeypatch):
    monkeypatch.setattr(bf, "_run_git", lambda args: "1788000000\n")
    monkeypatch.setattr(
        "divineos.core.ledger.get_events",
        lambda **kw: [{"timestamp": 1788999999.0}],
    )
    assert bf._walk_postdates_build("some-branch") is True
