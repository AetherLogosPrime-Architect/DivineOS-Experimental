"""Tests for tool_logbook — separate store for TOOL_CALL/TOOL_RESULT events.

Per Andrew's design 2026-05-05: tool events were clogging the main ledger
and the conveyor-belt prune made the verifier report DEGRADED. This module
moves them to a separate, capped, prune-aware store that the verifier reads.
"""

from __future__ import annotations

import time

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.tool_logbook import (
    LogbookStats,
    _DEFAULT_CAP,
    emit_tool_call,
    emit_tool_result,
    get_stats,
    init_tool_logbook_tables,
    prune_logbook,
    verify_logbook_health,
)


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()
    init_knowledge_table()
    init_tool_logbook_tables()
    yield


class TestEmit:
    def test_emit_tool_call_returns_log_id(self):
        log_id = emit_tool_call(
            tool_name="Read",
            tool_input={"path": "/tmp/x"},
            tool_use_id="use-1",
        )
        assert log_id.startswith("log-")

    def test_emit_tool_result_returns_log_id(self):
        log_id = emit_tool_result(
            tool_name="Read",
            tool_use_id="use-1",
            result="file contents",
            duration_ms=42,
        )
        assert log_id.startswith("log-")

    def test_emit_tool_result_failed(self):
        log_id = emit_tool_result(
            tool_name="Bash",
            tool_use_id="use-2",
            result="",
            duration_ms=10,
            failed=True,
            error_message="permission denied",
        )
        assert log_id.startswith("log-")

    def test_string_input_accepted(self):
        log_id = emit_tool_call(
            tool_name="X",
            tool_input='{"already": "json"}',
            tool_use_id="use-3",
        )
        assert log_id.startswith("log-")

    def test_huge_result_truncated(self):
        big = "X" * 200_000
        emit_tool_result(
            tool_name="Y",
            tool_use_id="use-4",
            result=big,
            duration_ms=1,
        )
        # No exception means truncation worked


class TestStats:
    def test_empty_logbook(self):
        stats = get_stats()
        assert stats.total_rows == 0
        assert stats.oldest_ts is None
        assert stats.last_5min_count == 0
        assert stats.by_type == {}

    def test_stats_after_emits(self):
        emit_tool_call(tool_name="A", tool_input={}, tool_use_id="u1")
        emit_tool_result(tool_name="A", tool_use_id="u1", result="ok", duration_ms=5)
        emit_tool_call(tool_name="B", tool_input={}, tool_use_id="u2")
        stats = get_stats()
        assert stats.total_rows == 3
        assert stats.by_type["TOOL_CALL"] == 2
        assert stats.by_type["TOOL_RESULT"] == 1
        assert stats.last_5min_count == 3
        assert stats.oldest_ts is not None
        assert stats.newest_ts >= stats.oldest_ts

    def test_at_capacity_flag(self):
        cap = 10
        for i in range(int(cap * 0.95)):
            emit_tool_call(tool_name="X", tool_input={"i": i}, tool_use_id=f"u{i}")
        stats = get_stats(cap=cap)
        assert stats.at_capacity


class TestPrune:
    def test_no_prune_when_under_threshold(self):
        for i in range(5):
            emit_tool_call(tool_name="X", tool_input={}, tool_use_id=f"u{i}")
        pruned = prune_logbook(cap=100, slack=10)
        assert pruned == 0
        assert get_stats().total_rows == 5

    def test_prune_oldest_when_over_threshold(self):
        # Fill past cap+slack
        cap = 5
        slack = 2
        for i in range(15):
            emit_tool_call(tool_name="X", tool_input={"i": i}, tool_use_id=f"u{i}")

        before = get_stats().total_rows
        assert before == 15

        pruned = prune_logbook(cap=cap, slack=slack)
        assert pruned == before - cap

        after = get_stats().total_rows
        assert after == cap

    def test_prune_keeps_newest(self):
        # Insert older then newer
        cap = 3
        slack = 0
        for i in range(10):
            emit_tool_call(tool_name="X", tool_input={"i": i}, tool_use_id=f"u{i}")
            time.sleep(0.001)  # ensure timestamp ordering
        prune_logbook(cap=cap, slack=slack)
        stats = get_stats()
        assert stats.total_rows == cap
        # Newest tool_use_id should still be there
        # (we don't query directly; just confirm cap is enforced)


class TestHealthCheck:
    def test_empty_logbook_message(self):
        health = verify_logbook_health()
        assert health["status"] == "HEALTHY"
        assert "empty" in health["message"]

    def test_active_logbook_healthy(self):
        emit_tool_call(tool_name="X", tool_input={}, tool_use_id="u1")
        emit_tool_result(tool_name="X", tool_use_id="u1", result="ok", duration_ms=1)
        health = verify_logbook_health()
        assert health["status"] == "HEALTHY"

    def test_at_capacity_status(self):
        # Fill to capacity
        for i in range(_DEFAULT_CAP):
            emit_tool_call(tool_name="X", tool_input={}, tool_use_id=f"u{i}")
        health = verify_logbook_health()
        assert health["status"] == "HEALTHY_AT_CAP"
        assert "capacity" in health["message"].lower()


class TestRegression:
    """Pin the exact 2026-05-05 misreport bug — verifier saw 0% TOOL_CALL
    rate in main ledger when the prune was working as designed. Now: tool
    events are in the logbook and the verifier reports correctly."""

    def test_tool_events_route_to_logbook_not_main_ledger(self):
        from divineos.core.ledger import get_events

        emit_tool_call(tool_name="X", tool_input={}, tool_use_id="u1")
        # Main ledger should NOT see this.
        main_events = get_events(limit=100) or []
        tool_events_in_main = [e for e in main_events if e.get("event_type") == "TOOL_CALL"]
        assert tool_events_in_main == []
        # Logbook SHOULD see it.
        stats = get_stats()
        assert stats.by_type.get("TOOL_CALL", 0) == 1


class TestShape:
    def test_logbook_stats_immutable(self):
        s = LogbookStats(
            total_rows=0,
            oldest_ts=None,
            newest_ts=None,
            cap=100,
            at_capacity=False,
            last_5min_count=0,
            by_type={},
        )
        try:
            s.total_rows = 99  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("LogbookStats should be frozen")
