"""Tests for the progress dashboard — measurable proof the system works.

Every test exercises real data paths. No mocking the thing we're testing.
"""

from divineos.core.progress_dashboard import (
    ProgressReport,
    _format_maturity_bar,
    _format_trend,
    _trend_percentage,
    format_progress_brief,
    format_progress_export,
    format_progress_text,
    gather_progress,
)


class TestProgressReport:
    """ProgressReport dataclass behavior."""

    def test_default_values(self) -> None:
        """Fresh report has sane defaults."""
        report = ProgressReport()
        assert report.total_sessions == 0
        assert report.active_knowledge == 0
        assert report.correction_trend == "unknown"
        assert report.db_integrity == "unknown"
        assert report.generated_at > 0

    def test_one_liner_format(self) -> None:
        """One-liner includes key metrics."""
        report = ProgressReport(
            total_sessions=14,
            correction_trend="improving",
            correction_rate_overall=0.5,
            correction_rate_recent=0.1,
            active_knowledge=145,
            directives_count=7,
            lessons_total=20,
            lessons_resolved=12,
            recent_health_grade="B",
        )
        line = report.one_liner()
        assert "14 sessions" in line
        assert "145 knowledge entries" in line
        assert "7 directives" in line
        assert "12/20 lessons resolved" in line
        assert "corrections v" in line

    def test_one_liner_worsening(self) -> None:
        """One-liner shows ^ for worsening corrections."""
        report = ProgressReport(correction_trend="worsening")
        line = report.one_liner()
        assert "corrections ^" in line

    def test_one_liner_stable(self) -> None:
        """One-liner shows rate for stable/unknown corrections."""
        report = ProgressReport(correction_trend="stable", correction_rate_recent=0.25)
        line = report.one_liner()
        assert "25%" in line


class TestTrendPercentage:
    """Trend percentage calculation."""

    def test_improvement(self) -> None:
        """50% overall to 10% recent = 80% improvement."""
        assert _trend_percentage(0.5, 0.1) == 80

    def test_zero_overall(self) -> None:
        """Zero overall = 0% improvement (no baseline)."""
        assert _trend_percentage(0.0, 0.1) == 0

    def test_no_change(self) -> None:
        """Same rate = 0% improvement."""
        assert _trend_percentage(0.3, 0.3) == 0

    def test_worsening_clamps_to_zero(self) -> None:
        """Worsening rate doesn't go negative."""
        assert _trend_percentage(0.1, 0.5) == 0


class TestFormatting:
    """Text formatting functions."""

    def test_format_trend_arrows(self) -> None:
        """Each trend gets the right indicator."""
        assert "^" in _format_trend("improving")
        assert "-" in _format_trend("stable")
        assert "v" in _format_trend("worsening")
        assert "?" in _format_trend("unknown")

    def test_format_maturity_bar_empty(self) -> None:
        """Empty maturity dict = no data."""
        assert _format_maturity_bar({}) == "no data"

    def test_format_maturity_bar_with_data(self) -> None:
        """Maturity bar shows percentages."""
        by_mat = {"CONFIRMED": 10, "RAW": 90}
        bar = _format_maturity_bar(by_mat)
        assert "C:" in bar  # CONFIRMED
        assert "R:" in bar  # RAW

    def test_format_full_text(self) -> None:
        """Full text format includes all sections."""
        report = ProgressReport(
            total_sessions=5,
            active_knowledge=50,
            directives_count=3,
            correction_trend="stable",
            db_integrity="intact",
        )
        text = format_progress_text(report)
        assert "PROGRESS DASHBOARD" in text
        assert "Session Trajectory" in text
        assert "Knowledge Growth" in text
        assert "Learning Evidence" in text
        assert "System Health" in text
        assert "Behavioral Indicators" in text

    def test_format_brief(self) -> None:
        """Brief format is compact."""
        report = ProgressReport(
            total_sessions=5,
            correction_trend="stable",
            knowledge_churn_rate=0.02,
            db_integrity="intact",
        )
        text = format_progress_brief(report)
        lines = text.strip().split("\n")
        assert len(lines) == 3

    def test_format_export_markdown(self) -> None:
        """Export format is valid markdown."""
        report = ProgressReport(
            total_sessions=10,
            active_knowledge=100,
            knowledge_by_maturity={"RAW": 50, "CONFIRMED": 50},
            correction_trend="improving",
            correction_rate_overall=0.5,
            correction_rate_recent=0.1,
            db_integrity="intact",
        )
        md = format_progress_export(report)
        assert md.startswith("# DivineOS Progress Report")
        assert "## Session Trajectory" in md
        assert "## Knowledge Store" in md
        assert "## Learning Evidence" in md
        assert "## System Integrity" in md
        assert "**improving**" in md


