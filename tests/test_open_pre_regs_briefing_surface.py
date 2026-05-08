"""Tests for format_open_pre_regs in pre_registrations.summary.

Verifies the surface fires when open preregs exist, returns empty
when there are none, respects the limit, and shows review-day countdown.
"""

from __future__ import annotations


import pytest


@pytest.fixture
def isolated_prereg_db(tmp_path, monkeypatch):
    """Point pre_registrations module at an isolated tmp DB."""
    import divineos.core._ledger_base as lb

    db_path = tmp_path / "test_ledger.db"
    monkeypatch.setattr(lb, "DB_PATH", db_path)

    # Init the prereg tables in the fresh DB
    from divineos.core.pre_registrations.store import init_pre_registrations_tables

    init_pre_registrations_tables()
    return db_path


def test_empty_string_when_no_open_pre_regs(isolated_prereg_db):
    from divineos.core.pre_registrations.summary import format_open_pre_regs

    assert format_open_pre_regs() == ""


def test_surfaces_recent_open_pre_reg(isolated_prereg_db):
    from divineos.core.pre_registrations.store import file_pre_registration
    from divineos.core.pre_registrations.summary import format_open_pre_regs

    file_pre_registration(
        actor="user",
        mechanism="test-mechanism",
        claim="Test claim about a thing.",
        success_criterion="Success looks like X",
        falsifier="Falsifier is Y observed",
        review_window_days=30,
    )
    out = format_open_pre_regs()
    assert "[active pre-regs]" in out
    assert "1 open prediction" in out
    assert "test-mechanism" in out
    assert "review in" in out  # countdown shows


def test_respects_limit(isolated_prereg_db):
    from divineos.core.pre_registrations.store import file_pre_registration
    from divineos.core.pre_registrations.summary import format_open_pre_regs

    for i in range(6):
        file_pre_registration(
            actor="user",
            mechanism=f"mech-{i}",
            claim=f"Claim {i}",
            success_criterion="X",
            falsifier="Y",
            review_window_days=30,
        )
    out = format_open_pre_regs(limit=3)
    # Header should still report 3 (the requested limit)
    assert "3 open prediction" in out
    # Should mention only 3 of the 6 mechanisms
    mech_count = sum(1 for i in range(6) if f"mech-{i}" in out)
    assert mech_count == 3


def test_overdue_pre_reg_shown_with_overdue_marker(isolated_prereg_db):
    """If a pre-reg becomes overdue, the surface still shows it but marks OVERDUE."""
    import sqlite3
    from divineos.core.pre_registrations.store import file_pre_registration
    from divineos.core.pre_registrations.summary import format_open_pre_regs

    file_pre_registration(
        actor="user",
        mechanism="overdue-mech",
        claim="Claim",
        success_criterion="X",
        falsifier="Y",
        review_window_days=30,
    )
    # Backdate review_ts directly so it is overdue (cannot file with negative window).
    conn = sqlite3.connect(isolated_prereg_db)
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE mechanism = ?",
            (1.0, "overdue-mech"),  # Jan 1 1970
        )
        conn.commit()
    finally:
        conn.close()
    out = format_open_pre_regs()
    assert "OVERDUE by" in out
    assert "overdue-mech" in out


def test_long_claim_truncated(isolated_prereg_db):
    from divineos.core.pre_registrations.store import file_pre_registration
    from divineos.core.pre_registrations.summary import format_open_pre_regs

    long_claim = "X" * 200
    file_pre_registration(
        actor="user",
        mechanism="mech",
        claim=long_claim,
        success_criterion="X",
        falsifier="Y",
        review_window_days=30,
    )
    out = format_open_pre_regs()
    assert "..." in out
    assert ("X" * 200) not in out  # truncated, not full
