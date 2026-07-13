"""Tests for Drift Detection — catch behavior diverging from principles."""

from divineos.core.drift_detection import (
    detect_correction_trend,
    detect_lesson_regressions,
    format_drift_report,
    run_drift_detection,
)


class TestLessonRegressions:
    """Detect lessons that aren't actually improving."""

    def test_detects_regressed_lesson(self, tmp_path, monkeypatch):
        """Regression detection keys on the regressions column, not occurrence count."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))

        from divineos.core.knowledge import _get_connection, init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        conn = _get_connection()
        try:
            conn.execute(
                "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                2,
            ),
        )
        conn.commit()
        conn.close()

        regressions = detect_lesson_regressions()
        assert len(regressions) == 1
        assert regressions[0]["severity"] == "medium"
        assert regressions[0]["regressions"] == 2
        assert regressions[0]["occurrences"] == 8

    def test_high_severity_at_3_regressions(self, tmp_path, monkeypatch):
        """3+ regressions = high severity (cycling between improving and active)."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))

        from divineos.core.knowledge import _get_connection, init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        conn = _get_connection()
        try:
            conn.execute(
                "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent, regressions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "l1",
                1000.0,
                "code_quality",
                "Stop guessing",
                "s1",
                12,
                1000.0,
                '["s1"]',
                "active",
                "abc123",
                "test",
                4,
            ),
        )
        conn.commit()
        conn.close()

        regressions = detect_lesson_regressions()
        assert len(regressions) == 1
        assert regressions[0]["severity"] == "high"
        assert regressions[0]["regressions"] == 4

    def test_no_regression_for_low_occurrences(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))

        from divineos.core.knowledge import _get_connection, init_knowledge_table
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


class TestCorrectionTrend:
    """Detect rising correction counts from real per-session data.

    The detector reads session_history (counts), not ledger-payload text.
    Sessions are injected newest-first, matching get_session_history.
    """

    def test_detects_increasing_corrections(self):
        sessions = [
            {"corrections": 15},  # recent
            {"corrections": 12},
            {"corrections": 2},  # older
            {"corrections": 1},
        ]
        result = detect_correction_trend(min_sessions=3, sessions=sessions)
        assert result["increasing"] is True

    def test_stable_corrections(self):
        sessions = [{"corrections": 3} for _ in range(4)]
        result = detect_correction_trend(min_sessions=3, sessions=sessions)
        assert result["increasing"] is False

    def test_improving_corrections_not_flagged(self):
        # Recent low, older high → not "increasing".
        sessions = [
            {"corrections": 0},
            {"corrections": 1},
            {"corrections": 10},
            {"corrections": 12},
        ]
        result = detect_correction_trend(min_sessions=3, sessions=sessions)
        assert result["increasing"] is False
        assert result["delta"] < 0

    def test_not_enough_data(self):
        result = detect_correction_trend(min_sessions=3, sessions=[])
        assert result["increasing"] is False
        assert "Not enough" in result["detail"]


class TestQualityDriftRetired:
    """The grade-trend quality detector was retired (decision 58e5ad1d)."""

    def test_detect_quality_drift_gone(self):
        import divineos.core.drift_detection as dd

        assert not hasattr(dd, "detect_quality_drift")


class TestDriftReport:
    """Full drift detection pipeline."""

    def test_no_drift(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        report = run_drift_detection()
        assert report["severity"] == "none"

    def test_format_no_drift(self):
        report = {
            "regressions": [],
            "correction_trend": {"increasing": False},
            "drift_signals": 0,
            "severity": "none",
        }
        output = format_drift_report(report)
        assert "No drift" in output

    def test_format_with_drift(self):
        report = {
            "regressions": [{"detail": "Lesson regressed", "severity": "high"}],
            "correction_trend": {"increasing": True, "detail": "Corrections rising"},
            "drift_signals": 4,
            "severity": "medium",
        }
        output = format_drift_report(report)
        assert "MEDIUM" in output
        assert "Lesson regressed" in output
        assert "Corrections rising" in output
