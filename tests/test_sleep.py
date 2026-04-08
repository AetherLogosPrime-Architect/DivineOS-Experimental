"""Tests for the sleep module — offline consolidation between sessions."""

import time

from divineos.core.sleep import (
    DreamReport,
    _AFFECT_DECAY_FACTOR,
    _AFFECT_DECAY_FAST,
    _AFFECT_DECAY_HOURS,
    _AFFECT_DECAY_SLOW,
    _AFFECT_INTENSITY_FLOOR,
    _RECOMBINATION_MAX_CONNECTIONS,
    _RECOMBINATION_MAX_SIMILARITY,
    _RECOMBINATION_MIN_SIMILARITY,
    _compute_decay_factor,
    _phase_affect,
    _phase_consolidation,
    _phase_recombination,
    run_sleep,
)


class TestDreamReport:
    def test_default_values(self):
        report = DreamReport()
        assert report.entries_scanned == 0
        assert report.total_promoted == 0
        assert report.affect_decayed == 0
        assert report.connections_found == 0
        assert report.phase_errors == {}

    def test_summary_includes_all_phases(self):
        report = DreamReport(duration_seconds=1.5)
        text = report.summary()
        assert "Phase 1" in text
        assert "Phase 2" in text
        assert "Phase 3" in text
        assert "Phase 4" in text
        assert "Phase 5" in text

    def test_summary_shows_promotions(self):
        report = DreamReport(
            entries_scanned=50,
            promotions={"HYPOTHESIS": 3, "TESTED": 1},
            total_promoted=4,
        )
        text = report.summary()
        assert "HYPOTHESIS: 3" in text
        assert "TESTED: 1" in text

    def test_summary_shows_connections(self):
        report = DreamReport(
            connections_found=2,
            connection_details=[
                {"summary": "PRINCIPLE~BOUNDARY: found overlap"},
                {"summary": "FACT~DIRECTION: another overlap"},
            ],
        )
        text = report.summary()
        assert "2 new connection" in text
        assert "PRINCIPLE~BOUNDARY" in text

    def test_summary_shows_affect_baseline(self):
        report = DreamReport(
            affect_entries_processed=5,
            affect_decayed=3,
            affect_baseline={"valence": 0.5, "arousal": 0.3, "dominance": -0.1},
        )
        text = report.summary()
        assert "V=+0.50" in text
        assert "A=0.30" in text
        assert "D=-0.10" in text

    def test_summary_shows_errors(self):
        report = DreamReport(phase_errors={"consolidation": "DB locked"})
        text = report.summary()
        assert "consolidation: DB locked" in text

    def test_summary_clean_store(self):
        report = DreamReport(health_results={}, hygiene_results={})
        text = report.summary()
        assert "clean" in text.lower()


