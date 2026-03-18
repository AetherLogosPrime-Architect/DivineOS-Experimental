"""Tests for the analysis module."""

import pytest
from pathlib import Path
from divineos.analysis.analysis import analyze_session, format_analysis_report, store_analysis
from divineos.core.ledger import init_db
from divineos.core.consolidation import init_knowledge_table
from divineos.analysis.quality_checks import init_quality_tables
from divineos.analysis.session_features import init_feature_tables


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Initialize database for each test."""
    # Use tmp_path for database
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))

    # Initialize all tables
    init_db()
    init_knowledge_table()
    init_quality_tables()
    init_feature_tables()

    yield

    # Cleanup happens automatically with tmp_path


class TestAnalyzeSession:
    """Test the analyze_session function."""

    def test_analyze_nonexistent_file(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            analyze_session(Path("nonexistent.jsonl"))

    def test_analyze_empty_file(self, tmp_path):
        """Should raise ValueError for empty file."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")

        with pytest.raises(ValueError):
            analyze_session(empty_file)

    def test_analyze_valid_session(self, tmp_path):
        """Should analyze a valid session file."""
        # Create a minimal valid JSONL file (Claude Code format)
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)

        assert result.session_id is not None
        assert result.file_path == str(session_file)
        assert result.timestamp is not None
        assert result.evidence_hash is not None
        assert result.quality_report is not None
        assert result.features is not None


class TestFormatAnalysisReport:
    """Test the format_analysis_report function."""

    def test_format_produces_string(self, tmp_path):
        """Should produce a formatted string."""
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)

        assert isinstance(report, str)
        assert len(report) > 0
        assert "SESSION ANALYSIS REPORT" in report
        assert result.session_id in report

    def test_format_includes_quality_checks(self, tmp_path):
        """Should include quality check results."""
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)

        assert "QUALITY CHECKS" in report

    def test_format_includes_features(self, tmp_path):
        """Should include session features."""
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)

        assert "SESSION FEATURES" in report

    def test_format_no_jargon(self, tmp_path):
        """Should not contain technical jargon."""
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)

        # Check for common jargon that should NOT appear
        jargon_terms = [
            "manifest-receipt",
            "reconciliation",
            "FTS5",
            "dataclass",
            "payload",
        ]

        for term in jargon_terms:
            assert term.lower() not in report.lower(), f"Found jargon: {term}"


class TestStoreAnalysis:
    """Test the store_analysis function."""

    def test_store_analysis_returns_true(self, tmp_path):
        """Should return True on successful storage."""
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        stored = store_analysis(result)

        assert stored is True

    def test_store_analysis_fidelity_verification(self, tmp_path):
        """Should verify data integrity with fidelity checks."""
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        stored = store_analysis(result)

        # If fidelity verification failed, store_analysis would return False
        assert stored is True

    def test_store_analysis_creates_events(self, tmp_path):
        """Should create events in the ledger."""
        from divineos.core.ledger import get_events

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        store_analysis(result)

        # Check that events were created
        events = get_events(limit=100)
        event_types = [e["event_type"] for e in events]

        assert "QUALITY_REPORT" in event_types
        assert "SESSION_FEATURES" in event_types
        assert "SESSION_ANALYSIS" in event_types


class TestGetStoredReport:
    """Test the get_stored_report function."""

    def test_get_stored_report_retrieves_analysis(self, tmp_path):
        """Should retrieve a stored analysis report."""
        from divineos.analysis.analysis import get_stored_report

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        store_analysis(result)

        # Try to retrieve the report
        report = get_stored_report(result.session_id)

        # Should return a formatted report string
        assert report is not None
        assert isinstance(report, str)


class TestListRecentSessions:
    """Test the list_recent_sessions function."""

    def test_list_recent_sessions_with_data(self, tmp_path):
        """Should list recent sessions."""
        from divineos.analysis.analysis import list_recent_sessions

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        store_analysis(result)

        sessions = list_recent_sessions(limit=10)

        assert len(sessions) > 0


class TestComputeCrossSessionTrends:
    """Test the compute_cross_session_trends function."""

    def test_compute_trends_empty(self):
        """Should handle empty session list."""
        from divineos.analysis.analysis import compute_cross_session_trends

        trends = compute_cross_session_trends(limit=10)

        assert isinstance(trends, dict)

    def test_compute_trends_with_data(self, tmp_path):
        """Should compute trends from multiple sessions."""
        from divineos.analysis.analysis import compute_cross_session_trends

        # Create and analyze multiple sessions
        for i in range(2):
            session_file = tmp_path / f"session{i}.jsonl"
            session_file.write_text(
                '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
                '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
            )

            result = analyze_session(session_file)
            store_analysis(result)

        trends = compute_cross_session_trends(limit=10)

        assert isinstance(trends, dict)


class TestFormatCrossSessionReport:
    """Test the format_cross_session_report function."""

    def test_format_cross_session_report(self):
        """Should format cross-session trends."""
        from divineos.analysis.analysis import format_cross_session_report

        trends = {
            "completeness": {"pass_rate": 80, "pass_count": 4, "total_count": 5},
            "correctness": {"pass_rate": 100, "pass_count": 5, "total_count": 5},
        }

        report = format_cross_session_report(trends)

        assert isinstance(report, str)
        assert len(report) > 0
        assert "CROSS-SESSION" in report
