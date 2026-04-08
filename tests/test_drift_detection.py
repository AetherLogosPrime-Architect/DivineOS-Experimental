"""Tests for Drift Detection — catch behavior diverging from principles."""

from divineos.core.drift_detection import (
    detect_correction_trend,
    detect_lesson_regressions,
    detect_quality_drift,
    format_drift_report,
    run_drift_detection,
)


class TestLessonRegressions:
    """Detect lessons that aren't actually improving."""

    def test_detects_high_occurrence_improving(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))

        from divineos.core.knowledge._base import _get_connection, init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        conn = _get_connection()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "l1",
                1000.0,
                "code_quality",
                "Read before you write",
                "s1",
                8,
                1000.0,
                '["s1"]',
                "improving",
                "abc123",
                "test",
            ),
        )
        conn.commit()
        conn.close()

        regressions = detect_lesson_regressions()
        assert len(regressions) == 1
        assert regressions[0]["severity"] == "medium"
        assert regressions[0]["occurrences"] == 8

    def test_high_severity_at_10_occurrences(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))

        from divineos.core.knowledge._base import _get_connection, init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        conn = _get_connection()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "l1",
                1000.0,
                "code_quality",
                "Stop guessing",
                "s1",
                12,
                1000.0,
                '["s1"]',
                "improving",
                "abc123",
                "test",
            ),
        )
        conn.commit()
        conn.close()

        regressions = detect_lesson_regressions()
        assert len(regressions) == 1
        assert regressions[0]["severity"] == "high"

    def test_no_regression_for_low_occurrences(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))

        from divineos.core.knowledge._base import _get_connection, init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        conn = _get_connection()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "l1",
                1000.0,
                "code_quality",
                "New lesson",
                "s1",
                2,
                1000.0,
                '["s1"]',
                "improving",
                "abc123",
                "test",
            ),
        )
        conn.commit()
        conn.close()

        regressions = detect_lesson_regressions()
        assert len(regressions) == 0

    def test_no_table_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "empty.db"))
        regressions = detect_lesson_regressions()
        assert regressions == []


class TestQualityDrift:
    """Detect declining session quality."""

    def test_detects_declining_quality(self):
        # Recent sessions (newest first): bad grades
        payloads = [
            "Session grade: D, 5 corrections",
            "Session grade: F, 8 corrections",
            # Older sessions: good grades
            "Session grade: A, 0 corrections",
            "Session grade: B, 1 corrections",
        ]
        result = detect_quality_drift(min_sessions=3, session_payloads=payloads)
        assert result["drifting"] is True
        assert result["delta"] < 0

    def test_stable_quality(self):
        payloads = [
            "Session grade: B, 2 corrections",
            "Session grade: B, 1 corrections",
            "Session grade: B, 2 corrections",
            "Session grade: B, 1 corrections",
        ]
        result = detect_quality_drift(min_sessions=3, session_payloads=payloads)
        assert result["drifting"] is False

    def test_not_enough_sessions(self):
        result = detect_quality_drift(min_sessions=3, session_payloads=["grade: A"])
        assert result["drifting"] is False
        assert "Not enough" in result["detail"]

    def test_improving_quality(self):
        payloads = [
            "Session grade: A, 0 corrections",
            "Session grade: A, 0 corrections",
            "Session grade: D, 5 corrections",
            "Session grade: F, 8 corrections",
        ]
        result = detect_quality_drift(min_sessions=3, session_payloads=payloads)
        assert result["drifting"] is False
        assert result["delta"] > 0


class TestCorrectionTrend:
    """Detect rising correction counts."""

    def test_detects_increasing_corrections(self):
        payloads = [
            "corrected 15 times this session",
            "corrected 12 times this session",
            "corrected 2 times this session",
            "corrected 1 times this session",
        ]
        result = detect_correction_trend(min_sessions=3, session_payloads=payloads)
        assert result["increasing"] is True

    def test_stable_corrections(self):
        payloads = [
            "corrected 3 times",
            "corrected 3 times",
            "corrected 3 times",
            "corrected 3 times",
        ]
        result = detect_correction_trend(min_sessions=3, session_payloads=payloads)
        assert result["increasing"] is False

    def test_not_enough_data(self):
        result = detect_correction_trend(min_sessions=3, session_payloads=[])
        assert result["increasing"] is False


class TestDriftReport:
    """Full drift detection pipeline."""

    def test_no_drift(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        report = run_drift_detection()
        assert report["severity"] == "none"

    def test_format_no_drift(self):
        report = {
            "regressions": [],
            "quality_drift": {"drifting": False},
            "correction_trend": {"increasing": False},
            "drift_signals": 0,
            "severity": "none",
        }
        output = format_drift_report(report)
        assert "No drift" in output

    def test_format_with_drift(self):
        report = {
            "regressions": [{"detail": "Lesson regressed", "severity": "high"}],
            "quality_drift": {"drifting": True, "detail": "Quality declining"},
            "correction_trend": {"increasing": True, "detail": "Corrections rising"},
            "drift_signals": 4,
            "severity": "medium",
        }
        output = format_drift_report(report)
        assert "MEDIUM" in output
        assert "Lesson regressed" in output
        assert "Quality declining" in output
        assert "Corrections rising" in output
