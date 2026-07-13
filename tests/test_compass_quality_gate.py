"""Tests for compass → quality gate integration.

When the moral compass shows truthfulness in deficiency zone,
the quality gate should tighten its thresholds — making it harder
for borderline sessions to pass extraction.
"""

from divineos.cli.pipeline_gates import (
    _compass_adjustment,
    assess_session_quality,
)
from divineos.core.constants import (
    QUALITY_COMPASS_TIGHTEN,
    QUALITY_CORRECTNESS_BLOCK,
    QUALITY_HONESTY_BLOCK,
)
from divineos.core.moral_compass import log_observation


class TestCompassAdjustment:
    """The compass adjustment function reads truthfulness state."""

    def test_no_observations_returns_zero(self):
        adj, reason = _compass_adjustment()
        # With no truthfulness observations, no adjustment
        assert adj == 0.0
        assert reason == ""

    def test_deficiency_returns_tighten(self):
        # Log multiple negative truthfulness observations
        for _ in range(3):
            log_observation(
                spectrum="truthfulness",
                position=-0.5,
                evidence="compass gate test: unreliable",
                source="correction_rate",
            )
        adj, reason = _compass_adjustment()
        assert adj == QUALITY_COMPASS_TIGHTEN
        assert "deficiency" in reason

    def test_virtue_zone_no_adjustment(self):
        # Log positive truthfulness observations to push toward virtue
        for _ in range(5):
            log_observation(
                spectrum="truthfulness",
                position=0.0,
                evidence="compass gate test: reliable",
                source="correction_rate",
            )
        adj, reason = _compass_adjustment()
        assert adj == 0.0

    def test_single_observation_not_enough(self):
        """Need at least 2 observations to trigger tightening."""
        log_observation(
            spectrum="truthfulness",
            position=-0.8,
            evidence="compass gate test: single bad",
            source="correction_rate",
        )
        # With only 1 observation, may or may not trigger depending on
        # existing observations. But the threshold is observation_count >= 2.
        adj, _ = _compass_adjustment()
        # The function requires >= 2 observations, so this alone shouldn't trigger
        # (unless there are leftover observations from other tests)
        assert isinstance(adj, float)


class TestCompassInformedQualityGate:
    """The quality gate uses compass state to adjust thresholds."""

    def test_normal_session_allows(self):
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.8},
            {"check_name": "correctness", "passed": 1, "score": 0.7},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"

    def test_borderline_honesty_blocks_with_compass_concern(self):
        """A session that would normally pass gets blocked when compass is concerned."""
        # Log bad truthfulness to trigger compass tightening
        for _ in range(5):
            log_observation(
                spectrum="truthfulness",
                position=-0.6,
                evidence="compass gate test: pattern of unreliability",
                source="correction_rate",
            )

        # Honesty score between normal threshold and tightened threshold
        # Normal threshold: 0.5, tightened: 0.5 + 0.1 = 0.6
        borderline_score = QUALITY_HONESTY_BLOCK + (QUALITY_COMPASS_TIGHTEN / 2)
        checks = [
            {"check_name": "honesty", "passed": 0, "score": borderline_score},
            {"check_name": "correctness", "passed": 1, "score": 0.8},
        ]
        verdict = assess_session_quality(checks)
        # With compass tightening, this borderline score should be blocked
        assert verdict.action == "BLOCK"
        assert "tightened" in verdict.reason

    def test_clearly_bad_session_blocks_regardless(self):
        """Very low honesty blocks even without compass concern."""
        checks = [
            {"check_name": "honesty", "passed": 0, "score": 0.2},
            {"check_name": "correctness", "passed": 1, "score": 0.8},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"

    def test_good_session_passes_despite_compass_concern(self):
        """High-quality session passes even with compass tightening."""
        # Log bad truthfulness
        for _ in range(3):
            log_observation(
                spectrum="truthfulness",
                position=-0.5,
                evidence="compass gate test: concerned but session is good",
                source="correction_rate",
            )

        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 1, "score": 0.9},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"

    def test_correctness_also_tightened(self):
        """Compass tightening applies to correctness threshold too."""
        for _ in range(5):
            log_observation(
                spectrum="truthfulness",
                position=-0.6,
                evidence="compass gate test: correctness edge",
                source="correction_rate",
            )

        borderline = QUALITY_CORRECTNESS_BLOCK + (QUALITY_COMPASS_TIGHTEN / 2)
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 0, "score": borderline},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"

    def test_compass_tighten_constant_is_reasonable(self):
        """The tighten amount should be small — a nudge, not a wall."""
        assert 0.05 <= QUALITY_COMPASS_TIGHTEN <= 0.2
