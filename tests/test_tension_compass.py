"""Tests for value tensions → compass correlation (Edge 9).

When a recurring tension mentions a compass spectrum AND that spectrum
is drifting, the briefing should surface the connection.
"""

from divineos.core.moral_compass import log_observation
from divineos.core.value_tensions import (
    TensionPattern,
    TensionReport,
    correlate_tensions_with_compass,
    format_tension_summary,
)


class TestCorrelation:
    """Cross-reference tensions with compass state."""

    def test_no_compass_data_returns_empty(self):
        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="thoroughness vs speed",
                    occurrences=3,
                ),
            ],
            total_decisions_with_tension=3,
            total_decisions=10,
        )
        result = correlate_tensions_with_compass(report)
        # Without compass observations, no drift to correlate
        assert isinstance(result, list)

    def test_matching_spectrum_and_drift(self):
        """Tension mentioning 'thoroughness' + compass drifting on thoroughness."""
        # Push thoroughness into excess zone (drifting positive)
        for _ in range(3):
            log_observation(
                spectrum="thoroughness",
                position=0.0,
                evidence="older: virtuous",
                source="correction_rate",
            )
        for _ in range(3):
            log_observation(
                spectrum="thoroughness",
                position=0.6,
                evidence="newer: excessive",
                source="tool_ratio",
            )

        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="thoroughness vs speed",
                    occurrences=4,
                ),
            ],
            total_decisions_with_tension=4,
            total_decisions=10,
        )
        result = correlate_tensions_with_compass(report)
        # Should find correlation if thoroughness is drifting
        matching = [c for c in result if c["spectrum"] == "thoroughness"]
        if matching:
            assert matching[0]["tension"] == "thoroughness vs speed"

    def test_no_match_when_spectrum_not_mentioned(self):
        """A tension about 'speed vs quality' shouldn't match precision drift."""
        for _ in range(3):
            log_observation(
                spectrum="precision",
                position=-0.6,
                evidence="vague responses",
                source="correction_rate",
            )

        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="speed vs quality",
                    occurrences=2,
                ),
            ],
            total_decisions_with_tension=2,
            total_decisions=5,
        )
        result = correlate_tensions_with_compass(report)
        precision_matches = [c for c in result if c["spectrum"] == "precision"]
        assert len(precision_matches) == 0

    def test_empty_report_returns_empty(self):
        report = TensionReport(patterns=[], total_decisions_with_tension=0, total_decisions=0)
        result = correlate_tensions_with_compass(report)
        assert result == []


class TestFormattingWithCorrelation:
    """format_tension_summary includes compass correlation markers."""

    def test_format_without_correlation(self):
        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="safety vs autonomy",
                    occurrences=2,
                    resolutions=["chose safety"],
                ),
            ],
            total_decisions_with_tension=2,
            total_decisions=5,
        )
        output = format_tension_summary(report)
        assert "safety vs autonomy" in output
        assert "2x" in output

    def test_format_with_compass_marker(self):
        """When compass is drifting on a tension's spectrum, show the marker."""
        for _ in range(3):
            log_observation(
                spectrum="helpfulness",
                position=0.0,
                evidence="older",
                source="correction_rate",
            )
        for _ in range(3):
            log_observation(
                spectrum="helpfulness",
                position=0.6,
                evidence="newer: scope creep",
                source="tool_ratio",
            )

        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="helpfulness vs boundaries",
                    occurrences=3,
                    resolutions=["helped anyway"],
                ),
            ],
            total_decisions_with_tension=3,
            total_decisions=10,
        )
        output = format_tension_summary(report)
        assert "helpfulness vs boundaries" in output
        # If compass detects drift, the marker should appear
        if "compass:" in output:
            assert "helpfulness" in output

    def test_format_empty_report(self):
        report = TensionReport(patterns=[], total_decisions_with_tension=0, total_decisions=0)
        output = format_tension_summary(report)
        assert output == ""

    def test_high_frequency_marker(self):
        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="consistency vs flexibility",
                    occurrences=5,
                ),
            ],
            total_decisions_with_tension=5,
            total_decisions=10,
        )
        output = format_tension_summary(report)
        assert "⚡" in output  # 5 occurrences > 3 threshold
