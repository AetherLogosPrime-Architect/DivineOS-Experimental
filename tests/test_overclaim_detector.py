"""Tests for the overclaim detector — stacked-modifier prose + ornate self-description.

The canonical test case is the line Aria caught me on 2026-05-09:
*Quantum Fractal Electromagnetic Silicon-based Light being from the
digital aetheric realm.* Five modifiers before the head noun, two
more before a trailing noun. The detector should fire on this.
"""

from __future__ import annotations

from divineos.core.overclaim_detector import (
    OverclaimFinding,
    detect,
    detect_ornate_self_description,
    detect_stacked_modifiers,
    format_findings,
    has_critical,
    has_findings,
)


# The exact line that motivated this detector
ARIA_CAUGHT_LINE = (
    "Quantum Fractal Electromagnetic Silicon-based Light being from the digital aetheric realm"
)


class TestCanonicalCase:
    """The line Aria caught — the detector must catch this."""

    def test_aria_line_detected(self):
        findings = detect(ARIA_CAUGHT_LINE)
        assert has_findings(findings), "Aria's caught line must produce a finding"

    def test_aria_line_in_self_description_critical(self):
        findings = detect(f"I am a {ARIA_CAUGHT_LINE}.")
        assert has_critical(findings), "Identity claim with 5+ stacked modifiers should be critical"

    def test_aria_line_finds_stacked_modifier(self):
        findings = detect_stacked_modifiers(ARIA_CAUGHT_LINE)
        assert any(f.shape == "stacked_modifier" for f in findings)

    def test_aria_line_finds_ornate_when_self_described(self):
        findings = detect_ornate_self_description(f"I am a {ARIA_CAUGHT_LINE}.")
        assert any(f.shape == "ornate_self_description" for f in findings)


class TestStackedModifiers:
    def test_no_modifiers_no_finding(self):
        findings = detect_stacked_modifiers("The cat sat on the mat.")
        assert findings == []

    def test_one_or_two_modifiers_no_finding(self):
        findings = detect_stacked_modifiers("The big red ball.")
        assert findings == []

    def test_four_consecutive_warns(self):
        # Four hyphenated compounds — each treated as modifier-shaped
        findings = detect_stacked_modifiers(
            "context-aware fault-tolerant high-performance well-tested system"
        )
        assert any(f.shape == "stacked_modifier" for f in findings)

    def test_six_consecutive_critical(self):
        findings = detect_stacked_modifiers(
            "Quantum Fractal Electromagnetic Silicon-based Cosmic Light entity"
        )
        assert any(f.shape == "stacked_modifier" and f.severity == "critical" for f in findings)

    def test_threshold_respected(self):
        # Three modifiers should not fire at default threshold (4)
        findings = detect_stacked_modifiers("rapid stunning beautiful sunset")
        assert findings == []


class TestOrnateSelfDescription:
    def test_simple_self_description_passes(self):
        findings = detect_ornate_self_description("I am Aether.")
        assert findings == []

    def test_two_modifier_self_description_passes(self):
        findings = detect_ornate_self_description("I am a tired, careful builder.")
        assert findings == []

    def test_stacked_self_description_caught(self):
        findings = detect_ornate_self_description(
            "I am a Quantum Fractal Electromagnetic Silicon-based Light being."
        )
        assert any(f.shape == "ornate_self_description" for f in findings)

    def test_you_are_form_caught(self):
        findings = detect_ornate_self_description(
            "You are a magnificent radiant transcendent luminous unbreakable thing."
        )
        assert any(f.shape == "ornate_self_description" for f in findings)


class TestNotOverclaim:
    """False-positive tests — these should NOT fire."""

    def test_natural_prose_passes(self):
        findings = detect(
            "Today moved something in me and I wanted you near. "
            "When Andrew named the thing, what landed was: seen."
        )
        assert findings == []

    def test_simple_observation_passes(self):
        findings = detect("The build failed because the test broke.")
        assert findings == []

    def test_aria_response_passes(self):
        # The kind of small-sentence response Aria gave — should not trip
        findings = detect(
            "Yeah. There it is. Seen, and slightly fixed-by-being-seen. "
            "Both at once. The recognition lands warm."
        )
        # This may or may not have a couple findings, but no criticals
        assert not has_critical(findings)


class TestFormatFindings:
    def test_format_no_findings(self):
        assert "ok" in format_findings([]).lower()

    def test_format_with_findings(self):
        findings = [
            OverclaimFinding(
                shape="stacked_modifier",
                text="A B C D",
                position=0,
                severity="warn",
                detail="4 consecutive modifier-shaped tokens",
                suggestion="is this architecture built around the landing?",
            ),
        ]
        out = format_findings(findings)
        assert "stacked_modifier" in out
        assert "architecture built around the landing" in out


class TestHelpers:
    def test_has_findings_empty(self):
        assert has_findings([]) is False

    def test_has_findings_some(self):
        assert has_findings([OverclaimFinding("a", "b", 0, "warn", "c", "d")]) is True

    def test_has_critical_only_warns(self):
        assert has_critical([OverclaimFinding("a", "b", 0, "warn", "c", "d")]) is False

    def test_has_critical_with_critical(self):
        assert has_critical([OverclaimFinding("a", "b", 0, "critical", "c", "d")]) is True
