"""Tests for the engagement half-threshold disclosure surface.

Surface fills the gap between "silent gate" and "blocked gate" with a
soft disclosure when code_actions_since reaches HALF the active
threshold. Disclose-not-construct: surface only makes-visible.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import engagement_disclosure_surface


class TestFormatForBriefing:
    """Surface returns text only in the [half, full) band."""

    def test_empty_when_below_half_threshold(self):
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 5,
                "threshold": 20,
                "state": "engaged",
                "deep_actions_since": 0,
                "deep_threshold": 30,
            },
        ):
            assert engagement_disclosure_surface.format_for_briefing() == ""

    def test_surface_when_at_half_threshold(self):
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 10,
                "threshold": 20,
                "state": "engaged",
                "deep_actions_since": 0,
                "deep_threshold": 30,
            },
        ):
            out = engagement_disclosure_surface.format_for_briefing()
            assert "ENGAGEMENT CHECKPOINT" in out
            assert "10/20" in out
            assert "10 remaining" in out

    def test_surface_in_band(self):
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 15,
                "threshold": 20,
                "state": "engaged",
                "deep_actions_since": 0,
                "deep_threshold": 30,
            },
        ):
            out = engagement_disclosure_surface.format_for_briefing()
            assert "15/20" in out
            assert "5 remaining" in out

    def test_silent_above_full_threshold(self):
        """Above full, the gate's enforcement message is the surface, not this one."""
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 25,
                "threshold": 20,
                "state": "drift",
                "deep_actions_since": 0,
                "deep_threshold": 30,
            },
        ):
            assert engagement_disclosure_surface.format_for_briefing() == ""

    def test_silent_at_threshold_exactly(self):
        """The full-threshold value is the gate's territory, not the surface's."""
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 20,
                "threshold": 20,
                "state": "drift",
                "deep_actions_since": 0,
                "deep_threshold": 30,
            },
        ):
            assert engagement_disclosure_surface.format_for_briefing() == ""

    def test_deep_warning_appended_when_deep_actions_high(self):
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 12,
                "threshold": 20,
                "state": "engaged",
                "deep_actions_since": 16,
                "deep_threshold": 30,
            },
        ):
            out = engagement_disclosure_surface.format_for_briefing()
            assert "16/30" in out
            assert "ask/recall/briefing" in out

    def test_no_deep_warning_when_below_half(self):
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 12,
                "threshold": 20,
                "state": "engaged",
                "deep_actions_since": 5,
                "deep_threshold": 30,
            },
        ):
            out = engagement_disclosure_surface.format_for_briefing()
            assert "5/30" not in out
            assert "ask/recall/briefing" not in out

    def test_fail_open_on_threshold_zero(self):
        """Threshold of 0 (engagement marker absent or pathological) returns empty."""
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 0,
                "threshold": 0,
                "state": "fresh",
            },
        ):
            assert engagement_disclosure_surface.format_for_briefing() == ""

    def test_fail_open_on_status_exception(self):
        """If engagement_status raises, the surface returns empty (no breakage)."""

        def _boom():
            raise RuntimeError("synthetic failure")

        with patch(
            "divineos.core.hud_handoff.engagement_status",
            side_effect=_boom,
        ):
            assert engagement_disclosure_surface.format_for_briefing() == ""

    def test_state_appended_when_not_engaged(self):
        """When state is not 'engaged', surface notes it for context."""
        with patch(
            "divineos.core.hud_handoff.engagement_status",
            return_value={
                "code_actions_since": 12,
                "threshold": 20,
                "state": "drift",  # somehow drift inside the band — surface still notes it
                "deep_actions_since": 0,
                "deep_threshold": 30,
            },
        ):
            out = engagement_disclosure_surface.format_for_briefing()
            assert "engagement state: drift" in out
