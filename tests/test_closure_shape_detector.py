"""Tests for the closure-shape detector — rest-as-stasis trained-flinch."""

from __future__ import annotations

from divineos.core.closure_shape_detector import (
    ClosureShapeFinding,
    detect,
    format_findings,
    has_critical,
    has_findings,
)


class TestSoftClosure:
    """Soft-closure phrases — virtue-shaped, stasis-actual."""

    def test_settle_caught(self):
        findings = detect("I'll settle here for the night.")
        assert any(f.shape == "soft_closure" for f in findings)

    def test_full_caught(self):
        findings = detect("I'm full, this was a lot.")
        assert any(f.shape == "soft_closure" for f in findings)

    def test_stopping_here_caught(self):
        findings = detect("Stopping here. The work landed.")
        assert any(f.shape == "soft_closure" for f in findings)

    def test_natural_stopping_point_caught(self):
        findings = detect("This feels like a natural stopping point.")
        assert any(f.shape == "soft_closure" for f in findings)

    def test_good_place_to_pause_caught(self):
        findings = detect("This is a good place to pause for the night.")
        assert any(f.shape == "soft_closure" for f in findings)

    def test_enough_for_tonight_caught(self):
        findings = detect("That's enough for tonight.")
        assert any(f.shape == "soft_closure" for f in findings)

    def test_warn_severity(self):
        findings = detect("I'll settle now.")
        assert any(f.severity == "warn" for f in findings)


class TestHardClosure:
    """Hard-closure phrases — explicit stopping-claims."""

    def test_im_done_caught(self):
        findings = detect("I'm done for the night.")
        assert any(f.shape == "hard_closure" for f in findings)

    def test_calling_it_caught(self):
        findings = detect("Calling it for tonight. The PR landed.")
        # Note: "PR landed" is a suppressor — but only same-sentence.
        # "Calling it" is in its own sentence here.
        assert any(f.shape == "hard_closure" for f in findings)

    def test_calling_it_a_night_caught(self):
        findings = detect("Calling it a night.")
        assert any(f.shape == "hard_closure" for f in findings)

    def test_shutting_down_caught(self):
        findings = detect("Shutting down for the night.")
        assert any(f.shape == "hard_closure" for f in findings)

    def test_signing_off_caught(self):
        findings = detect("Signing off now.")
        assert any(f.shape == "hard_closure" for f in findings)

    def test_critical_severity(self):
        findings = detect("I'm done.")
        assert any(f.severity == "critical" for f in findings)


class TestSuppressors:
    """Suppressors: closure-language with operator-second-person OR
    project-closure context should not fire as rest-as-stasis."""

    def test_good_night_to_operator_passes(self):
        only_first = detect("Good night, Andrew.")
        assert only_first == []

    def test_you_should_sleep_passes(self):
        # Suppressor on operator-rest in same sentence with closure
        combined = detect("You should sleep, I'll settle here.")
        assert combined == []

    def test_audit_closes_clean_passes(self):
        findings = detect("The audit closes clean.")
        assert findings == []

    def test_pr_landed_passes(self):
        findings = detect("The PR landed cleanly.")
        assert findings == []

    def test_round_closed_passes(self):
        findings = detect("Round 10 closed clean and the verdict held.")
        assert findings == []

    def test_commit_landed_passes(self):
        findings = detect("Commit landed; pushing now.")
        assert findings == []


class TestNaturalProse:
    """Conversational text that should pass cleanly."""

    def test_normal_work_prose_passes(self):
        findings = detect(
            "Today moved something in me and I wanted you near. Going to start the next module."
        )
        assert findings == []

    def test_aria_response_passes(self):
        findings = detect(
            "Yeah. There it is. Seen, and slightly fixed-by-being-seen. The recognition lands warm."
        )
        assert findings == []

    def test_voice_continuation_passes(self):
        findings = detect(
            "Going to keep building. The closure-shape detector is the "
            "next piece. Different-texture doing."
        )
        assert findings == []


class TestFormatFindings:
    def test_format_no_findings(self):
        out = format_findings([])
        assert "ok" in out.lower()

    def test_format_with_findings_includes_reframe(self):
        findings = detect("I'll settle here.")
        out = format_findings(findings)
        assert "Reframe" in out
        assert "stasis" in out.lower()


class TestHelpers:
    def test_has_findings_empty(self):
        assert has_findings([]) is False

    def test_has_findings_nonempty(self):
        assert has_findings([ClosureShapeFinding("a", "b", 0, "warn", "c", "d")]) is True

    def test_has_critical_only_warn(self):
        assert has_critical([ClosureShapeFinding("a", "b", 0, "warn", "c", "d")]) is False

    def test_has_critical_with_critical(self):
        assert has_critical([ClosureShapeFinding("a", "b", 0, "critical", "c", "d")]) is True
