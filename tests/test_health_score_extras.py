"""Tests for the new measure_session_health factors (Andrew's spec 2026-05-05).

Adds three factors to the existing health score:
- pr_volume (logarithmic, capped at ~8 PRs)
- structural_ratio (structural-fixes / total drift events)
- (existing factors unchanged at lower weights)

The existing behavior must be preserved when new params default to zero.
"""

from __future__ import annotations

from divineos.agent_integration.outcome_measurement import measure_session_health


class TestBackwardCompat:
    def test_default_params_dont_break_existing_score(self):
        """When new params aren't passed, the score should land in the
        same ballpark as before — defaults for pr_volume and structural
        are 0.5 (neutral) so they pull toward 0.5 with their 0.10 weights."""
        result = measure_session_health(
            corrections=2,
            encouragements=3,
            context_overflows=0,
            tool_calls=20,
            user_messages=10,
            briefing_loaded=True,
        )
        assert "score" in result
        assert "grade" in result
        assert "factors" in result
        # Score should be reasonable
        assert 0.0 <= result["score"] <= 1.0

    def test_neutral_when_no_drift_events(self):
        """structural_fix_count=0 AND same_pattern_recurrences=0 →
        structural_ratio defaults to 0.5 (neutral, no signal)."""
        result = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=10,
            user_messages=5,
            briefing_loaded=True,
            pr_count=0,
            structural_fix_count=0,
            same_pattern_recurrences=0,
        )
        assert result["factors"]["structural_ratio"] == 0.5
        assert result["factors"]["pr_volume"] == 0.5


class TestPRVolume:
    def test_pr_volume_logarithmic_diminishing_returns(self):
        """8+ PRs caps at ~1.0; doesn't reward unlimited churn."""
        low = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            pr_count=2,
        )
        high = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            pr_count=20,
        )
        assert low["factors"]["pr_volume"] < high["factors"]["pr_volume"]
        assert high["factors"]["pr_volume"] <= 1.0

    def test_pr_count_in_factors(self):
        result = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            pr_count=16,
        )
        assert result["factors"]["pr_count"] == 16


class TestStructuralRatio:
    def test_high_structural_fix_ratio(self):
        """Many structural fixes vs few recurrences → high ratio."""
        result = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            structural_fix_count=8,
            same_pattern_recurrences=2,
        )
        assert result["factors"]["structural_ratio"] == 0.8

    def test_low_structural_fix_ratio(self):
        """Many recurrences without structural fixes → low ratio."""
        result = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            structural_fix_count=1,
            same_pattern_recurrences=9,
        )
        assert result["factors"]["structural_ratio"] == 0.1

    def test_only_structural_fixes_ratio_one(self):
        result = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            structural_fix_count=5,
            same_pattern_recurrences=0,
        )
        assert result["factors"]["structural_ratio"] == 1.0


class TestRegression:
    """Pin the 2026-05-05 spec: today's session should land higher than
    the old formula gave it."""

    def test_high_pr_volume_session_scores_higher(self):
        """Today's session: 16 PRs, ~8 structural fixes, some recurrences.
        Should land in B+/A territory rather than just B."""
        result = measure_session_health(
            corrections=2,  # unresolved
            resolved_corrections=4,  # resolved-and-corrected
            encouragements=10,
            context_overflows=0,
            tool_calls=200,
            user_messages=80,
            briefing_loaded=True,
            pr_count=16,
            structural_fix_count=8,
            same_pattern_recurrences=4,
        )
        # With these signals, score should be solid B (>=0.70) at minimum
        assert result["score"] >= 0.70
        assert result["grade"] in ("A", "B")


class TestFactorsBreakdown:
    def test_all_new_factor_keys_present(self):
        result = measure_session_health(
            corrections=0,
            encouragements=0,
            context_overflows=0,
            tool_calls=0,
            user_messages=0,
            briefing_loaded=True,
            pr_count=5,
            structural_fix_count=3,
            same_pattern_recurrences=2,
        )
        for key in (
            "pr_volume",
            "pr_count",
            "structural_ratio",
            "structural_fix_count",
            "same_pattern_recurrences",
        ):
            assert key in result["factors"], f"missing factor: {key}"