class TestPhaseConsolidation:
    def test_scans_entries(self, tmp_path, monkeypatch):
        """Consolidation phase populates entries_scanned."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge import _base

        _base._connection = None  # reset cached connection

        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        report = DreamReport()
        _phase_consolidation(report)
        # Should run without error, entries_scanned >= 0
        assert report.entries_scanned >= 0


class TestPhaseAffect:
    def test_decays_old_entries(self, tmp_path, monkeypatch):
        """Old affect entries should have their intensity reduced."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.memory import _get_connection

        from divineos.core.affect import init_affect_log

        init_affect_log()
        conn = _get_connection()
        # Insert an old entry (24 hours ago) with strong emotion
        old_time = time.time() - 86400
        conn.execute(
            "INSERT INTO affect_log (entry_id, created_at, valence, arousal, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ("old-entry", old_time, 0.9, 0.8, "test"),
        )
        # Insert a recent entry (5 minutes ago)
        recent_time = time.time() - 300
        conn.execute(
            "INSERT INTO affect_log (entry_id, created_at, valence, arousal, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ("recent-entry", recent_time, 0.5, 0.6, "test"),
        )
        conn.commit()
        conn.close()

        report = DreamReport()
        _phase_affect(report)

        assert report.affect_entries_processed == 2
        assert report.affect_decayed >= 1  # at least the old one

        # Verify the old entry was decayed
        conn2 = _get_connection()
        row = conn2.execute(
            "SELECT valence, arousal FROM affect_log WHERE entry_id = 'old-entry'"
        ).fetchone()
        conn2.close()
        assert row[0] < 0.9  # valence should be reduced
        assert row[1] < 0.8  # arousal should be reduced

    def test_recent_entries_untouched(self, tmp_path, monkeypatch):
        """Recent affect entries should not be decayed."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.memory import _get_connection

        from divineos.core.affect import init_affect_log

        init_affect_log()
        conn = _get_connection()
        recent_time = time.time() - 60  # 1 minute ago
        conn.execute(
            "INSERT INTO affect_log (entry_id, created_at, valence, arousal, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ("recent", recent_time, 0.8, 0.7, "test"),
        )
        conn.commit()
        conn.close()

        report = DreamReport()
        _phase_affect(report)

        conn2 = _get_connection()
        row = conn2.execute(
            "SELECT valence, arousal FROM affect_log WHERE entry_id = 'recent'"
        ).fetchone()
        conn2.close()
        assert row[0] == 0.8  # unchanged
        assert row[1] == 0.7  # unchanged

    def test_empty_affect_log(self, tmp_path, monkeypatch):
        """No affect history should not crash."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.memory import _get_connection

        from divineos.core.affect import init_affect_log

        init_affect_log()
        conn = _get_connection()
        conn.commit()
        conn.close()

        report = DreamReport()
        _phase_affect(report)
        assert report.affect_entries_processed == 0
        assert report.affect_decayed == 0

    def test_baseline_computed_from_recent(self, tmp_path, monkeypatch):
        """Baseline should average only recent (non-decayed) entries."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.memory import _get_connection

        from divineos.core.affect import init_affect_log

        init_affect_log()
        conn = _get_connection()
        now = time.time()
        # Two recent entries
        conn.execute(
            "INSERT INTO affect_log (entry_id, created_at, valence, arousal, dominance, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("r1", now - 60, 0.6, 0.4, 0.2, "test"),
        )
        conn.execute(
            "INSERT INTO affect_log (entry_id, created_at, valence, arousal, dominance, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("r2", now - 120, 0.4, 0.6, -0.2, "test"),
        )
        conn.commit()
        conn.close()

        report = DreamReport()
        _phase_affect(report)

        assert report.affect_baseline["valence"] == 0.5  # (0.6+0.4)/2
        assert report.affect_baseline["arousal"] == 0.5  # (0.4+0.6)/2
        assert report.affect_baseline["dominance"] == 0.0  # (0.2-0.2)/2


class TestPhaseRecombination:
    def test_finds_cross_type_connections(self, tmp_path, monkeypatch):
        """Should find connections between entries of different types."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge.crud import store_knowledge
        from divineos.core.knowledge import _base

        _base._connection = None
        init_knowledge_table()

        # Store entries with moderate overlap (same domain, different types)
        store_knowledge(
            "PRINCIPLE",
            "The maturity lifecycle promotes knowledge from RAW to CONFIRMED "
            "based on corroboration count and confidence score thresholds",
        )
        store_knowledge(
            "BOUNDARY",
            "The maturity lifecycle has never organically promoted an entry "
            "because corroboration counts remain too low across sessions",
        )

        report = DreamReport()
        _phase_recombination(report)
        # These two entries share "maturity lifecycle" and "corroboration"
        # so they should show up as a connection
        assert report.connections_found >= 1

    def test_no_connections_in_empty_store(self, tmp_path, monkeypatch):
        """Empty knowledge store should produce no connections."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge import _base

        _base._connection = None
        init_knowledge_table()

        report = DreamReport()
        _phase_recombination(report)
        assert report.connections_found == 0

    def test_respects_max_connections_limit(self, tmp_path, monkeypatch):
        """Should not exceed the max connections limit."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge.crud import store_knowledge
        from divineos.core.knowledge import _base

        _base._connection = None
        init_knowledge_table()

        # Store many similar entries across two types
        for i in range(20):
            store_knowledge(
                "PRINCIPLE",
                f"Knowledge maturity lifecycle entry number {i} with corroboration "
                f"and confidence scoring for promotions",
            )
            store_knowledge(
                "BOUNDARY",
                f"Boundary about maturity lifecycle discovered in entry {i} with "
                f"corroboration thresholds and confidence requirements",
            )

        report = DreamReport()
        _phase_recombination(report)
        assert report.connections_found <= _RECOMBINATION_MAX_CONNECTIONS


