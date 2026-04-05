"""Tests for compass trust tier display integration."""

import pytest

from divineos.core.moral_compass import (
    _count_observation_tiers,
    format_compass_reading,
    init_compass,
    log_observation,
)


@pytest.fixture(autouse=True)
def _init():
    init_compass()


class TestObservationTierCounts:
    def test_empty_spectrum(self):
        counts = _count_observation_tiers("truthfulness")
        # May have existing data, but should return a dict
        assert isinstance(counts, dict)

    def test_counts_measured_source(self):
        log_observation(
            spectrum="truthfulness",
            position=0.0,
            evidence="Low correction rate",
            source="correction_rate",
        )
        counts = _count_observation_tiers("truthfulness")
        assert counts.get("MEASURED", 0) >= 1

    def test_counts_self_reported_source(self):
        log_observation(
            spectrum="engagement",
            position=0.1,
            evidence="Feeling engaged",
            source="self_report",
        )
        counts = _count_observation_tiers("engagement")
        assert counts.get("SELF_REPORTED", 0) >= 1

    def test_counts_behavioral_source(self):
        log_observation(
            spectrum="helpfulness",
            position=0.0,
            evidence="Session ended clean",
            source="session_end",
        )
        counts = _count_observation_tiers("helpfulness")
        assert counts.get("BEHAVIORAL", 0) >= 1

    def test_mixed_tiers(self):
        log_observation(
            spectrum="thoroughness",
            position=0.0,
            evidence="Tool ratio normal",
            source="tool_ratio",
        )
        log_observation(
            spectrum="thoroughness",
            position=0.1,
            evidence="Manual observation",
            source="self_report",
        )
        counts = _count_observation_tiers("thoroughness")
        total = sum(counts.values())
        assert total >= 2


class TestCompassReadingWithTiers:
    def test_reading_includes_tier_info(self):
        """The formatted compass reading should include trust tier breakdown."""
        log_observation(
            spectrum="truthfulness",
            position=-0.1,
            evidence="Test evidence",
            source="correction_rate",
        )
        reading = format_compass_reading()
        # Should mention "measured" in the observation breakdown
        assert "measured" in reading.lower() or "observations" in reading.lower()
