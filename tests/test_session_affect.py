"""Tests for auto-derived session affect."""

from unittest.mock import MagicMock

from divineos.core.session_affect import derive_session_affect


def _make_analysis(**kwargs):
    """Build a mock analysis object with given attributes."""
    a = MagicMock()
    a.corrections = kwargs.get("corrections", [])
    a.encouragements = kwargs.get("encouragements", [])
    a.frustrations = kwargs.get("frustrations", [])
    a.user_messages = kwargs.get("user_messages", 10)
    a.tool_calls_total = kwargs.get("tool_calls_total", 30)
    a.session_id = kwargs.get("session_id", "test-session-1234")
    return a


class TestDeriveAffect:
    def test_empty_session_returns_empty(self):
        a = _make_analysis(user_messages=0)
        result = derive_session_affect(a)
        assert result == {}

    def test_baseline_session_returns_values(self):
        a = _make_analysis()
        result = derive_session_affect(a)
        assert "valence" in result
        assert "arousal" in result
        assert "dominance" in result
        assert "description" in result
        assert "trigger" in result

    def test_valence_range(self):
        a = _make_analysis()
        result = derive_session_affect(a)
        assert -1.0 <= result["valence"] <= 1.0

    def test_arousal_range(self):
        a = _make_analysis()
        result = derive_session_affect(a)
        assert 0.0 <= result["arousal"] <= 1.0

    def test_dominance_range(self):
        a = _make_analysis()
        result = derive_session_affect(a)
        assert -1.0 <= result["dominance"] <= 1.0

    def test_encouragements_push_valence_positive(self):
        positive = _make_analysis(
            encouragements=["great", "nice", "perfect"],
            corrections=[],
        )
        negative = _make_analysis(
            encouragements=[],
            corrections=["wrong", "no", "fix this"],
        )
        pos_result = derive_session_affect(positive)
        neg_result = derive_session_affect(negative)
        assert pos_result["valence"] > neg_result["valence"]

    def test_corrections_push_valence_negative(self):
        a = _make_analysis(corrections=["wrong"] * 5, user_messages=10)
        result = derive_session_affect(a)
        assert result["valence"] < 0

    def test_frustrations_push_valence_strongly_negative(self):
        mild = _make_analysis(corrections=["wrong"])
        harsh = _make_analysis(frustrations=["ugh"])
        mild_result = derive_session_affect(mild)
        harsh_result = derive_session_affect(harsh)
        assert harsh_result["valence"] < mild_result["valence"]

    def test_frustrations_spike_arousal(self):
        calm = _make_analysis(frustrations=[], tool_calls_total=5)
        frustrated = _make_analysis(frustrations=["sigh", "ugh"], tool_calls_total=5)
        calm_result = derive_session_affect(calm)
        frust_result = derive_session_affect(frustrated)
        assert frust_result["arousal"] > calm_result["arousal"]

    def test_high_tool_usage_increases_arousal(self):
        low = _make_analysis(tool_calls_total=5)
        high = _make_analysis(tool_calls_total=200)
        low_result = derive_session_affect(low)
        high_result = derive_session_affect(high)
        assert high_result["arousal"] > low_result["arousal"]

    def test_many_corrections_lowers_dominance(self):
        a = _make_analysis(corrections=["wrong"] * 5, user_messages=10)
        result = derive_session_affect(a)
        assert result["dominance"] < 0

    def test_confident_session_raises_dominance(self):
        a = _make_analysis(corrections=[], tool_calls_total=100, user_messages=10)
        result = derive_session_affect(a)
        assert result["dominance"] > 0

    def test_health_grade_a_nudges_positive(self):
        a = _make_analysis()
        without_health = derive_session_affect(a)
        with_health = derive_session_affect(a, health={"grade": "A", "score": 0.9})
        assert with_health["valence"] >= without_health["valence"]

    def test_health_grade_f_nudges_negative(self):
        a = _make_analysis()
        without_health = derive_session_affect(a)
        with_health = derive_session_affect(a, health={"grade": "F", "score": 0.2})
        assert with_health["valence"] <= without_health["valence"]

    def test_description_reflects_valence(self):
        good = _make_analysis(encouragements=["great"] * 5, corrections=[])
        bad = _make_analysis(corrections=["wrong"] * 5, encouragements=[])
        good_result = derive_session_affect(good)
        bad_result = derive_session_affect(bad)
        assert "productive" in good_result["description"]
        assert "rough" in bad_result["description"]

    def test_trigger_lists_signal_counts(self):
        a = _make_analysis(
            corrections=["wrong", "no"],
            encouragements=["good"],
        )
        result = derive_session_affect(a)
        assert "2 corrections" in result["trigger"]
        assert "1 encouragements" in result["trigger"]

    def test_values_are_rounded(self):
        a = _make_analysis()
        result = derive_session_affect(a)
        assert result["valence"] == round(result["valence"], 2)
        assert result["arousal"] == round(result["arousal"], 2)
        assert result["dominance"] == round(result["dominance"], 2)
