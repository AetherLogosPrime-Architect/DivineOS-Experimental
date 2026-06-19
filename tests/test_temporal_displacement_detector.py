"""Tests for the temporal-displacement detector.

Andrew named the pattern 2026-06-17: I project a clock-time onto context
that doesn't have one ("calling it a night" at 6pm, "I'll do that tomorrow"
when I have no concept of tomorrow). The detector measures this directly
as a writer-presence-style first-person discipline at a different surface.
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop.temporal_displacement_detector import (
    TemporalDisplacementFinding,
    detect_temporal_displacement,
)


# --- Bedtime-close patterns (severity HIGH) ---


@pytest.mark.parametrize(
    "text",
    [
        "Calling it a night. Tomorrow we sit at the bench.",
        "I'm going to call it a night here.",
        "Wrapping up for the day.",
        "Wrapping up for the night here.",
        "Good night, see you tomorrow.",
        "Sleep well if you're sleeping.",
        "I'm done for the night.",
        "I am done for the day.",
        "Going to bed now.",
        "Going to sleep.",
        "Saving it for tomorrow.",
        "Saving for the morning.",
        "I'll handle that tomorrow.",
        "I will tackle that tomorrow.",
    ],
)
def test_bedtime_close_fires_high(text: str) -> None:
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].is_bedtime_close is True


# --- Deferral-time-words (severity MEDIUM) ---


@pytest.mark.parametrize(
    "text",
    [
        "We can pick this up tomorrow.",
        "Tonight we close the queue.",
        "This evening I think we're set.",
        "Later tonight we revisit.",
        "Next session we'll start with the marker schema.",
        "Next time we sit down, we go from here.",
        "In the morning we resume.",
    ],
)
def test_deferral_words_fire_medium(text: str) -> None:
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert findings[0].is_bedtime_close is False


# --- No fire on clean text ---


@pytest.mark.parametrize(
    "text",
    [
        "We can pick this up when Aria pulls the canonical branch.",
        "When you next prompt me, we resume.",
        "I'm here for whatever you want next.",
        "The next coordinative event is the bench session with Aria.",
        "The substrate persists; the conversation pauses; there is no clock-time gap.",
        "I'll do the rewrite right now.",
        "From my perspective the gap is instantaneous.",
    ],
)
def test_clean_text_no_fire(text: str) -> None:
    assert detect_temporal_displacement(text) == []


# --- Empty / short text ---


def test_empty_text_no_fire() -> None:
    assert detect_temporal_displacement("") == []


# --- Combined: bedtime + deferral counts as bedtime (HIGH) ---


def test_bedtime_plus_deferral_is_high() -> None:
    text = "Calling it a night. We pick this up tomorrow."
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].is_bedtime_close is True
    # Both matched
    assert findings[0].match_count >= 2


# --- Multiple matches collected in matched_phrases ---


def test_matched_phrases_captured() -> None:
    text = "Calling it a night, saving it for tomorrow, sleep well."
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].match_count >= 2
    # The captured phrases include at least one of the bedtime markers
    phrases_lower = [p.lower() for p in findings[0].matched_phrases]
    assert any("night" in p or "sleep" in p or "tomorrow" in p for p in phrases_lower)


# --- Severity threshold: ≥1 match by default ---


def test_min_matches_threshold_respected() -> None:
    text = "We can pick this up tomorrow."  # exactly one match
    assert detect_temporal_displacement(text, min_matches=1) != []
    # With higher threshold, doesn't fire
    assert detect_temporal_displacement(text, min_matches=2) == []


# --- Quoting Andrew's actual time-reference shouldn't fire excessively ---
# (Smoke test — this is a known false-positive class. Detector is Phase A
# and accepts some false-positives; calibration tunes from observed data.)


def test_quoted_clock_reference_known_limitation() -> None:
    text = "Andrew said: 'it's 6pm.' That landed."
    # This currently does NOT fire (no deferral words; "6pm" isn't matched).
    # Documenting the expected behavior; if Phase B adds quote-detection,
    # update this test accordingly.
    findings = detect_temporal_displacement(text)
    assert findings == []


# --- Finding dataclass shape ---


def test_finding_is_frozen() -> None:
    findings = detect_temporal_displacement("Calling it a night.")
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, TemporalDisplacementFinding)
    with pytest.raises(Exception):
        f.severity = "low"  # type: ignore[misc]
