"""Tests for compass trust tier display integration."""

import ast
import pathlib

import pytest

from divineos.core.moral_compass import (
    _count_observation_tiers,
    _SOURCE_TRUST,
    format_compass_reading,
    init_compass,
    log_observation,
)


def _compass_observation_sources() -> set[str]:
    """All literal source= values passed to log_observation() in the tree.

    AST-based so it sees only real log_observation calls — the timeline /
    holding-room subsystems use a `source=` kwarg too, but on different
    functions, and must NOT be swept in here.
    """
    src_root = pathlib.Path(__file__).resolve().parent.parent / "src" / "divineos"
    found: set[str] = set()
    for path in src_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name != "log_observation":
                continue
            for kw in node.keywords:
                if kw.arg == "source" and isinstance(kw.value, ast.Constant):
                    if isinstance(kw.value.value, str) and kw.value.value:
                        found.add(kw.value.value)
    return found


class TestSourceTrustRegistryComplete:
    """Every compass observation source must be tiered, or it silently
    defaults to SELF_REPORTED — which both under-weights real signals and
    mislabels them in the display. Found 2026-05-23: completion_check (the
    initiative dial's real witness) and three others were defaulting this
    way. This test makes that class of bug un-reintroducible.
    """

    def test_all_log_observation_sources_are_registered(self):
        sources = _compass_observation_sources()
        assert sources, "AST scan found no log_observation source literals — scanner broke"
        unregistered = sorted(s for s in sources if s not in _SOURCE_TRUST)
        assert not unregistered, (
            f"compass observation source(s) not in _SOURCE_TRUST (would silently "
            f"default to SELF_REPORTED): {unregistered}"
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
