"""Tests for the external-audit cadence module (Grok audit round 4 of 4).

Invariants locked by these tests:

* A fresh install (zero audit_rounds) reads as OVERDUE. Self-review
  cannot substitute for external validation.
* ``days_since_last_audit`` returns None when no round exists and a
  positive float when one does.
* ``is_overdue`` respects the threshold parameter.
* ``format_cadence_warning`` returns empty string when not overdue and
  a non-empty briefing block when overdue.
* Filing a fresh round clears the overdue state.
* ``cadence_status_line`` always returns a string, even at zero state.
"""

import os
import time

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.cadence import (
    CADENCE_THRESHOLD_DAYS,
    SECONDS_PER_DAY,
    cadence_status_line,
    days_since_last_audit,
    format_cadence_warning,
    is_overdue,
    last_external_audit_ts,
)
from divineos.core.watchmen.store import submit_round


@pytest.fixture(autouse=True)
def _cadence_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_watchmen_tables()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# ── Empty-state invariants ───────────────────────────────────────────


class TestEmptyState:
    def test_fresh_install_has_no_audit_ts(self):
        assert last_external_audit_ts() is None

    def test_fresh_install_reports_none_days(self):
        assert days_since_last_audit() is None

    def test_fresh_install_is_overdue(self):
        """A fresh install cannot be trusted to have been externally
        validated. The cadence gate must block until the first audit fires."""
        assert is_overdue() is True

    def test_fresh_install_warning_is_non_empty(self):
        warning = format_cadence_warning()
        assert warning
        assert "OVERDUE" in warning
        assert "has ever been filed" in warning.lower()


# ── Freshly-filed round clears overdue ───────────────────────────────


class TestFreshRound:
    def test_filing_round_sets_last_audit_ts(self):
        before = time.time()
        submit_round(actor="grok", focus="test audit")
        after = time.time()
        ts = last_external_audit_ts()
        assert ts is not None
        assert before <= ts <= after

    def test_filing_round_clears_overdue(self):
        submit_round(actor="grok", focus="test audit")
        assert is_overdue() is False

    def test_filing_round_clears_warning(self):
        submit_round(actor="grok", focus="test audit")
        assert format_cadence_warning() == ""

    def test_days_since_is_small_after_filing(self):
        submit_round(actor="grok", focus="test audit")
        delta = days_since_last_audit()
        assert delta is not None
        assert 0 <= delta < 0.1  # fraction of a day


# ── Stale round triggers overdue ─────────────────────────────────────


class TestStaleRound:
    def test_round_older_than_threshold_is_overdue(self):
        """Simulate time passing past the threshold."""
        submit_round(actor="grok", focus="old audit")
        future = time.time() + (CADENCE_THRESHOLD_DAYS + 1) * SECONDS_PER_DAY
        assert is_overdue(now=future) is True

    def test_round_within_threshold_is_not_overdue(self):
        submit_round(actor="grok", focus="recent audit")
        future = time.time() + (CADENCE_THRESHOLD_DAYS - 1) * SECONDS_PER_DAY
        assert is_overdue(now=future) is False

    def test_custom_threshold_honored(self):
        submit_round(actor="grok", focus="audit")
        # At 3 days old, should be overdue under a 2-day threshold
        future = time.time() + 3 * SECONDS_PER_DAY
        assert is_overdue(threshold_days=2, now=future) is True
        assert is_overdue(threshold_days=7, now=future) is False

    def test_overdue_warning_names_elapsed_days(self):
        submit_round(actor="grok", focus="old audit")
        future = time.time() + (CADENCE_THRESHOLD_DAYS + 3) * SECONDS_PER_DAY
        warning = format_cadence_warning(now=future)
        assert warning
        assert "days ago" in warning


# ── Multiple rounds — latest wins ────────────────────────────────────


class TestMultipleRounds:
    def test_latest_round_determines_ts(self):
        """``last_external_audit_ts`` must use MAX(created_at), not count
        or first-found."""
        # File an old-looking one then a fresh one — the DB stores real
        # created_at from time.time() at filing, so filing twice gives
        # two distinct timestamps. The second should dominate.
        submit_round(actor="grok", focus="older")
        first_ts = last_external_audit_ts()
        time.sleep(0.01)
        submit_round(actor="user", focus="newer")
        second_ts = last_external_audit_ts()
        assert second_ts is not None
        assert first_ts is not None
        assert second_ts > first_ts


# ── cadence_status_line: always returns a string ─────────────────────


class TestStatusLine:
    def test_empty_returns_overdue_line(self):
        line = cadence_status_line()
        assert "OVERDUE" in line
        assert "never been filed" in line.lower() or "no audit" in line.lower()

    def test_recent_returns_ok_line(self):
        submit_round(actor="grok", focus="test")
        line = cadence_status_line()
        assert "OK" in line

    def test_stale_returns_overdue_line(self):
        submit_round(actor="grok", focus="test")
        future = time.time() + (CADENCE_THRESHOLD_DAYS + 5) * SECONDS_PER_DAY
        line = cadence_status_line(now=future)
        assert "OVERDUE" in line


# ── Constants are stable ─────────────────────────────────────────────


def test_threshold_default_value_is_3_days():
    """Lock the default so a silent change appears in the diff.

    Was 14 days in the initial ship; calibrated down to 3 days on
    2026-04-16 after Grok/Andrew observed the actual audit rhythm is
    bursty (several per day, then gaps). 14 days failed to fire on a
    real 5.5-day historical gap. If this default changes again, the
    diff must reference new evidence about real-world cadence.
    """
    assert CADENCE_THRESHOLD_DAYS == 3


def test_seconds_per_day_constant():
    assert SECONDS_PER_DAY == 86400
