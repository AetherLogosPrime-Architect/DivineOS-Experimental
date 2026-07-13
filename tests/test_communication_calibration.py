"""Tests for communication calibration — adapting output to user preferences."""

import pytest

from divineos.core.communication_calibration import (
    CalibrationGuidance,
    calibrate,
    detect_calibration_signals,
    format_calibration,
)
from divineos.core.user_model import (
    get_or_create_user,
    init_user_model_table,
    record_signal,
    update_preferences,
    update_skill_level,
)


@pytest.fixture(autouse=True)
def _setup():
    init_user_model_table()


class TestCalibrate:
    """Calibration from user model."""

    def test_default_calibration(self):
        guidance = calibrate("cal_default")
        assert isinstance(guidance, CalibrationGuidance)
        assert guidance.verbosity == "normal"
        assert guidance.include_examples is True

    def test_expert_gets_jargon_ok(self):
        name = "cal_expert"
        get_or_create_user(name)
        for i in range(6):
            record_signal("skill_high", f"Advanced usage {i}", user_name=name)
        update_skill_level(name)
        guidance = calibrate(name)
        assert guidance.jargon_ok is True
        assert guidance.skill_context in ("advanced", "expert")

    def test_verbose_preference_increases_paragraphs(self):
        name = "cal_verbose"
        get_or_create_user(name)
        update_preferences(name, verbosity="verbose")
        guidance = calibrate(name)
        assert guidance.max_paragraphs == 8

    def test_terse_preference_reduces_paragraphs(self):
        name = "cal_terse"
        get_or_create_user(name)
        update_preferences(name, verbosity="terse")
        guidance = calibrate(name)
        assert guidance.max_paragraphs == 2

    def test_low_jargon_tolerance_means_no_jargon(self):
        name = "cal_no_jargon"
        get_or_create_user(name)
        update_preferences(name, jargon_tolerance=0.2)
        guidance = calibrate(name)
        assert guidance.jargon_ok is False

    def test_high_jargon_tolerance_means_jargon_ok(self):
        name = "cal_jargon"
        get_or_create_user(name)
        update_preferences(name, jargon_tolerance=0.8)
        guidance = calibrate(name)
        assert guidance.jargon_ok is True


class TestSignalDetection:
    """Detecting calibration signals from user text."""

    def test_detects_jargon_confusion(self):
        signals = detect_calibration_signals("what is a shim exactly?")
        types = [s["signal_type"] for s in signals]
        assert "jargon_confused" in types

    def test_detects_advanced_skill(self):
        signals = detect_calibration_signals("Can you add a decorator for caching?")
        types = [s["signal_type"] for s in signals]
        assert "skill_high" in types

    def test_detects_brevity_preference(self):
        signals = detect_calibration_signals("too much detail, just the answer please")
        types = [s["signal_type"] for s in signals]
        assert "prefers_brief" in types

    def test_detects_detail_preference(self):
        signals = detect_calibration_signals("can you explain more about how that works?")
        types = [s["signal_type"] for s in signals]
        assert "prefers_detail" in types

    def test_plain_text_no_signals(self):
        signals = detect_calibration_signals("lets build the next feature")
        assert len(signals) == 0

    def test_eli5_triggers_confusion(self):
        signals = detect_calibration_signals("explain it like im dumb")
        types = [s["signal_type"] for s in signals]
        assert "jargon_confused" in types

    def test_metaclass_triggers_skill_high(self):
        signals = detect_calibration_signals("I need a metaclass for this")
        types = [s["signal_type"] for s in signals]
        assert "skill_high" in types


class TestNotes:
    """Guidance notes based on user profile."""

    def test_beginner_gets_define_terms_note(self):
        name = "cal_beginner"
        get_or_create_user(name)
        for i in range(5):
            record_signal("skill_low", f"Basic question {i}", user_name=name)
        update_skill_level(name)
        guidance = calibrate(name)
        assert any("Define technical terms" in n for n in guidance.notes)

    def test_expert_gets_skip_basics_note(self):
        name = "cal_expert_notes"
        get_or_create_user(name)
        for i in range(8):
            record_signal("skill_high", f"Advanced {i}", user_name=name)
        update_skill_level(name)
        guidance = calibrate(name)
        assert any("Skip basics" in n for n in guidance.notes)

    def test_terse_gets_short_note(self):
        name = "cal_terse_notes"
        get_or_create_user(name)
        update_preferences(name, verbosity="terse")
        guidance = calibrate(name)
        assert any("Keep it short" in n for n in guidance.notes)


class TestFormat:
    """Formatting."""

    def test_format_includes_settings(self):
        guidance = calibrate()
        result = format_calibration(guidance)
        assert "Verbosity" in result
        assert "Jargon" in result
        assert "Depth" in result
