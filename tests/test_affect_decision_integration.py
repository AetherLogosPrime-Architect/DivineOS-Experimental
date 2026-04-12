"""Tests for affect-decision integration — auto-linking and context retrieval."""

import pytest

import divineos.core.ledger as ledger_mod
from divineos.core.affect import (
    describe_affect,
    get_recent_affect,
    init_affect_log,
    log_affect,
)
from divineos.core.decision_journal import (
    get_affect_at_decision,
    init_decision_journal,
    record_decision,
)
from divineos.core.ledger import init_db
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: test_db)
    init_db()
    init_memory_tables()
    init_affect_log()
    init_decision_journal()
    yield


class TestDescribeAffect:
    def test_engaged_resonant(self):
        assert describe_affect(0.8, 0.7) == "engaged-resonant"

    def test_calm_aligned(self):
        assert describe_affect(0.5, 0.3) == "calm-aligned"

    def test_tense_dissonant(self):
        assert describe_affect(-0.5, 0.8) == "tense-dissonant"

    def test_flat_distant(self):
        assert describe_affect(-0.4, 0.2) == "flat-distant"

    def test_alert_neutral(self):
        assert describe_affect(0.0, 0.7) == "alert-neutral"

    def test_idle(self):
        assert describe_affect(0.1, 0.3) == "idle"


class TestGetRecentAffect:
    def test_returns_recent_entry(self):
        log_affect(0.8, 0.6, description="focused")
        result = get_recent_affect(within_seconds=60.0)
        assert result is not None
        assert result["valence"] == 0.8
        assert result["description"] == "focused"

    def test_returns_none_when_empty(self):
        assert get_recent_affect(within_seconds=60.0) is None

    def test_returns_none_when_too_old(self):
        log_affect(0.5, 0.5, description="old")
        # Can't easily make it old, but within_seconds=0 should find nothing
        assert get_recent_affect(within_seconds=0.0) is None


class TestAutoLinkAffectToDecision:
    def test_record_decision_auto_links_recent_affect(self):
        log_affect(0.7, 0.8, description="energized")
        decision_id = record_decision("Use SQLite for storage", reasoning="Simple and reliable")

        # The affect entry should now have linked_decision_id set
        affect = get_affect_at_decision(decision_id)
        assert affect is not None
        assert affect["linked_decision_id"] == decision_id

    def test_record_decision_no_crash_without_affect(self):
        # Should not crash when no affect entries exist
        decision_id = record_decision("Test decision", reasoning="Just testing")
        assert decision_id is not None


class TestGetAffectAtDecision:
    def test_finds_closest_affect(self):
        log_affect(0.3, 0.3, description="calm")
        log_affect(0.9, 0.9, description="excited")
        decision_id = record_decision("Big choice", reasoning="Important")

        affect = get_affect_at_decision(decision_id)
        assert affect is not None
        # Should find the most recent (closest in time) — "excited"
        assert affect["description"] == "excited"

    def test_returns_none_for_missing_decision(self):
        assert get_affect_at_decision("nonexistent-id") is None

    def test_auto_logs_affect_when_none_recent(self, tmp_path, monkeypatch):
        # record_decision now auto-logs affect when no recent affect exists.
        # This verifies the event-triggered affect capture works.
        fresh_db = tmp_path / "fresh.db"
        monkeypatch.setattr(ledger_mod, "DB_PATH", fresh_db)
        monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: fresh_db)
        init_db()
        init_memory_tables()
        init_decision_journal()
        decision_id = record_decision("Test", reasoning="test")
        affect = get_affect_at_decision(decision_id)
        assert affect is not None
        assert affect["trigger"] == "decision_recorded"
        assert affect["valence"] == 0.3  # WEIGHT_ROUTINE default
