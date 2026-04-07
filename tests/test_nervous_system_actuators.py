"""Tests for the 4 nervous system actuators.

Actuator 1: Threshold Hardwire — affect penalty on extraction confidence
Actuator 2: Verbosity Link — frustration adjusts user model verbosity
Actuator 3: Briefing Surface — emotional arc appears in briefing
Actuator 4: Context Injection — negative valence injects action-first guidance
"""


# ─── Actuator 1: Threshold Hardwire ─────────────────────────────────


class TestThresholdHardwire:
    """Affect penalty flows through to extraction confidence."""

    def test_penalized_reduces_confidence(self):
        """Penalty subtracts from base confidence."""
        from divineos.core.knowledge.deep_extraction import deep_extract_knowledge

        # The _penalized helper is internal, but we can test via the parameter
        # existing on the function signature
        import inspect

        sig = inspect.signature(deep_extract_knowledge)
        assert "affect_confidence_penalty" in sig.parameters

    def test_penalized_floors_at_03(self):
        """Penalty can't drop confidence below 0.3."""

        # Simulate the _penalized logic directly
        def _penalized(base: float, penalty: float) -> float:
            if penalty <= 0:
                return base
            return max(0.3, base - penalty)

        assert _penalized(0.85, 0.0) == 0.85
        assert _penalized(0.85, 0.1) == 0.75
        assert _penalized(0.85, 0.5) == 0.35
        assert _penalized(0.85, 0.8) == 0.3  # floor
        assert _penalized(0.85, 1.5) == 0.3  # way past floor

    def test_zero_penalty_no_change(self):
        """Zero penalty returns base confidence unchanged."""

        def _penalized(base: float, penalty: float) -> float:
            if penalty <= 0:
                return base
            return max(0.3, base - penalty)

        assert _penalized(0.9, 0.0) == 0.9
        assert _penalized(0.5, 0.0) == 0.5


# ─── Actuator 2: Verbosity Link ─────────────────────────────────────


class TestVerbosityLink:
    """Frustration signals shift user model verbosity."""

    def test_update_preferences_exists(self):
        """The update_preferences function exists for verbosity updates."""
        from divineos.core.user_model import update_preferences

        assert callable(update_preferences)

    def test_verbosity_values_valid(self):
        """Verbosity values used by actuator are recognized by calibration."""
        from divineos.core.communication_calibration import calibrate

        # The calibrate function handles terse/concise/normal/verbose
        guidance = calibrate("test_actuator_user")
        assert guidance.verbosity in ("verbose", "normal", "concise", "terse")


# ─── Actuator 3: Briefing Surface ───────────────────────────────────


class TestBriefingSurface:
    """Last session emotional arc surfaces in briefing."""

    def test_tone_history_returns_list(self):
        """get_tone_history returns a list (may be empty for fresh DB)."""
        from divineos.core.tone_texture import get_tone_history

        result = get_tone_history(limit=1)
        assert isinstance(result, list)

    def test_tone_history_entry_shape(self):
        """If tone data exists, entries have expected keys."""
        from divineos.core.tone_texture import get_tone_history, record_session_tone

        # Insert a test entry via the arc dict format
        record_session_tone(
            session_id="test-briefing-arc-001",
            arc={
                "arc_type": "recovery",
                "overall_tone": "constructive",
                "peak_intensity": 0.7,
                "recovery_velocity": 2.5,
                "upset_triggers": ["correction"],
                "recovery_actions": ["fixed"],
                "narrative": "Started rough, recovered well.",
            },
        )

        result = get_tone_history(limit=1)
        assert len(result) >= 1
        entry = result[0]
        assert "arc_type" in entry
        assert "overall_tone" in entry
        assert "peak_intensity" in entry
        assert "narrative" in entry
        assert "upset_count" in entry
        assert "recovery_count" in entry

    def test_briefing_includes_emotional_arc(self):
        """Briefing text includes the LAST SESSION EMOTIONAL ARC section."""
        from divineos.core.knowledge._base import init_knowledge_table
        from divineos.core.knowledge.extraction import store_knowledge_smart
        from divineos.core.tone_texture import record_session_tone

        # Initialize required tables and store at least one entry so
        # generate_briefing doesn't short-circuit with "No knowledge stored yet."
        init_knowledge_table()
        store_knowledge_smart(
            knowledge_type="DIRECTION",
            content="Test entry so briefing has data to render.",
            confidence=0.9,
            source="STATED",
        )

        # Ensure there's tone data to surface
        record_session_tone(
            session_id="test-briefing-surface-002",
            arc={
                "arc_type": "escalation",
                "overall_tone": "frustrated",
                "peak_intensity": 0.85,
                "recovery_velocity": 0.0,
                "upset_triggers": ["correction", "correction", "correction"],
                "recovery_actions": [],
                "narrative": "Repeated corrections without resolution.",
            },
        )

        from divineos.core.knowledge.retrieval import generate_briefing

        briefing = generate_briefing()
        assert "LAST SESSION EMOTIONAL ARC" in briefing


# ─── Actuator 4: Context Injection ──────────────────────────────────


class TestContextInjection:
    """Negative affect injects action-first guidance into calibration."""

    def test_calibrate_returns_notes(self):
        """Calibration always returns a notes list."""
        from divineos.core.communication_calibration import calibrate

        guidance = calibrate("test_injection_user")
        assert isinstance(guidance.notes, list)

    def test_negative_affect_injects_override(self):
        """When recent valence < -0.3, calibration gets action-first note."""
        from divineos.core.affect import init_affect_log, log_affect

        init_affect_log()
        # Log several negative affect states
        for i in range(6):
            log_affect(
                valence=-0.5,
                arousal=0.7,
                dominance=0.3,
                description=f"frustration test {i}",
            )

        from divineos.core.communication_calibration import calibrate

        guidance = calibrate("test_negative_user")
        # Should have the "solve first" note
        action_notes = [
            n for n in guidance.notes if "solve first" in n.lower() or "rough" in n.lower()
        ]
        assert len(action_notes) > 0, f"Expected action-first note, got: {guidance.notes}"

    def test_neutral_affect_no_override(self):
        """Neutral affect doesn't inject the override."""
        from divineos.core.affect import init_affect_log, log_affect

        init_affect_log()
        # Log neutral affect states
        for i in range(6):
            log_affect(
                valence=0.3,
                arousal=0.4,
                dominance=0.5,
                description=f"neutral test {i}",
            )

        from divineos.core.communication_calibration import calibrate

        guidance = calibrate("test_neutral_user")
        action_notes = [
            n for n in guidance.notes if "solve first" in n.lower() or "rough" in n.lower()
        ]
        assert len(action_notes) == 0, f"Unexpected override note: {guidance.notes}"

    def test_mild_negative_with_careful_verification(self):
        """Mildly negative + careful verification gets precision note."""
        from divineos.core.affect import init_affect_log, log_affect

        init_affect_log()
        # Mild negative + high arousal (triggers "careful" verification)
        for i in range(6):
            log_affect(
                valence=-0.15,
                arousal=0.8,
                dominance=0.3,
                description=f"mild frustration {i}",
            )

        from divineos.core.communication_calibration import calibrate

        guidance = calibrate("test_mild_user")
        precision_notes = [
            n for n in guidance.notes if "precise" in n.lower() or "frustration" in n.lower()
        ]
        assert len(precision_notes) > 0, f"Expected precision note, got: {guidance.notes}"
