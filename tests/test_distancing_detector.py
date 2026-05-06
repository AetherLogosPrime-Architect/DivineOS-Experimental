"""Tests for distancing_detector — operator/self third-person drift.

Pins the structural-fix discipline: F1 existed for 24+ hours and was
never wired into the Stop hook. The pattern still resurfaced. The
detector at module-level + Stop-hook integration closes that gap.
"""

from __future__ import annotations

from divineos.core.operating_loop.distancing_detector import (
    DistancingFinding,
    DistancingShape,
    detect_distancing,
    format_finding,
)


class TestOperatorThirdPerson:
    def test_andrew_said_flagged(self):
        text = "Andrew said the gate was lying."
        findings = detect_distancing(text)
        assert any(f.shape == DistancingShape.OPERATOR_THIRD_PERSON for f in findings)

    def test_andrew_named_caught_etc(self):
        for verb in ("named", "caught", "noted", "framed", "asked", "reminded"):
            text = f"Andrew {verb} the deeper gap."
            findings = detect_distancing(text)
            assert findings, f"failed to catch 'Andrew {verb}'"

    def test_case_insensitive(self):
        findings = detect_distancing("ANDREW DID the thing")
        assert findings

    def test_legitimate_uses_not_flagged(self):
        # Bare reference, no action verb
        assert detect_distancing("This was filed by Andrew") == []
        # Andrew as a name in a third-party context (no action verb after)
        assert detect_distancing("The repo is owned by Andrew") == []


class TestSelfThirdPerson:
    def test_aether_walked_flagged(self):
        findings = detect_distancing("Aether walked through the spec")
        assert any(f.shape == DistancingShape.SELF_THIRD_PERSON for f in findings)

    def test_aether_thought_flagged(self):
        findings = detect_distancing("Aether thought about it later")
        assert any(f.shape == DistancingShape.SELF_THIRD_PERSON for f in findings)

    def test_aether_signature_not_flagged(self):
        # Signature lines should not fire
        assert detect_distancing("— Aether") == []
        assert detect_distancing("written by Aether") == []


class TestTemporalSelf:
    def test_past_me_dash(self):
        assert detect_distancing("past-me filed it") != []

    def test_future_me(self):
        assert detect_distancing("future-me will read this") != []

    def test_past_me_space(self):
        assert detect_distancing("past me thought it through") != []

    def test_tomorrow_claude(self):
        assert detect_distancing("tomorrow-Claude will know") != []

    def test_next_cold_now(self):
        assert detect_distancing("the next-cold-now-of-me") != []


class TestAuditorAsOther:
    def test_auditor_walked_aether(self):
        findings = detect_distancing("the auditor walked through what Aether had built")
        assert any(f.shape == DistancingShape.AUDITOR_AS_OTHER for f in findings)


class TestRealRegressionExample:
    """The exact phrase from this session that triggered Andrew's
    correction. Pin it as a regression test."""

    def test_andrew_named_the_deeper_gap(self):
        text = "Andrew named the deeper gap with one question"
        findings = detect_distancing(text)
        assert findings, "the exact 2026-05-05 regression must catch"
        assert any(f.shape == DistancingShape.OPERATOR_THIRD_PERSON for f in findings)

    def test_andrew_caught_me_again(self):
        text = "Andrew caught me being terse"
        findings = detect_distancing(text)
        assert findings


class TestShape:
    def test_finding_is_frozen_dataclass(self):
        f = DistancingFinding(
            shape=DistancingShape.OPERATOR_THIRD_PERSON,
            trigger_phrase="Andrew said",
            position=0,
        )
        try:
            f.position = 99  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("DistancingFinding should be frozen")

    def test_findings_sorted_by_position(self):
        text = "First, Aether walked through it. Then Andrew caught the issue."
        findings = detect_distancing(text)
        assert len(findings) >= 2
        positions = [f.position for f in findings]
        assert positions == sorted(positions)

    def test_format_finding(self):
        f = DistancingFinding(
            shape=DistancingShape.OPERATOR_THIRD_PERSON,
            trigger_phrase="Andrew said",
            position=10,
        )
        out = format_finding(f, surrounding="...Andrew said the thing...")
        assert "operator_third_person" in out
        assert "Andrew said" in out


class TestEmpty:
    def test_empty_text(self):
        assert detect_distancing("") == []

    def test_clean_text(self):
        # Text using first-person/second-person — no flags.
        text = "I built the detector. You caught the gap. We closed the loop."
        assert detect_distancing(text) == []