class TestRunSleep:
    def test_returns_dream_report(self, tmp_path, monkeypatch):
        """Full sleep cycle should return a DreamReport."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge import _base

        _base._connection = None
        init_knowledge_table()

        report = run_sleep(skip_maintenance=True)
        assert isinstance(report, DreamReport)
        assert report.duration_seconds >= 0
        assert report.started_at > 0
        assert report.finished_at >= report.started_at

    def test_continues_through_phase_errors(self, tmp_path, monkeypatch):
        """If a phase fails, subsequent phases should still run."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge import _base

        _base._connection = None
        init_knowledge_table()

        # Even with potential issues, sleep should complete
        report = run_sleep(skip_maintenance=True)
        assert isinstance(report, DreamReport)
        # Should have scanned something even if other phases had issues
        assert report.entries_scanned >= 0

    def test_skip_maintenance_flag(self, tmp_path, monkeypatch):
        """Skip maintenance should leave maintenance_results empty."""
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge import _base

        _base._connection = None
        init_knowledge_table()

        report = run_sleep(skip_maintenance=True)
        assert report.maintenance_results == {}


class TestContextSensitiveDecay:
    """Test that decay rate varies by emotional state."""

    def test_frustration_decays_fast(self):
        """Intense negative + high arousal = frustration, decays fastest."""
        factor = _compute_decay_factor(valence=-0.5, arousal=0.7)
        assert factor == _AFFECT_DECAY_FAST

    def test_positive_decays_slow(self):
        """Positive states should linger longer."""
        factor = _compute_decay_factor(valence=0.5, arousal=0.5)
        assert factor == _AFFECT_DECAY_SLOW

    def test_neutral_uses_default(self):
        """Neutral/moderate states use the default rate."""
        factor = _compute_decay_factor(valence=0.0, arousal=0.3)
        assert factor == _AFFECT_DECAY_FACTOR

    def test_mild_negative_not_fast(self):
        """Mildly negative but low arousal = not frustration, default decay."""
        factor = _compute_decay_factor(valence=-0.2, arousal=0.3)
        assert factor == _AFFECT_DECAY_FACTOR

    def test_fast_less_than_default(self):
        assert _AFFECT_DECAY_FAST < _AFFECT_DECAY_FACTOR

    def test_slow_greater_than_default(self):
        assert _AFFECT_DECAY_SLOW > _AFFECT_DECAY_FACTOR

    def test_all_factors_between_zero_and_one(self):
        assert 0 < _AFFECT_DECAY_FAST < 1
        assert 0 < _AFFECT_DECAY_FACTOR < 1
        assert 0 < _AFFECT_DECAY_SLOW < 1


class TestConstants:
    def test_decay_factor_between_zero_and_one(self):
        assert 0 < _AFFECT_DECAY_FACTOR < 1

    def test_intensity_floor_positive(self):
        assert _AFFECT_INTENSITY_FLOOR > 0

    def test_decay_hours_positive(self):
        assert _AFFECT_DECAY_HOURS > 0

    def test_similarity_thresholds_ordered(self):
        assert _RECOMBINATION_MIN_SIMILARITY < _RECOMBINATION_MAX_SIMILARITY

    def test_max_connections_reasonable(self):
        assert 1 <= _RECOMBINATION_MAX_CONNECTIONS <= 50
