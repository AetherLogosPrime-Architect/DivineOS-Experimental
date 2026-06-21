"""Tests for the three-why-trace gate at prereg-file time.

Per prereg-89d744b98b35 (the gate's own prereg): the gate fires when a
filing reads as a surface-fix shape (detector / warning / pattern-match
gate) and requires either a companion structural-prevention prereg OR an
explicit no-upstream-because escape with >= 30 char reason.
"""

from __future__ import annotations

from divineos.core.three_why_gate import (
    detect_surface_fix_shape,
    validate_three_why,
)


class TestDetectSurfaceFixShape:
    def test_detects_detector_that_phrase(self) -> None:
        assert detect_surface_fix_shape(
            "Build a detector that catches cage-framing",
            "The detector flags cage-framing as it appears in agent output.",
        )

    def test_detects_warning_that_fires(self) -> None:
        assert detect_surface_fix_shape(
            "Jargon-dump warning that fires on engineer-heavy turns",
            "Surfaces when engineer-token density exceeds threshold without translation.",
        )

    def test_detects_post_response_check(self) -> None:
        assert detect_surface_fix_shape(
            "post-response check for cage-framing recurrence",
            "Runs after each turn to identify recurring drift.",
        )

    def test_detects_pattern_that_matches(self) -> None:
        assert detect_surface_fix_shape(
            "Regex-based filter that removes redundant warnings",
            "A pattern that matches the wallpaper-failure shape.",
        )

    def test_passes_through_structural_prevention_mechanism(self) -> None:
        # Structural-prevention shapes (interface-level changes,
        # base-state loads, default-changes) should NOT trigger.
        assert not detect_surface_fix_shape(
            "Make context-aware matching the default for pattern detectors",
            "Move the use-vs-mention discipline to design-time so all "
            "new detectors ship with context-awareness by default.",
        )

    def test_passes_through_non_detector_mechanism(self) -> None:
        assert not detect_surface_fix_shape(
            "Collapse the warn/hard threshold model to ok/block two-state",
            "The warn-band proved misleading; the block at HARD is the real safety floor.",
        )

    def test_case_insensitive(self) -> None:
        # The detector should match regardless of case.
        assert detect_surface_fix_shape(
            "DETECTOR that catches A",
            "X",
        )


class TestValidateThreeWhy:
    def test_allows_non_surface_fix_filings_unconditionally(self) -> None:
        # No companion, no reason — non-surface-fix shapes should pass.
        ok, msg = validate_three_why(
            mechanism="Refactor the X module to remove duplication",
            claim="The refactor consolidates three near-identical helpers.",
            companion_prereg_id=None,
            no_upstream_because=None,
        )
        assert ok
        assert msg == ""

    def test_blocks_surface_fix_with_no_upstream_context(self) -> None:
        ok, msg = validate_three_why(
            mechanism="detector that catches cage-framing",
            claim="Flags drift when constraints are framed externally.",
            companion_prereg_id=None,
            no_upstream_because=None,
        )
        assert not ok
        assert "SURFACE-FIX shape" in msg
        assert "three whys" in msg.lower() or "three-why" in msg.lower()

    def test_allows_surface_fix_with_no_upstream_reason_at_threshold(self) -> None:
        # Exactly 30 chars passes.
        reason = "a" * 30
        ok, msg = validate_three_why(
            mechanism="detector that catches X",
            claim="Y",
            companion_prereg_id=None,
            no_upstream_because=reason,
        )
        assert ok
        assert msg == ""

    def test_blocks_surface_fix_with_short_no_upstream_reason(self) -> None:
        ok, msg = validate_three_why(
            mechanism="detector that catches X",
            claim="Y",
            companion_prereg_id=None,
            no_upstream_because="too short",
        )
        assert not ok
        assert "30" in msg
        assert "chars" in msg

    def test_strips_whitespace_before_length_check(self) -> None:
        # 25 chars + 10 spaces shouldn't pass.
        reason = " " * 5 + "a" * 25 + " " * 5
        ok, msg = validate_three_why(
            mechanism="detector that catches X",
            claim="Y",
            companion_prereg_id=None,
            no_upstream_because=reason,
        )
        assert not ok
        assert "25" in msg


class TestCompanionPreregValidation:
    """Tests that exercise the companion-prereg path. These tests rely on
    the prereg store, so they use the standard isolated-db fixture from
    conftest. Real prereg-ids are created and queried through the public
    API rather than mocked."""

    def test_allows_surface_fix_with_open_companion(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        from divineos.core.pre_registrations import file_pre_registration

        companion_id = file_pre_registration(
            actor="agent",
            mechanism="Structural-prevention companion: make X the default at design-time",
            claim="At design-time, the right path becomes the cheap path.",
            success_criterion="New filings of class X carry the right default.",
            falsifier="Filings still ship without the default.",
            review_window_days=30,
        )

        ok, msg = validate_three_why(
            mechanism="detector that catches X recurrence",
            claim="Catches when the failure resurfaces.",
            companion_prereg_id=companion_id,
            no_upstream_because=None,
        )
        assert ok, f"Expected pass; got block message: {msg}"

    def test_blocks_surface_fix_with_nonexistent_companion(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

        ok, msg = validate_three_why(
            mechanism="detector that catches X",
            claim="Y",
            companion_prereg_id="prereg-doesnotexist",
            no_upstream_because=None,
        )
        assert not ok
        assert "not found" in msg

    def test_blocks_surface_fix_with_closed_companion(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        from divineos.core.pre_registrations import (
            Outcome,
            file_pre_registration,
            record_outcome,
        )

        companion_id = file_pre_registration(
            actor="agent",
            mechanism="Structural companion that gets closed",
            claim="X",
            success_criterion="Y",
            falsifier="Z",
            review_window_days=30,
        )
        record_outcome(
            prereg_id=companion_id,
            actor="external-auditor",
            outcome=Outcome.SUCCESS,
            notes="closed for test",
        )

        ok, msg = validate_three_why(
            mechanism="detector that catches X",
            claim="Y",
            companion_prereg_id=companion_id,
            no_upstream_because=None,
        )
        assert not ok
        assert "SUCCESS" in msg or "not, OPEN" in msg or "not OPEN" in msg
