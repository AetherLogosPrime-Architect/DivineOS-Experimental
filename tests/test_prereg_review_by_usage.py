"""A pre-registration is reviewed when it has been used, never when a date arrives.

Dad, 2026-10-16: *"we do not do reviews by dates but by usage itself... i could
go on vacation for 30 days come back and you have no data.. or even worse it
takes 30 days for the issue to sit there and pile up before its addressed."*

The pairs are the point. "A usage row is not overdue by date" alone is satisfied
by a query that never reports anything; "a usage row IS due after N uses" proves
it still reports.
"""

from __future__ import annotations

import time

import pytest

from divineos.core.ledger import log_event
from divineos.core.pre_registrations.store import (
    _get_connection,
    file_pre_registration,
    get_overdue_pre_registrations,
    get_pre_registration,
)

EVENT = "TEST_USAGE_EVENT"


def _use(n: int = 1) -> None:
    for _ in range(n):
        log_event(EVENT, "test", {"k": "v"}, validate=False)


def _file(uses: int = 2) -> str:
    return file_pre_registration(
        actor="aether",
        mechanism="m",
        claim="c",
        success_criterion="s",
        falsifier="f",
        review_after_uses=uses,
        uses_of=EVENT,
    )


def _backdate(prereg_id: str, days: float) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ?, created_at = ? WHERE prereg_id = ?",
            (time.time() - days * 86400, time.time() - days * 86400, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()


def _ids() -> set[str]:
    return {p.prereg_id for p in get_overdue_pre_registrations()}


def test_due_only_after_n_more_uses():
    _use()
    pid = _file(uses=2)
    assert pid not in _ids()
    _use()
    assert pid not in _ids()
    _use()
    assert pid in _ids()


def test_uses_before_filing_do_not_count():
    _use(5)
    pid = _file(uses=2)
    assert pid not in _ids()


def test_a_long_passed_date_never_makes_a_usage_row_due():
    _use()
    pid = _file(uses=3)
    _backdate(pid, days=400)
    assert pid not in _ids()


def test_a_date_scheduled_legacy_row_still_goes_overdue_by_date():
    pid = file_pre_registration(
        actor="aether",
        mechanism="legacy",
        claim="c",
        success_criterion="s",
        falsifier="f",
        review_window_days=7,
    )
    assert pid not in _ids()
    _backdate(pid, days=30)
    assert pid in _ids()


def test_filing_against_an_event_type_that_never_happened_is_refused():
    with pytest.raises(ValueError, match="no 'NEVER_HAPPENED_EVENT' events"):
        file_pre_registration(
            actor="aether",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_after_uses=1,
            uses_of="NEVER_HAPPENED_EVENT",
        )


def test_both_halves_of_the_trigger_are_needed():
    with pytest.raises(ValueError):
        file_pre_registration(
            actor="aether",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_after_uses=2,
        )


def test_a_pruned_event_type_is_refused_at_filing():
    # The conveyor belt deletes these, so a count of them can fall below its baseline
    # and the review would silently never come due (Aria, 2026-10-16).
    with pytest.raises(ValueError, match="pruned from the ledger"):
        file_pre_registration(
            actor="aether",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_after_uses=1,
            uses_of="TOOL_CALL",
        )


def test_a_due_row_carries_the_moment_of_its_last_needed_use_not_a_placeholder():
    # Every reader sorts and prints by review_ts. For a usage row it must be a real
    # moment once due, and a far-future date until then, whatever is stored.
    _use(1)
    pid = _file(uses=2)
    before = get_pre_registration(pid)
    assert before is not None and before.review_ts > time.time() + 86400 * 365
    _use(2)
    after = get_pre_registration(pid)
    assert after is not None and after.review_ts <= time.time()


def test_the_briefing_and_the_warning_show_a_use_due_row_as_overdue():
    from divineos.core.briefing_dashboard import _row_preregs
    from divineos.core.pre_registrations.summary import format_overdue_warning

    _use(1)
    pid = _file(uses=1)
    assert pid not in format_overdue_warning()
    _use(1)
    assert pid in format_overdue_warning()
    row = _row_preregs()
    assert row is not None
    assert "overdue" in str(row).lower()


def test_the_trigger_is_stored_with_its_baseline():
    _use(3)
    pid = _file(uses=2)
    row = get_pre_registration(pid)
    assert row is not None
    assert (row.review_after_uses, row.uses_of, row.uses_baseline) == (2, EVENT, 3)


def test_the_cli_refuses_a_filing_with_no_usage_trigger():
    from click.testing import CliRunner

    from divineos.cli import cli

    result = CliRunner().invoke(
        cli,
        [
            "prereg",
            "file",
            "m",
            "--claim",
            "c",
            "--success",
            "s",
            "--falsifier",
            "f",
            "--embarrassing",
            "e",
        ],
    )
    assert result.exit_code != 0
    assert "--review-after-uses" in result.output
