"""Tests for user model — structured user preference and skill tracking."""

import pytest

from divineos.core.user_model import (
    format_user_model,
    get_or_create_user,
    get_user_signals,
    init_user_model_table,
    record_signal,
    update_preferences,
    update_skill_level,
)


@pytest.fixture(autouse=True)
def _setup():
    init_user_model_table()


class TestGetOrCreateUser:
    """User creation and retrieval."""

    def test_creates_default_user(self):
        user = get_or_create_user()
        assert user["name"] == "default"
        assert user["skill_level"] == "intermediate"
        assert user["skill_confidence"] == 0.3

    def test_creates_named_user(self):
        user = get_or_create_user("andrew")
        assert user["name"] == "andrew"

    def test_get_existing_user(self):
        user1 = get_or_create_user("test_user")
        user2 = get_or_create_user("test_user")
        assert user1["user_id"] == user2["user_id"]

    def test_default_preferences(self):
        user = get_or_create_user()
        prefs = user["preferences"]
        assert prefs["verbosity"] == "normal"
        assert prefs["jargon_tolerance"] == 0.5
        assert prefs["prefers_examples"] is True


class TestRecordSignal:
    """Signal recording."""

    def test_record_returns_id(self):
        sid = record_signal("skill_high", "Used complex regex fluently")
        assert sid.startswith("sig-")

    def test_signal_retrievable(self):
        record_signal("skill_high", "Wrote generator expression")
        signals = get_user_signals()
        assert len(signals) >= 1
        assert signals[0]["signal_type"] == "skill_high"

    def test_increments_interaction_count(self):
        get_or_create_user("counter_test")
        record_signal("skill_high", "Signal 1", user_name="counter_test")
        record_signal("skill_high", "Signal 2", user_name="counter_test")
        user = get_or_create_user("counter_test")
        assert user["interaction_count"] == 2

    def test_filter_by_type(self):
        record_signal("skill_high", "Advanced", user_name="filter_test")
        record_signal("skill_low", "Basic question", user_name="filter_test")
        high = get_user_signals(user_name="filter_test", signal_type="skill_high")
        assert all(s["signal_type"] == "skill_high" for s in high)

    def test_session_id_stored(self):
        record_signal("correction_given", "Fixed my mistake", session_id="sess-123")
        signals = get_user_signals()
        assert signals[0]["session_id"] == "sess-123"


class TestSkillLevelComputation:
    """Skill level inferred from signals."""

    def test_no_signals_keeps_default(self):
        get_or_create_user("no_signals")
        user = update_skill_level("no_signals")
        assert user["skill_level"] == "intermediate"

    def test_high_signals_increase_level(self):
        name = "skilled_user"
        get_or_create_user(name)
        for i in range(5):
            record_signal("skill_high", f"Advanced usage {i}", user_name=name)
        user = update_skill_level(name)
        assert user["skill_level"] in ("advanced", "expert")

    def test_low_signals_decrease_level(self):
        name = "new_user"
        get_or_create_user(name)
        for i in range(5):
            record_signal("skill_low", f"Basic question {i}", user_name=name)
        user = update_skill_level(name)
        assert user["skill_level"] == "beginner"

    def test_mixed_signals_intermediate(self):
        name = "mixed_user"
        get_or_create_user(name)
        record_signal("skill_high", "Complex code", user_name=name)
        record_signal("skill_low", "Basic question", user_name=name)
        user = update_skill_level(name)
        assert user["skill_level"] == "intermediate"

    def test_confidence_grows_with_signals(self):
        name = "conf_user"
        get_or_create_user(name)
        for i in range(10):
            record_signal("skill_high", f"Evidence {i}", user_name=name)
        user = update_skill_level(name)
        assert user["skill_confidence"] > 0.5

    def test_jargon_signals_affect_level(self):
        name = "jargon_user"
        get_or_create_user(name)
        for i in range(5):
            record_signal("jargon_used", f"Used term {i}", user_name=name)
        user = update_skill_level(name)
        assert user["skill_level"] in ("advanced", "expert")


class TestPreferences:
    """Preference updates."""

    def test_update_verbosity(self):
        name = "pref_user"
        get_or_create_user(name)
        user = update_preferences(name, verbosity="concise")
        assert user["preferences"]["verbosity"] == "concise"

    def test_update_multiple_prefs(self):
        name = "multi_pref"
        get_or_create_user(name)
        user = update_preferences(name, jargon_tolerance=0.9, explanation_depth="deep")
        assert user["preferences"]["jargon_tolerance"] == 0.9
        assert user["preferences"]["explanation_depth"] == "deep"

    def test_partial_update_preserves_others(self):
        name = "partial_pref"
        get_or_create_user(name)
        update_preferences(name, verbosity="terse")
        user = get_or_create_user(name)
        # Other prefs should still be at defaults
        assert user["preferences"]["prefers_examples"] is True


class TestFormat:
    """Formatting."""

    def test_format_includes_skill(self):
        get_or_create_user("fmt_user")
        result = format_user_model("fmt_user")
        assert "intermediate" in result
        assert "fmt_user" in result

    def test_format_includes_preferences(self):
        get_or_create_user("fmt_pref")
        result = format_user_model("fmt_pref")
        assert "Verbosity" in result
        assert "normal" in result
