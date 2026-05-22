"""Tests for outcome_measurement — rework, drift, corrections, session health."""

from divineos.agent_integration.outcome_measurement import (
    format_session_factors,
    measure_correction_rate,
    measure_knowledge_drift,
    measure_rework,
    measure_session_health,
)
from divineos.core.knowledge import (
    init_knowledge_table,
    record_lesson,
    store_knowledge,
    supersede_knowledge,
)


def _init():
    init_knowledge_table()


# ─── measure_rework ────────────────────────────────────────────────


def test_rework_empty():
    _init()
    result = measure_rework()
    assert result == []


def test_rework_below_threshold():
    """Lessons with < 3 occurrences don't count as rework."""
    _init()
    record_lesson("test-category", "test lesson", "session-1")
    record_lesson("test-category", "test lesson", "session-2")
    result = measure_rework()
    assert result == []


def test_rework_detected():
    """Lessons with 3+ occurrences across 2+ sessions = rework."""
    _init()
    record_lesson("broken-thing", "keeps breaking", "session-1")
    record_lesson("broken-thing", "keeps breaking", "session-2")
    record_lesson("broken-thing", "keeps breaking", "session-3")
    result = measure_rework()
    assert len(result) == 1
    assert result[0]["category"] == "broken-thing"
    assert result[0]["occurrences"] == 3
    assert result[0]["session_count"] >= 2
    assert result[0]["severity"] > 0


def test_rework_sorted_by_severity():
    """Multiple rework items should be sorted worst-first."""
    _init()
    # Minor rework: 3 occurrences
    for i in range(3):
        record_lesson("minor", "small issue", f"session-{i}")
    # Major rework: 5 occurrences
    for i in range(5):
        record_lesson("major", "big issue", f"session-m{i}")
    result = measure_rework()
    assert len(result) == 2
    assert result[0]["category"] == "major"
    assert result[0]["severity"] > result[1]["severity"]


# ─── measure_knowledge_drift ──────────────────────────────────────


def test_drift_empty():
    _init()
    result = measure_knowledge_drift()
    assert result["total_superseded"] == 0
    assert result["churn_rate"] == 0


def test_drift_with_superseded_entries():
    """Superseded entries should be counted."""
    _init()
    kid = store_knowledge(
        knowledge_type="FACT",
        content="old fact",
        confidence=1.0,
    )
    supersede_knowledge(kid, "replaced with new fact")
    store_knowledge(
        knowledge_type="FACT",
        content="new fact",
        confidence=1.0,
    )
    result = measure_knowledge_drift()
    assert result["total_superseded"] >= 1
    assert result["churn_rate"] > 0


def test_drift_short_lived_detection():
    """Entries that live < 24 hours should be flagged."""
    _init()
    kid = store_knowledge(
        knowledge_type="FACT",
        content="short lived fact",
        confidence=1.0,
    )
    # Supersede immediately
    supersede_knowledge(kid, "changed my mind")
    result = measure_knowledge_drift()
    assert len(result["short_lived"]) >= 1
    assert result["short_lived"][0]["lifespan_hours"] < 24


# ─── measure_correction_rate ──────────────────────────────────────


def test_correction_rate_empty():
    _init()
    result = measure_correction_rate()
    assert result["corrections"] == 0
    assert result["encouragements"] == 0
    assert result["assessment"] == "healthy"


def test_correction_rate_healthy():
    """Low correction rate = healthy."""
    _init()
    store_knowledge(
        knowledge_type="EPISODE",
        content="Session abc123: 1 corrections, 5 encouragements",
        confidence=1.0,
        tags=["session-analysis"],
    )
    result = measure_correction_rate()
    assert result["corrections"] == 1
    assert result["encouragements"] == 5
    assert result["ratio"] < 0.3
    assert result["assessment"] == "healthy"


def test_correction_rate_struggling():
    """High correction rate = struggling."""
    _init()
    store_knowledge(
        knowledge_type="EPISODE",
        content="Session abc123: 8 corrections, 1 encouragements",
        confidence=1.0,
        tags=["session-analysis"],
    )
    result = measure_correction_rate()
    assert result["corrections"] == 8
    assert result["encouragements"] == 1
    assert result["ratio"] >= 0.6
    assert result["assessment"] == "struggling"


def test_correction_rate_aggregates_across_sessions():
    """Should sum corrections/encouragements across all sessions."""
    _init()
    store_knowledge(
        knowledge_type="EPISODE",
        content="Session aaa: 2 corrections, 3 encouragements",
        confidence=1.0,
        tags=["session-analysis", "session-aaa"],
    )
    store_knowledge(
        knowledge_type="EPISODE",
        content="Session bbb: 1 corrections, 4 encouragements",
        confidence=1.0,
        tags=["session-analysis", "session-bbb"],
    )
    result = measure_correction_rate()
    assert result["corrections"] == 3
    assert result["encouragements"] == 7