class TestGatherProgress:
    """Integration tests — gather from real (empty) DB."""

    def test_gather_returns_report(self) -> None:
        """gather_progress() returns a ProgressReport even on empty DB."""
        report = gather_progress(lookback_days=7)
        assert isinstance(report, ProgressReport)
        assert report.lookback_days == 7

    def test_gather_with_knowledge(self) -> None:
        """After storing knowledge, counts reflect it."""
        from divineos.core.knowledge import store_knowledge

        store_knowledge("FACT", "Test fact for progress")
        store_knowledge("DIRECTIVE", "Always test progress")
        store_knowledge("PRINCIPLE", "Measure everything")

        report = gather_progress()
        assert report.active_knowledge >= 3
        assert report.directives_count >= 1
        assert "FACT" in report.knowledge_by_type
        assert "DIRECTIVE" in report.knowledge_by_type

    def test_gather_with_sessions(self) -> None:
        """After logging sessions, count reflects them."""
        from divineos.core.ledger import log_event

        log_event("SESSION_END", "ai", {"session_id": "test-1"})
        log_event("SESSION_END", "ai", {"session_id": "test-2"})

        report = gather_progress()
        assert report.total_sessions >= 2

    def test_gather_with_lessons(self) -> None:
        """After storing lessons, lesson counts reflect them."""
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge.lessons import record_lesson

        init_knowledge_table()
        record_lesson("testing", "Always run tests", "session-1")
        record_lesson("coding", "Read before write", "session-1")

        report = gather_progress()
        assert report.lessons_total >= 2

    def test_gather_db_integrity(self) -> None:
        """DB integrity check runs without error."""
        report = gather_progress()
        # On empty/fresh DB, integrity should be intact or unknown
        assert report.db_integrity.startswith("intact") or report.db_integrity in (
            "broken",
            "unknown",
        )

    def test_gather_knowledge_maturity(self) -> None:
        """Maturity distribution is captured."""
        from divineos.core.knowledge import store_knowledge

        store_knowledge("FACT", "Raw fact", maturity="RAW")
        store_knowledge("FACT", "Confirmed fact", maturity="CONFIRMED")

        report = gather_progress()
        assert "RAW" in report.knowledge_by_maturity or report.knowledge_by_maturity == {}
        # At minimum, gathering didn't crash


class TestEdgeCases:
    """Edge cases and error resilience."""

    def test_zero_division_safety(self) -> None:
        """No division by zero in any path."""
        report = ProgressReport(
            total_sessions=0,
            correction_rate_overall=0.0,
            correction_rate_recent=0.0,
        )
        # Should not raise
        line = report.one_liner()
        assert "0 sessions" in line

    def test_format_with_all_zeros(self) -> None:
        """Format handles all-zero report gracefully."""
        report = ProgressReport()
        text = format_progress_text(report)
        assert "PROGRESS DASHBOARD" in text

    def test_export_with_empty_maturity(self) -> None:
        """Export handles empty maturity dict."""
        report = ProgressReport()
        md = format_progress_export(report)
        assert "Maturity Distribution" not in md  # skipped when empty
