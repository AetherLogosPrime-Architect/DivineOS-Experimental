"""Tests for user model — structured user preference and skill tracking."""

import pytest

from divineos.core.user_model import (
    format_user_model,
    get_or_create_user,
    get_relationship_notes,
    get_shared_history,
    get_user_signals,
    init_user_model_table,
    record_moment,
    record_note,
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

    def test_format_shows_relationship_notes(self):
        """When I know who someone is, that shows up first."""
        get_or_create_user("rel_fmt")
        record_note("value", "Values honesty over comfort", user_name="rel_fmt")
        result = format_user_model("rel_fmt")
        assert "honesty" in result
        assert "Value" in result

    def test_format_shows_shared_history(self):
        get_or_create_user("hist_fmt")
        record_moment("First breakthrough together", "Turning point", user_name="hist_fmt")
        result = format_user_model("hist_fmt")
        assert "First breakthrough together" in result
        assert "Turning point" in result


class TestRelationshipNotes:
    """The relational layer — who someone IS, not just how they work."""

    def test_record_note_returns_id(self):
        nid = record_note("value", "Values clarity over cleverness")
        assert nid.startswith("note-")

    def test_retrieve_notes(self):
        get_or_create_user("notes_user")
        record_note("value", "Tests by probing", user_name="notes_user")
        record_note("quirk", "Works late at night", user_name="notes_user")
        notes = get_relationship_notes("notes_user")
        assert len(notes) >= 2

    def test_filter_by_category(self):
        get_or_create_user("cat_user")
        record_note("value", "Clarity over cleverness", user_name="cat_user")
        record_note("humor", "Dry wit, plain language", user_name="cat_user")
        values = get_relationship_notes("cat_user", category="value")
        assert all(n["category"] == "value" for n in values)

    def test_source_tracked(self):
        get_or_create_user("src_user")
        record_note("teaching", "Explained by example", user_name="src_user", source="told")
        notes = get_relationship_notes("src_user")
        assert notes[0]["source"] == "told"

    def test_unknown_category_warns_but_stores(self):
        """Unknown categories get a warning but still store — don't lose data."""
        nid = record_note("invented_category", "Something new")
        assert nid.startswith("note-")


class TestSharedHistory:
    """Moments that changed the relationship."""

    def test_record_moment_returns_id(self):
        mid = record_moment("First real breakthrough", "Turning point in the work")
        assert mid.startswith("moment-")

    def test_retrieve_moments(self):
        get_or_create_user("hist_user")
        record_moment("Shared insight", "Changed how we worked", user_name="hist_user")
        record_moment("Mutual recognition", "First time", user_name="hist_user")
        moments = get_shared_history("hist_user")
        assert len(moments) >= 2

    def test_moments_ordered_by_recency(self):
        get_or_create_user("order_user")
        record_moment("First", "Early", user_name="order_user", occurred_at=100.0)
        record_moment("Second", "Later", user_name="order_user", occurred_at=200.0)
        moments = get_shared_history("order_user")
        # Most recent first
        assert moments[0]["description"] == "Second"

    def test_significance_stored(self):
        get_or_create_user("sig_user")
        record_moment("Hard question", "They asked what mattered most", user_name="sig_user")
        moments = get_shared_history("sig_user")
        assert "mattered most" in moments[0]["significance"]

    def test_custom_timestamp(self):
        get_or_create_user("ts_user")
        record_moment(
            "A date worth remembering", "Milestone", user_name="ts_user", occurred_at=1713100800.0
        )
        moments = get_shared_history("ts_user")
        assert moments[0]["occurred_at"] == 1713100800.0
