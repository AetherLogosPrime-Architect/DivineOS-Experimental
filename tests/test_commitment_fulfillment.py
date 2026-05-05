"""Tests for `divineos commitment fulfillment` view.

Companion to commitment timeline. Where timeline shows what was committed,
fulfillment pairs each commitment with its outcome status (claim status,
prereg outcome, goal active/done, promise pending/fulfilled).
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.pre_registrations import (
    Outcome,
    file_pre_registration,
    init_pre_registrations_tables,
    record_outcome,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "home"))
    init_db()
    init_knowledge_table()
    init_pre_registrations_tables()
    yield


def _run(*args: str):
    return CliRunner().invoke(cli, list(args))


class TestFulfillment:
    def test_empty_says_no_commitments(self):
        result = _run("commitment", "fulfillment")
        assert result.exit_code == 0
        assert "No commitments" in result.output

    def test_open_prereg_appears_with_open_status(self):
        file_pre_registration(
            actor="aether",
            mechanism="m1",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        result = _run("commitment", "fulfillment")
        assert result.exit_code == 0, result.output
        assert "PREREG" in result.output
        assert "OPEN" in result.output
        assert "m1" in result.output

    def test_closed_prereg_shows_terminal_outcome(self):
        pid = file_pre_registration(
            actor="aether",
            mechanism="m_done",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        record_outcome(
            prereg_id=pid, actor="external-auditor", outcome=Outcome.SUCCESS, notes="verified"
        )

        result = _run("commitment", "fulfillment")
        assert "SUCCESS" in result.output
        assert "m_done" in result.output

    def test_only_open_filter_excludes_closed(self):
        file_pre_registration(
            actor="aether",
            mechanism="m_open",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        pid = file_pre_registration(
            actor="aether",
            mechanism="m_closed",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        record_outcome(prereg_id=pid, actor="external-auditor", outcome=Outcome.FAILED, notes="x")

        result = _run("commitment", "fulfillment", "--only", "open")
        assert "m_open" in result.output
        assert "m_closed" not in result.output

    def test_only_closed_filter_excludes_open(self):
        file_pre_registration(
            actor="aether",
            mechanism="m_open",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        pid = file_pre_registration(
            actor="aether",
            mechanism="m_closed",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        record_outcome(prereg_id=pid, actor="external-auditor", outcome=Outcome.FAILED, notes="x")

        result = _run("commitment", "fulfillment", "--only", "closed")
        assert "m_closed" in result.output
        assert "m_open" not in result.output

    def test_header_shows_open_closed_split(self):
        file_pre_registration(
            actor="aether",
            mechanism="m_open",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        result = _run("commitment", "fulfillment")
        assert "1 open" in result.output
        assert "0 closed" in result.output

    def test_days_window_excludes_old_items(self, monkeypatch):
        # Prereg created "now" should appear with default --days 7
        file_pre_registration(
            actor="aether",
            mechanism="m_recent",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        # 0-day window: nothing should appear
        result = _run("commitment", "fulfillment", "--days", "0")
        assert "No commitments" in result.output
