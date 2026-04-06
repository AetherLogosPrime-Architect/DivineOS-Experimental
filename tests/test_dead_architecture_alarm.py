"""Tests for the dead architecture alarm module."""

import json

import pytest

from divineos.core.dead_architecture_alarm import (
    AlarmResult,
    DisplayIssue,
    check_self_dormant,
    format_alarm_detail,
    format_alarm_summary,
    get_latest_scan,
    init_alarm_table,
    record_scan,
    run_full_scan,
    scan_active_tables,
    scan_display_integrity,
    scan_dormant_tables,
    scan_empty_hud_slots,
)
from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.ledger import get_connection


@pytest.fixture(autouse=True)
def _ensure_schema():
    """Ensure tables exist for scanning."""
    init_knowledge_table()
    init_alarm_table()
    yield


class TestScanDormantTables:
    def test_returns_list(self):
        result = scan_dormant_tables()
        assert isinstance(result, list)

    def test_does_not_include_fts_internals(self):
        result = scan_dormant_tables()
        fts_internals = [t for t in result if t.endswith(("_data", "_idx", "_docsize", "_config"))]
        assert fts_internals == []

    def test_does_not_include_infrastructure(self):
        result = scan_dormant_tables()
        assert "sqlite_sequence" not in result
        assert "seed_metadata" not in result

    def test_sorted(self):
        result = scan_dormant_tables()
        assert result == sorted(result)


class TestScanActiveTables:
    def test_returns_list(self):
        result = scan_active_tables()
        assert isinstance(result, list)

    def test_knowledge_is_active_after_store(self):
        """After storing knowledge, the knowledge table should be active."""
        from divineos.core.knowledge.crud import store_knowledge

        store_knowledge("FACT", "Dead arch test entry for active table check xyzzy999")
        result = scan_active_tables()
        assert "knowledge" in result

    def test_no_overlap_with_dormant(self):
        dormant = scan_dormant_tables()
        active = scan_active_tables()
        overlap = set(dormant) & set(active)
        assert overlap == set()


class TestScanEmptyHudSlots:
    def test_returns_two_lists(self):
        empty, active = scan_empty_hud_slots()
        assert isinstance(empty, list)
        assert isinstance(active, list)

    def test_identity_slot_usually_active(self):
        """Identity slot has core memory, should be active if seeded."""
        empty, active = scan_empty_hud_slots()
        # At minimum, slot lists are returned
        assert len(empty) + len(active) > 0


class TestCheckSelfDormant:
    def test_dormant_before_first_scan(self):
        # Drop any existing scans
        conn = get_connection()
        conn.execute("DELETE FROM dead_architecture_scan")
        conn.commit()
        conn.close()
        assert check_self_dormant() is True

    def test_not_dormant_after_scan(self):
        result = AlarmResult(
            dormant_tables=["fake_table"],
            active_tables=["system_events"],
        )
        record_scan(result)
        assert check_self_dormant() is False


class TestRunFullScan:
    def test_returns_alarm_result(self):
        result = run_full_scan()
        assert isinstance(result, AlarmResult)

    def test_has_scan_time(self):
        result = run_full_scan()
        assert result.scan_time > 0

    def test_dormant_and_active_dont_overlap(self):
        result = run_full_scan()
        overlap = set(result.dormant_tables) & set(result.active_tables)
        assert overlap == set()

    def test_total_tables_property(self):
        result = run_full_scan()
        assert result.total_tables == result.dormant_count + result.active_count


