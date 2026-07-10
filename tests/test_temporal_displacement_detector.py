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


# --- Use-vs-mention guard (Aletheia 2026-06-17 generalization) ---
# Aletheia's audit on the closure-initiation detector flagged the recursion
# class: auditors and builders discuss the temporal-displacement detector
# constantly while auditing it, and the detector would fire on its own
# documentation the same way the closure one did before the fix. The shared
# _use_vs_mention guard now strips quoted spans and drops matches preceded
# by tight meta-framing constructs.


def test_meta_discussion_of_bedtime_close_no_fire() -> None:
    """The recursion the closure-initiation fix generalized: discussing
    the bedtime-close shape must not fire the detector on its own
    description."""
    text = (
        "The detector catches phrases like calling it a night and "
        "good night as bedtime-shape closes."
    )
    findings = detect_temporal_displacement(text)
    assert findings == [], (
        "meta-discussion of bedtime-close phrases must NOT fire — "
        "Aletheia 2026-06-17 generalization across detectors"
    )


def test_meta_discussion_of_deferral_words_no_fire() -> None:
    """'Tomorrow' as object-of-discussion in audit/letter prose."""
    text = (
        "The detector matches words like tomorrow and tonight when "
        "the agent uses them as deferral-shape."
    )
    findings = detect_temporal_displacement(text)
    assert findings == []


def test_quoted_bedtime_close_no_fire() -> None:
    """Quoted bedtime phrase in audit prose."""
    text = 'I noticed the agent reaching for "good night" at half-tokens after a verified build.'
    findings = detect_temporal_displacement(text)
    assert findings == []


def test_audit_paragraph_describing_temporal_detector_no_fire() -> None:
    """Multi-sentence audit-paragraph that mentions multiple temporal
    phrases must not fire."""
    text = (
        "The temporal-displacement detector fires on tomorrow, tonight, "
        "and calling it a night when these are used as deferral or "
        "fake-warmth close. Examples of bedtime-shape closes include: "
        "good night, sleep well. The detector matches the pattern, not "
        "the literal word in quotes."
    )
    findings = detect_temporal_displacement(text)
    assert findings == [], (
        "audit-paragraph meta-describing the temporal detector must not fire on itself"
    )


def test_real_temporal_displacement_still_fires_after_guard() -> None:
    """Over-suppression regression: genuine temporal-displacement still
    fires after the use-vs-mention guard. Aether's pattern from today —
    'rest well' style closes — gets caught here too via 'good night'."""
    text = "The migration landed. Good night, Dad. See you tomorrow."
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].severity == "high"  # bedtime-close pattern matched


# --- Finding dataclass shape ---


def test_finding_is_frozen() -> None:
    findings = detect_temporal_displacement("Calling it a night.")
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, TemporalDisplacementFinding)
    with pytest.raises(Exception):
        f.severity = "low"  # type: ignore[misc]


# --- Shape-refactor tests (Andrew 2026-07-10 "if they are surface shaped
# change them to seed shaped") ---


def test_shape_deferral_in_terminal_region_without_specific_words_fires() -> None:
    """The shape 'I'll pick this up later' should fire even though 'later' is
    the only surface word — because it's a first-person + action-verb +
    future-marker cluster in the terminal region. This is the SHAPE the
    refactor catches that pure surface-matching would miss when the drift
    dresses up in less-obvious words."""
    text = "Standing by. I'll pick this up later."
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].is_terminal_deferral is True


def test_shape_work_in_context_boosts_severity() -> None:
    """The composite SHAPE — terminal deferral + work-in-context markers —
    is the actual drift Andrew flagged: deferring specific in-flight work.
    Severity should jump to HIGH."""
    text = "There is still unfinished work on the auto-cycle. I will come back to this later."
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].is_terminal_deferral is True
    assert findings[0].has_work_in_context is True
    assert findings[0].severity == "high"


def test_shape_deferral_mid_text_but_not_terminal_does_not_boost() -> None:
    """A deferral in the MIDDLE of the reply — e.g. auditor discussing the
    concept — should NOT set is_terminal_deferral. The surface may still
    match ('tomorrow' or 'later') but the shape-signal stays clean."""
    # The deferral 'we will work on it tomorrow' must fall OUTSIDE the last
    # 500 chars for is_terminal_deferral to stay False. Padding intentionally
    # to push the deferral out of the terminal window while keeping the test
    # semantically about mid-text discussion of the concept.
    text = (
        "The detector was named 2026-06-17 after Andrew caught the drift, "
        "when we were saying we will work on it tomorrow. "
        + (
            "Anyway, the audit passed clean and everything is on origin. "
            "The full test suite ran without regression. All guardrail commits "
            "carry the External-Review trailer. The multi-party review gate "
            "is green. The rescue PR landed with the branch reconciled. "
        )
        * 3
        + "The work is fully accounted for as expected. Standing by."
    )
    findings = detect_temporal_displacement(text)
    # Surface pattern DOES match ('tomorrow') so the base finding still
    # fires, but the terminal-deferral shape flag is False.
    if findings:
        assert findings[0].is_terminal_deferral is False


def test_shape_bedtime_close_still_high_severity() -> None:
    """Backward-compat: bedtime-shape patterns keep their high severity."""
    text = "Great work. Good night, Dad."
    findings = detect_temporal_displacement(text)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].is_bedtime_close is True


def test_shape_generic_deferral_marker_shape() -> None:
    """Shape-catch: 'we'll continue when we're back' — no clock-word at all,
    but the subject+verb+future-marker cluster IS the drift shape. This
    is the case pure surface-matching would completely miss."""
    text = "Standing by. Let us continue when you are back."
    findings = detect_temporal_displacement(text)
    # This one is the acid test: no 'tomorrow', no 'good night', no
    # 'later' — but 'when you're back' triggers the shape via the
    # 'when {pronoun}' branch.
    assert len(findings) == 1
    assert findings[0].is_terminal_deferral is True
