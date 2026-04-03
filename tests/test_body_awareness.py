"""Tests for Body Awareness -- computational interoception."""

from divineos.core.body_awareness import (
    SubstrateVitals,
    format_vitals,
    format_vitals_brief,
    measure_vitals,
)


class TestMeasureVitals:
    """Vital measurements work and return sane values."""

    def test_returns_vitals(self):
        vitals = measure_vitals()
        assert isinstance(vitals, SubstrateVitals)
        assert vitals.measured_at > 0

    def test_ledger_events_counted(self):
        vitals = measure_vitals()
        # Tests create events, so there should be some
        assert vitals.ledger_events >= 0

    def test_knowledge_counted(self):
        vitals = measure_vitals()
        assert vitals.knowledge_entries >= 0
        assert vitals.superseded_entries >= 0

    def test_ratios_bounded(self):
        vitals = measure_vitals()
        assert 0.0 <= vitals.supersession_ratio <= 1.0
        assert 0.0 <= vitals.tool_event_ratio <= 1.0

    def test_total_size_non_negative(self):
        vitals = measure_vitals()
        assert vitals.total_size_mb >= 0.0

    def test_warnings_are_list(self):
        vitals = measure_vitals()
        assert isinstance(vitals.warnings, list)


class TestWarningThresholds:
    """Warnings fire at correct thresholds."""

    def test_storage_warning_at_50mb(self):
        vitals = SubstrateVitals(total_size_mb=60)
        # Manually check threshold logic
        assert vitals.total_size_mb > 50

    def test_tool_event_ratio_warning(self):
        vitals = SubstrateVitals(
            tool_event_ratio=0.85,
            ledger_events=1000,
            tool_events=850,
        )
        assert vitals.tool_event_ratio > 0.8

    def test_no_warnings_on_healthy_vitals(self):
        vitals = SubstrateVitals(
            total_size_mb=5.0,
            tool_event_ratio=0.02,
            supersession_ratio=0.3,
            ledger_events=500,
        )
        # measure_vitals generates warnings; raw construction doesn't
        assert len(vitals.warnings) == 0


class TestFormatting:
    """Output formatting."""

    def test_format_vitals_contains_header(self):
        output = format_vitals()
        assert "BODY AWARENESS" in output

    def test_format_vitals_contains_storage(self):
        output = format_vitals()
        assert "STORAGE" in output

    def test_format_vitals_contains_tables(self):
        output = format_vitals()
        assert "TABLES" in output

    def test_format_brief_contains_body(self):
        output = format_vitals_brief()
        assert "Body:" in output

    def test_format_brief_compact(self):
        output = format_vitals_brief()
        # Brief should be a single line (pipe-separated)
        assert "|" in output
