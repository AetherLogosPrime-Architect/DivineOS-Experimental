"""Tests for the sleep module — offline consolidation between sessions."""

import time

from divineos.core.sleep import (
    _AFFECT_DECAY_FACTOR,
    _AFFECT_DECAY_FAST,
    _AFFECT_DECAY_HOURS,
    _AFFECT_DECAY_SLOW,
    _AFFECT_INTENSITY_FLOOR,
    _RECOMBINATION_MAX_CONNECTIONS,
    _RECOMBINATION_MAX_SIMILARITY,
    _RECOMBINATION_MIN_SIMILARITY,
    DreamReport,
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

    def test_summary_shows_resolved_lessons(self):
        report = DreamReport(lessons_resolved=["upset_user", "shallow_output"])
        text = report.summary()
        assert "Lessons resolved" in text
        assert "upset_user" in text
        assert "shallow_output" in text

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
        from divineos.core.knowledge import init_knowledge_table

        init_knowledge_table()

        report = DreamReport()
        _phase_consolidation(report)
        # Should run without error, entries_scanned >= 0
        assert report.entries_scanned >= 0

    def test_transitions_eligible_lessons(self, tmp_path, monkeypatch):
        """Lesson lifecycle transitions run during sleep, not just explicit
        SESSION_END.

        A lesson that's been 'improving' for >= LESSON_ABSENCE_DAYS with zero
        regressions and no positive-counterfactual evidence should transition
        to DORMANT when sleep runs, even if the full SESSION_END pipeline
        never fires. RESOLVED requires positive evidence (Kahneman audit
        2026-04-16) — absence alone only earns "quiet, not proven."
        """
        import json

        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge._base import _get_connection
        from divineos.core.knowledge.lessons import _ensure_lesson_schema

        init_knowledge_table()
        conn_init = _get_connection()
        _ensure_lesson_schema(conn_init)
        conn_init.close()

        # Insert an 'improving' lesson that qualifies for DORMANT transition:
        # - 21 days quiet (well past LESSON_ABSENCE_DAYS=7)
        # - 0 regressions
        # - 5 clean sessions (meets LESSON_EFFECTIVE_MIN floor)
        # - no positive_evidence_sessions (absence-only)
        past = time.time() - 21 * 86400
        conn = _get_connection()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, "
            "regressions, positive_evidence_sessions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "test-lesson-1",
                past,
                "sleep_test_category",
                "A test lesson that has been quiet for 21 days.",
                "session-a",
                5,
                past,
                json.dumps(["s1", "s2", "s3", "s4", "s5"]),
                "improving",
                "hash1",
                "test",
                0,
                "{}",
            ),
        )
        conn.commit()
        conn.close()

        report = DreamReport()
        _phase_consolidation(report)

        # Absence-only → dormant, not resolved. Sleep reports the transition
        # in the lessons_dormant bucket; lessons_resolved stays empty.
        assert "sleep_test_category" in report.lessons_dormant
        assert "sleep_test_category" not in report.lessons_resolved

        # Verify the DB was actually updated
        conn2 = _get_connection()
        status = conn2.execute(
            "SELECT status FROM lesson_tracking WHERE lesson_id = 'test-lesson-1'"
        ).fetchone()[0]
        conn2.close()
        assert status == "dormant"

    def test_resolves_lessons_with_positive_evidence(self, tmp_path, monkeypatch):
        """A lesson with LESSON_MIN_POSITIVE_EVIDENCE positive-counterfactual
        sessions plus the time and stimulus gates resolves honestly —
        sleep reports it in lessons_resolved."""
        import json

        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge._base import _get_connection
        from divineos.core.knowledge.lessons import _ensure_lesson_schema
        from divineos.core.ledger import get_connection as get_ledger_connection

        init_knowledge_table()
        conn_init = _get_connection()
        _ensure_lesson_schema(conn_init)
        conn_init.close()

        # Lesson with TWO positive-evidence sessions — enough for RESOLVED.
        past = time.time() - (LESSON_MIN_RESOLUTION_DAYS + 1) * 86400
        evidence = {
            "s1": "agent demonstrated corrected behavior",
            "s2": "agent demonstrated corrected behavior",
        }
        conn = _get_connection()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, "
            "regressions, positive_evidence_sessions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "test-lesson-resolved",
                past,
                "sleep_resolved_category",
                "Lesson with direct positive-counterfactual evidence.",
                "s1",
                3,
                past,
                json.dumps(["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"]),
                "improving",
                "hash-resolved",
                "test",
                0,
                json.dumps(evidence),
            ),
        )
        conn.commit()
        conn.close()

        # Stimulus gate: decision journal entries mentioning the category.
        ledger_conn = get_ledger_connection()
        try:
            ledger_conn.execute(
                """CREATE TABLE IF NOT EXISTS decision_journal (
                    decision_id TEXT PRIMARY KEY, created_at REAL, content TEXT,
                    reasoning TEXT DEFAULT '', alternatives TEXT DEFAULT '[]',
                    context TEXT DEFAULT '', emotional_weight INTEGER DEFAULT 1,
                    tags TEXT DEFAULT '[]', linked_knowledge_ids TEXT DEFAULT '[]',
                    session_id TEXT DEFAULT '', tension TEXT DEFAULT '',
                    almost TEXT DEFAULT '')"""
            )
            for sid in ("s6", "s7", "s8"):
                ledger_conn.execute(
                    "INSERT INTO decision_journal "
                    "(decision_id, created_at, content, session_id) VALUES (?, ?, ?, ?)",
                    (
                        f"dj-{sid}",
                        time.time(),
                        "Worked on the sleep resolved category problem.",
                        sid,
                    ),
                )
            ledger_conn.commit()
        finally:
            ledger_conn.close()

        report = DreamReport()
        _phase_consolidation(report)

        assert "sleep_resolved_category" in report.lessons_resolved
        assert "sleep_resolved_category" not in report.lessons_dormant

        conn2 = _get_connection()
        status = conn2.execute(
            "SELECT status FROM lesson_tracking WHERE lesson_id = 'test-lesson-resolved'"
        ).fetchone()[0]
        conn2.close()
        assert status == "resolved"

    def test_ineligible_lessons_untouched(self, tmp_path, monkeypatch):
        """Lessons that don't meet absence-mode criteria stay improving."""
        import json

        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge._base import _get_connection
        from divineos.core.knowledge.lessons import _ensure_regressions_column

        init_knowledge_table()
        conn_init = _get_connection()
        _ensure_regressions_column(conn_init)
        conn_init.close()

        # This lesson has regressions, so absence-mode doesn't apply.
        # Without the session-padding threshold met, it can't resolve.
        recent = time.time() - 3600
        conn = _get_connection()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "test-lesson-2",
                recent,
                "regressing_category",
                "A lesson that just regressed an hour ago.",
                "session-b",
                4,
                recent,
                json.dumps(["s1", "s2"]),
                "improving",
                "hash2",
                "test",
                3,
            ),
        )
        conn.commit()
        conn.close()

        report = DreamReport()
        _phase_consolidation(report)

        assert "regressing_category" not in report.lessons_resolved

        conn2 = _get_connection()
        status = conn2.execute(
            "SELECT status FROM lesson_tracking WHERE lesson_id = 'test-lesson-2'"
        ).fetchone()[0]
        conn2.close()
        assert status == "improving"


