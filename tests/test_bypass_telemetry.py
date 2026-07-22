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


# ---------------------------------------------------------------------------
# Fix tests for the subset-is-not-the-whole violation (Andrew 2026-05-20,
# council-8faadb872d0b norman+wayne+knuth+pearl+feynman, 2026-07-21). The
# briefing_block was showing a 14-day window as if it were the whole
# history; now it shows both windowed sample AND full-history counts with
# crisp scope labels.
# ---------------------------------------------------------------------------


class TestFullHistoryStats:
    """The new full_history_stats() function reports the invariant that
    lets the observer compare windowed sample to the whole. Knuth
    boundary cases per council-8faadb872d0b."""

    def test_empty_log_returns_zeros(self, isolated_home):
        stats = bypass_telemetry.full_history_stats()
        assert stats["total_events_all_time"] == 0
        assert stats["first_recorded_date"] == ""
        assert stats["unique_days_all_time"] == 0
        assert stats["days_since_first"] == 0.0
        assert stats["events_per_day_avg"] == 0.0

    def test_single_event_today(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        stats = bypass_telemetry.full_history_stats()
        assert stats["total_events_all_time"] == 1
        assert stats["unique_days_all_time"] == 1
        assert stats["first_recorded_date"] != ""
        # days_since_first is ~0 for a same-second recording
        assert stats["days_since_first"] < 1.0

    def test_events_spanning_window_boundary(self, isolated_home):
        # One fresh, one 40 days old. Full history should count both;
        # windowed bypass_rate() should count only the fresh one.
        bypass_telemetry.record_bypass("gate-fresh", "ENV_FRESH", "r")
        log = bypass_telemetry._event_log()
        old = {
            "gate_name": "gate-old",
            "env_var": "ENV_OLD",
            "session_id": "test-session-1",
            "day": "2000-01-01",
            "timestamp": time.time() - (40 * 86400.0),
            "reason": "old",
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(old) + "\n")
        full = bypass_telemetry.full_history_stats()
        assert full["total_events_all_time"] == 2
        assert full["days_since_first"] >= 39.0

    def test_corrupted_lines_skipped(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        log = bypass_telemetry._event_log()
        with log.open("a", encoding="utf-8") as fh:
            fh.write("{ not valid json\n")
            fh.write("also garbage\n")
        stats = bypass_telemetry.full_history_stats()
        assert stats["total_events_all_time"] == 1

    def test_missing_timestamp_field_skipped_from_earliest_calc(self, isolated_home):
        # A record with a valid day but no timestamp should count in
        # totals but not contribute to earliest-event calculation.
        log = bypass_telemetry._event_log()
        good = {
            "gate_name": "gate-a",
            "env_var": "ENV_A",
            "session_id": "s",
            "day": "2026-07-21",
            "timestamp": time.time(),
            "reason": "",
        }
        no_ts = {
            "gate_name": "gate-b",
            "env_var": "ENV_B",
            "session_id": "s",
            "day": "2026-07-21",
            "reason": "",
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(good) + "\n")
            fh.write(json.dumps(no_ts) + "\n")
        stats = bypass_telemetry.full_history_stats()
        assert stats["total_events_all_time"] == 2
        assert stats["first_recorded_date"] != ""

    def test_future_timestamp_clamped_no_negative_days(self, isolated_home):
        # Clock drift or manual edit — a timestamp from the future must
        # not produce negative days_since_first.
        log = bypass_telemetry._event_log()
        future = {
            "gate_name": "gate-a",
            "env_var": "ENV_A",
            "session_id": "s",
            "day": "2099-01-01",
            "timestamp": time.time() + (365 * 86400.0),
            "reason": "clock-drift",
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(future) + "\n")
        stats = bypass_telemetry.full_history_stats()
        assert stats["days_since_first"] >= 0.0
        assert stats["events_per_day_avg"] >= 0.0


class TestBriefingBlockFullHistoryShape:
    """The fixed briefing_block shows BOTH windowed sample AND full-
    history counts with crisp scope labels (Norman gulf-of-evaluation)."""

    def test_windowed_and_full_history_both_named(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        block = bypass_telemetry.briefing_block()
        assert "Windowed" in block or "windowed" in block
        assert "Full history" in block or "full history" in block

    def test_windowed_section_names_its_window(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        block = bypass_telemetry.briefing_block()
        # Windowed line must state the window explicitly.
        assert "within the last" in block

    def test_full_history_section_names_first_date(self, isolated_home):
        bypass_telemetry.record_bypass("gate-a", "ENV_A", "r")
        block = bypass_telemetry.briefing_block()
        assert "since " in block

    def test_full_history_only_when_events_exist(self, isolated_home):
        # No events -> empty block, no full-history section.
        assert bypass_telemetry.briefing_block() == ""

    def test_full_history_elevated_at_20_total(self, isolated_home):
        # Full-history threshold: >= 20 total events, even if windowed
        # count is under the 5-in-14-days windowed threshold. Simulate by
        # writing 22 old events directly.
        log = bypass_telemetry._event_log()
        base_ts = time.time() - (60 * 86400.0)
        with log.open("a", encoding="utf-8") as fh:
            for i in range(22):
                rec = {
                    "gate_name": f"g{i}",
                    "env_var": f"ENV_OLD_{i}",
                    "session_id": f"s{i}",
                    "day": f"2026-05-{(i % 28) + 1:02d}",
                    "timestamp": base_ts + (i * 3600),
                    "reason": "",
                }
                fh.write(json.dumps(rec) + "\n")
        block = bypass_telemetry.briefing_block()
        assert "Elevated bypass rate" in block
        assert "full-history rate" in block
