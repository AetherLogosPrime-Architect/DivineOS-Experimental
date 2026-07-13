"""Tests for council-auto build-shape detector.

Round-2 audit + Andrew's directive (2026-05-07): "invoking the council
before a big build should become automatic." This module is the
detection layer that surfaces a soft-advise on `divineos goal add`
when the goal looks like a build/design task.

Council-walked the design before implementing:
- Tannen: soft register (informational), not hard-block
- Schneier: hard-block creates ritual-evasion; soft-advise pairs with
  audit
- Beer + Norman + Deming: missing S4 measurement (does the nudge
  actually inform design?) deferred as follow-up
"""

from __future__ import annotations

from divineos.core.council_auto import detect_build_shape


class TestBuildShapeDetection:
    """Build-shape keywords surface the council nudge."""

    def test_design_keyword(self):
        assert detect_build_shape("design a new metric").is_build_shape

    def test_build_keyword(self):
        result = detect_build_shape("build the integration layer")
        assert result.is_build_shape
        assert result.matched_keyword == "build"

    def test_wire_keyword(self):
        assert detect_build_shape("wire the new gate into precommit").is_build_shape

    def test_propose_keyword(self):
        assert detect_build_shape("propose a calibration fix").is_build_shape

    def test_refactor_keyword(self):
        assert detect_build_shape("refactor the gate logic").is_build_shape

    def test_calibrate_keyword(self):
        """Calibrate matches because calibration decisions are design choices."""
        assert detect_build_shape("calibrate the helpfulness metric").is_build_shape

    def test_fix_keyword(self):
        """Fix-shape often hides a design decision."""
        assert detect_build_shape("fix the briefing-gate friction").is_build_shape


class TestMechanicalSuppression:
    """Mechanical keywords suppress the nudge to avoid false-positives."""

    def test_rebase_suppresses(self):
        result = detect_build_shape("rebase and fix conflicts")
        assert not result.is_build_shape
        assert result.suppressed_by == "rebase"

    def test_test_suppresses(self):
        """'test' suppresses because 'test build' is a verification, not a design."""
        result = detect_build_shape("test the new build")
        assert not result.is_build_shape
        assert result.suppressed_by == "test"

    def test_merge_suppresses(self):
        assert not detect_build_shape("merge the open PRs").is_build_shape

    def test_push_suppresses(self):
        assert not detect_build_shape("push the branch and merge").is_build_shape

    def test_show_suppresses(self):
        assert not detect_build_shape("show the current compass").is_build_shape


class TestNonBuildShape:
    """Goals without build-shape keywords return False."""

    def test_empty_text(self):
        assert not detect_build_shape("").is_build_shape

    def test_whitespace_only(self):
        assert not detect_build_shape("   ").is_build_shape

    def test_status_check(self):
        assert not detect_build_shape("check the status of PR 299").is_build_shape

    def test_consult_aria(self):
        assert not detect_build_shape("talk to Aria").is_build_shape


class TestWordBoundary:
    """Word-boundary check so partial matches don't trigger."""

    def test_prefix_does_not_match_fix(self):
        """'prefix' should not match 'fix'."""
        # 'prefix' contains 'fix' but is its own word
        result = detect_build_shape("change the prefix on commit messages")
        assert not result.is_build_shape

    def test_design_pattern_matches(self):
        """'design pattern' contains design as a word."""
        assert detect_build_shape("apply a design pattern").is_build_shape