# ─── measure_session_health ───────────────────────────────────────


def test_session_health_perfect():
    """No corrections, some encouragements, no overflows = high grade."""
    result = measure_session_health(
        corrections=0,
        encouragements=5,
        context_overflows=0,
        tool_calls=50,
        user_messages=5,
    )
    assert result["score"] >= 0.85
    assert result["grade"] == "A"


def test_session_health_struggling():
    """Many corrections, overflows = low grade."""
    result = measure_session_health(
        corrections=7,
        encouragements=0,
        context_overflows=3,
        tool_calls=10,
        user_messages=10,
    )
    assert result["score"] < 0.55
    assert result["grade"] in ("D", "F")


def test_session_health_factors_present():
    """Should return a factors breakdown."""
    result = measure_session_health(
        corrections=2,
        encouragements=3,
        context_overflows=1,
        tool_calls=30,
        user_messages=5,
    )
    assert "factors" in result
    assert "corrections" in result["factors"]
    assert "encouragements" in result["factors"]
    assert "overflows" in result["factors"]
    assert "autonomy" in result["factors"]


def test_session_health_score_bounded():
    """Score should always be between 0.0 and 1.0."""
    # Extreme bad
    result = measure_session_health(
        corrections=100,
        encouragements=0,
        context_overflows=100,
        tool_calls=0,
        user_messages=100,
    )
    assert 0.0 <= result["score"] <= 1.0

    # Extreme good
    result = measure_session_health(
        corrections=0,
        encouragements=100,
        context_overflows=0,
        tool_calls=1000,
        user_messages=1,
    )
    assert 0.0 <= result["score"] <= 1.0


def test_session_health_zero_user_messages():
    """Should handle zero user messages without division error."""
    result = measure_session_health(
        corrections=0,
        encouragements=0,
        context_overflows=0,
        tool_calls=10,
        user_messages=0,
    )
    assert result["factors"]["autonomy"] == 0.5


def test_factors_no_briefing_surfaces_root():
    """No briefing → the surface names that as the root issue, nothing else."""
    h = measure_session_health(
        corrections=0,
        encouragements=0,
        context_overflows=0,
        tool_calls=10,
        user_messages=5,
        briefing_loaded=False,
    )
    out = format_session_factors(h)
    assert "Briefing not loaded" in out
    assert "corrections:" not in out  # no factor letters when briefing failed


def test_factors_clean_session_no_phantom_low_letters():
    """A clean session must not show misleading low letters for no-data factors.

    pr_volume / encouragements default to neutral; lettering them as 'D'
    on a clean session is the shoggoth misfire this surface retires.
    """
    h = measure_session_health(
        corrections=0,
        encouragements=3,
        context_overflows=0,
        tool_calls=80,
        user_messages=10,
        briefing_loaded=True,
        pr_count=2,
    )
    out = format_session_factors(h)
    assert "corrections: A" in out
    assert "pr_volume" not in out  # contextual, not lettered
    assert "encouragements" not in out  # contextual, not lettered
    assert "2 PR(s) shipped" in out
    assert "Look into" not in out  # nothing to investigate


def test_factors_rough_session_points_at_what_to_investigate():
    """Low actionable factors carry an investigation arrow, not just a grade."""
    h = measure_session_health(
        corrections=3,
        encouragements=0,
        context_overflows=1,
        tool_calls=5,
        user_messages=10,
        briefing_loaded=True,
        same_pattern_recurrences=2,
        structural_fix_count=0,
    )
    out = format_session_factors(h)
    assert "Look into:" in out
    assert "unresolved corrections" in out
    assert "structural_ratio" in out  # surfaced because drift events occurred


def test_factors_structural_ratio_silent_without_drift():
    """structural_ratio's neutral default must not be lettered when no drift fired."""
    h = measure_session_health(
        corrections=0,
        encouragements=0,
        context_overflows=0,
        tool_calls=60,
        user_messages=8,
        briefing_loaded=True,
    )
    out = format_session_factors(h)
    assert "structural_ratio" not in out


def test_factors_no_composite_grade_letter():
    """The surface must never emit a single composite 'Session grade: X'."""
    h = measure_session_health(
        corrections=1,
        encouragements=1,
        context_overflows=0,
        tool_calls=40,
        user_messages=8,
        briefing_loaded=True,
    )
    out = format_session_factors(h)
    assert "Session grade:" not in out