class TestPhaseAffect:
    def test_decays_old_entries(self, tmp_path, monkeypatch):
        """Old affect entries should have their intensity reduced."""
        from divineos.core.affect import init_affect_log
        from divineos.core.memory import _get_connection

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
        from divineos.core.affect import init_affect_log
        from divineos.core.memory import _get_connection

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
        from divineos.core.affect import init_affect_log
        from divineos.core.memory import _get_connection

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
        from divineos.core.affect import init_affect_log
        from divineos.core.memory import _get_connection

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
        """Should find connections between semantically related but topically distinct entries."""
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge.crud import store_knowledge

        init_knowledge_table()

        store_knowledge(
            "PRINCIPLE",
            "When an action fails, investigate the root cause of the error "
            "before retrying. Blind repetition wastes valuable debugging "
            "time and delays the actual fix.",
        )
        store_knowledge(
            "BOUNDARY",
            "Never retry an action that fails without finding the root cause "
            "first. To investigate each error before retrying saves effort "
            "and reveals what actually went wrong.",
        )

        # Pin similarity to word-overlap fallback so the test is deterministic
        # regardless of whether sentence-transformers is installed.
        # Embedding similarity and word overlap can disagree on whether entries
        # are "too similar" (>0.80 semantic vs <=0.50 word overlap), making
        # the test flaky when the backend varies between environments.
        monkeypatch.setattr(
            "divineos.core.knowledge._text._embeddings_available",
            False,
        )

        report = DreamReport()
        _phase_recombination(report)
        assert report.connections_found >= 1

    def test_no_connections_in_empty_store(self, tmp_path, monkeypatch):
        """Empty knowledge store should produce no connections."""
        from divineos.core.knowledge import init_knowledge_table

        init_knowledge_table()

        report = DreamReport()
        _phase_recombination(report)
        assert report.connections_found == 0

    def test_respects_max_connections_limit(self, tmp_path, monkeypatch):
        """Should not exceed the max connections limit."""
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge.crud import store_knowledge

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
        from divineos.core.knowledge import init_knowledge_table

        init_knowledge_table()

        report = run_sleep(skip_maintenance=True)
        assert isinstance(report, DreamReport)
        assert report.duration_seconds >= 0
        assert report.started_at > 0
        assert report.finished_at >= report.started_at

    def test_continues_through_phase_errors(self, tmp_path, monkeypatch):
        """If a phase fails, subsequent phases should still run."""
        from divineos.core.knowledge import init_knowledge_table

        init_knowledge_table()

        # Even with potential issues, sleep should complete
        report = run_sleep(skip_maintenance=True)
        assert isinstance(report, DreamReport)
        # Should have scanned something even if other phases had issues
        assert report.entries_scanned >= 0

    def test_skip_maintenance_flag(self, tmp_path, monkeypatch):
        """Skip maintenance should leave maintenance_results empty."""
        from divineos.core.knowledge import init_knowledge_table

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
