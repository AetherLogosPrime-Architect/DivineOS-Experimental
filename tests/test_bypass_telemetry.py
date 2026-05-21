"""Tests for bypass_telemetry — gate-bypass usage tracking.

Aletheia hidden-issues audit 2026-05-20 (Finding B): the instrument that
measures whether the gates are being routed-around had zero tests. The
window-edge counting and same-session-day dedup are the load-bearing logic.
"""

from __future__ import annotations

import json
import time

import pytest

from divineos.core import bypass_telemetry


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point divineos_home at a tmp dir and fix the session id so the
    dedup key is deterministic."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session-1")
    monkeypatch.delenv("DIVINEOS_SESSION_ID", raising=False)
    return tmp_path


class TestRecordAndRate:
    def test_record_then_rate_counts_it(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "a reason")
        stats = bypass_telemetry.bypass_rate()
        assert stats["total_events"] == 1
        assert stats["by_env_var"] == {"ENV_A": 1}
        assert stats["unique_days"] == 1

    def test_empty_when_no_events(self, isolated_home):
        stats = bypass_telemetry.bypass_rate()
        assert stats["total_events"] == 0
        assert stats["by_env_var"] == {}
        assert stats["unique_days"] == 0


class TestDedup:
    def test_same_env_session_day_collapses(self, isolated_home):
        # Repeated bypass within the same session-day is one row — the
        # signal is "fired today", not "fired N times".
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "first")
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "second")
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "third")
        assert bypass_telemetry.bypass_rate()["total_events"] == 1

    def test_distinct_env_vars_counted_separately(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        bypass_telemetry.record_bypass("gate-b", "ENV_B", "r")
        stats = bypass_telemetry.bypass_rate()
        assert stats["total_events"] == 2
        assert stats["by_env_var"] == {"ENV_A": 1, "ENV_B": 1}


class TestWindowFiltering:
    def test_events_outside_window_excluded(self, isolated_home):
        # Write one fresh event and one with an old timestamp directly.
        bypass_telemetry.record_bypass("gate-a", "ENV_FRESH", "fresh")
        log = bypass_telemetry._event_log()
        old_event = {
            "gate_name": "gate-old",
            "env_var": "ENV_OLD",
            "session_id": "test-session-1",
            "day": "2000-01-01",
            "timestamp": time.time() - (40 * 86400.0),  # 40 days ago
            "reason": "old",
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(old_event) + "\n")
        stats = bypass_telemetry.bypass_rate(window_days=14)
        assert stats["total_events"] == 1
        assert "ENV_OLD" not in stats["by_env_var"]
        assert "ENV_FRESH" in stats["by_env_var"]


class TestBriefingBlock:
    def test_empty_when_no_events(self, isolated_home):
        assert bypass_telemetry.briefing_block() == ""

    def test_nonempty_when_events(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        block = bypass_telemetry.briefing_block()
        assert "GATE BYPASS TELEMETRY" in block
        assert "ENV_A" in block

    def test_escalation_note_at_five_events(self, isolated_home):
        # Five distinct env vars (each unique key) cross the >=5 threshold.
        for i in range(5):
            bypass_telemetry.record_bypass(f"gate-{i}", f"ENV_{i}", "r")
        block = bypass_telemetry.briefing_block()
        assert "Elevated bypass rate" in block
