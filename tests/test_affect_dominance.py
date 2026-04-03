"""Tests for Affect Dominance — the third PAD dimension.

Dominance tracks coping potential: who is driving the interaction?
-1.0 = submissive/guided, +1.0 = dominant/driving.
"""

from unittest.mock import patch

from divineos.core.affect import (
    compute_affect_modifiers,
    describe_affect,
    get_affect_history,
    get_affect_summary,
    log_affect,
)


class TestLogAffectDominance:
    """Dominance is stored and retrieved correctly."""

    def test_log_with_dominance(self):
        entry_id = log_affect(valence=0.5, arousal=0.6, dominance=0.3, description="confident")
        assert entry_id
        history = get_affect_history(limit=1)
        assert history[0]["dominance"] == 0.3

    def test_log_without_dominance(self):
        entry_id = log_affect(valence=0.5, arousal=0.6, description="no dominance")
        assert entry_id
        history = get_affect_history(limit=1)
        assert history[0]["dominance"] is None

    def test_dominance_clamped_high(self):
        log_affect(valence=0.0, arousal=0.5, dominance=2.5)
        history = get_affect_history(limit=1)
        assert history[0]["dominance"] == 1.0

    def test_dominance_clamped_low(self):
        log_affect(valence=0.0, arousal=0.5, dominance=-3.0)
        history = get_affect_history(limit=1)
        assert history[0]["dominance"] == -1.0


class TestAffectSummaryDominance:
    """Summary stats include dominance."""

    def test_summary_includes_avg_dominance(self):
        # Log several entries with dominance
        for d in [0.2, 0.4, 0.6]:
            log_affect(valence=0.5, arousal=0.5, dominance=d)
        summary = get_affect_summary(limit=3)
        assert "avg_dominance" in summary
        assert summary["avg_dominance"] > 0

    def test_summary_handles_mixed_null_dominance(self):
        # Some with, some without dominance
        log_affect(valence=0.5, arousal=0.5, dominance=0.8)
        log_affect(valence=0.5, arousal=0.5)  # No dominance
        summary = get_affect_summary(limit=2)
        # avg_dominance computed only from non-null entries
        assert "avg_dominance" in summary
        assert summary["avg_dominance"] == 0.8

    def test_summary_no_dominance_entries(self):
        log_affect(valence=0.3, arousal=0.3)
        log_affect(valence=0.4, arousal=0.4)
        summary = get_affect_summary(limit=2)
        assert summary["avg_dominance"] == 0.0
        assert summary["dominance_range"] == (0.0, 0.0)


class TestDescribeAffectOctants:
    """describe_affect uses eight PAD octants when dominance is provided."""

    def test_exuberant(self):
        assert describe_affect(0.5, 0.7, 0.5) == "exuberant"

    def test_dependent(self):
        assert describe_affect(0.5, 0.7, -0.5) == "dependent"

    def test_relaxed(self):
        assert describe_affect(0.5, 0.3, 0.5) == "relaxed"

    def test_docile(self):
        assert describe_affect(0.5, 0.3, -0.5) == "docile"

    def test_hostile(self):
        assert describe_affect(-0.5, 0.7, 0.5) == "hostile"

    def test_anxious(self):
        assert describe_affect(-0.5, 0.7, -0.5) == "anxious"

    def test_disdainful(self):
        assert describe_affect(-0.5, 0.3, 0.5) == "disdainful"

    def test_bored(self):
        assert describe_affect(-0.5, 0.3, -0.5) == "bored"

    def test_no_dominance_falls_back_to_quadrants(self):
        # Without dominance, uses the old 2D mapping
        assert describe_affect(0.5, 0.7) == "engaged-resonant"
        assert describe_affect(0.5, 0.3) == "calm-aligned"
        assert describe_affect(-0.5, 0.7) == "tense-dissonant"
        assert describe_affect(-0.5, 0.3) == "flat-distant"

    def test_none_dominance_same_as_no_dominance(self):
        assert describe_affect(0.5, 0.7, None) == "engaged-resonant"


class TestModifiersIncludeDominance:
    """compute_affect_modifiers returns avg_dominance."""

    def test_modifiers_include_avg_dominance(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": 0.3,
                "avg_arousal": 0.4,
                "avg_dominance": 0.5,
                "trend": "stable",
            }
            mods = compute_affect_modifiers()
            assert mods["avg_dominance"] == 0.5

    def test_modifiers_default_dominance_when_missing(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": 0.3,
                "avg_arousal": 0.4,
                "trend": "stable",
            }
            mods = compute_affect_modifiers()
            assert mods["avg_dominance"] == 0.0