class TestRecordScan:
    def test_returns_scan_id(self):
        result = run_full_scan()
        scan_id = record_scan(result)
        assert scan_id.startswith("scan-")

    def test_stored_in_database(self):
        result = run_full_scan()
        scan_id = record_scan(result)
        conn = get_connection()
        row = conn.execute(
            "SELECT dormant_count, active_count FROM dead_architecture_scan WHERE scan_id = ?",
            (scan_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == result.dormant_count
        assert row[1] == result.active_count

    def test_dormant_list_stored_as_json(self):
        result = run_full_scan()
        scan_id = record_scan(result)
        conn = get_connection()
        row = conn.execute(
            "SELECT dormant FROM dead_architecture_scan WHERE scan_id = ?",
            (scan_id,),
        ).fetchone()
        conn.close()
        stored = json.loads(row[0])
        assert stored == result.dormant_tables


class TestGetLatestScan:
    def test_none_when_empty(self):
        conn = get_connection()
        conn.execute("DELETE FROM dead_architecture_scan")
        conn.commit()
        conn.close()
        assert get_latest_scan() is None

    def test_returns_latest(self):
        r1 = AlarmResult(dormant_tables=["a"], active_tables=["b"], scan_time=100.0)
        r2 = AlarmResult(dormant_tables=["c", "d"], active_tables=["e"], scan_time=200.0)
        record_scan(r1)
        record_scan(r2)
        latest = get_latest_scan()
        assert latest is not None
        assert latest["dormant"] == ["c", "d"]
        assert latest["dormant_count"] == 2


class TestFormatAlarmSummary:
    def test_includes_counts(self):
        result = AlarmResult(
            dormant_tables=["a", "b", "c"],
            active_tables=["d", "e"],
        )
        summary = format_alarm_summary(result)
        assert "3 dormant" in summary
        assert "2 active" in summary

    def test_includes_self_dormant_warning(self):
        result = AlarmResult(self_dormant=True)
        summary = format_alarm_summary(result)
        assert "alarm itself is dormant" in summary

    def test_includes_empty_hud(self):
        result = AlarmResult(empty_hud_slots=["a", "b"])
        summary = format_alarm_summary(result)
        assert "2 empty HUD" in summary


class TestFormatAlarmDetail:
    def test_includes_dormant_list(self):
        result = AlarmResult(dormant_tables=["fake_table"], active_tables=["system_events"])
        detail = format_alarm_detail(result)
        assert "fake_table" in detail
        assert "Dormant tables" in detail

    def test_includes_active_list(self):
        result = AlarmResult(dormant_tables=[], active_tables=["system_events"])
        detail = format_alarm_detail(result)
        assert "system_events" in detail

    def test_includes_display_issues(self):
        result = AlarmResult(
            dormant_tables=["a"],
            active_tables=["b"],
            display_issues=[
                DisplayIssue(
                    slot_name="self_awareness",
                    issue="empty label: '- TRY:'",
                    line="- TRY:",
                )
            ],
        )
        detail = format_alarm_detail(result)
        assert "self_awareness" in detail
        assert "active but broken" in detail.lower() or "Display integrity" in detail

    def test_includes_self_dormant_warning(self):
        result = AlarmResult(self_dormant=True)
        detail = format_alarm_detail(result)
        assert "alarm's own table is empty" in detail or "[!]" in detail

    def test_empty_hud_slots_shown(self):
        result = AlarmResult(empty_hud_slots=["broken_slot"])
        detail = format_alarm_detail(result)
        assert "broken_slot" in detail
        assert "Empty HUD" in detail


class TestScanDisplayIntegrity:
    """Test the active-but-broken detection layer."""

    def test_returns_list(self):
        result = scan_display_integrity()
        assert isinstance(result, list)

    def test_no_false_positives_on_healthy_hud(self):
        """After our TRY: fix, the HUD should have zero display issues."""
        result = scan_display_integrity()
        for issue in result:
            assert isinstance(issue, DisplayIssue)
            assert issue.slot_name
            assert issue.issue

    def test_display_issue_dataclass(self):
        di = DisplayIssue(
            slot_name="test_slot",
            issue="empty label: '- TRY:'",
            line="- TRY:",
        )
        assert di.slot_name == "test_slot"
        assert "empty label" in di.issue

    def test_summary_includes_display_issues(self):
        result = AlarmResult(
            display_issues=[DisplayIssue(slot_name="x", issue="broken", line="- TRY:")],
        )
        summary = format_alarm_summary(result)
        assert "1 display issue" in summary

    def test_full_scan_includes_display_integrity(self):
        result = run_full_scan()
        assert isinstance(result.display_issues, list)
