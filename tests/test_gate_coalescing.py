"""GATE-GATE 2026-06-03: the engagement-discipline gates (goal / engagement /
consultation) coalesce into one deny instead of surfacing single-file.

The chain was first-deny-wins, so a turn missing all three hit them one at a
time (clear goal -> retry -> hit engagement -> retry -> hit consultation).
Now they are collected and surfaced together. Hard safety walls still
short-circuit individually and take precedence.

Falsifiability:
  - _combine_engagement_denies returns a single message UNCHANGED (so isolated
    gate behaviour and existing tests are preserved).
  - With >= 2 soft gates failing it returns one combined message containing
    every gate's text plus the coalescing header.
  - _check_gates, with goal+engagement+consultation all failing and the hard
    walls passing, returns ONE deny carrying all three.
"""

from __future__ import annotations

import pytest

from divineos.core import (
    briefing_id,
    compass_required_marker,
    consultation_tracker,
    correction_marker,
    hedge_marker,
    hud_handoff,
    hud_state,
    mansion_quiet_marker,
    pull_detection,
    session_briefing_gate,
    stale_engagement,
)
from divineos.hooks import pre_tool_use_gate


class TestCombineEngagementDenies:
    def test_single_deny_returned_unchanged(self):
        msg = "BLOCKED: No goal set for this session. Run: divineos goal add ..."
        assert pre_tool_use_gate._combine_engagement_denies([msg]) == msg

    def test_multiple_denies_coalesced_with_all_text(self):
        a = "BLOCKED: No goal set for this session."
        b = "BLOCKED: 30 code actions since last thinking command."
        c = "BLOCKED: 5 responses without consulting the substrate."
        out = pre_tool_use_gate._combine_engagement_denies([a, b, c])
        # The header signals coalescing, and every gate's body survives.
        assert "3 engagement checks" in out
        assert "one pass" in out
        assert "No goal set" in out
        assert "30 code actions" in out
        assert "5 responses without consulting" in out
        # Numbered so they are scannable.
        assert "[1]" in out and "[2]" in out and "[3]" in out


class TestCheckGatesCoalesces:
    @pytest.fixture
    def isolate(self, tmp_path, monkeypatch):
        """Pass every gate except the three under test; route all markers to
        non-existent tmp paths so no real session state leaks in."""
        # Briefing gates pass.
        monkeypatch.setattr(hud_handoff, "was_briefing_loaded", lambda: True)
        monkeypatch.setattr(session_briefing_gate, "briefing_loaded_this_session", lambda: True)
        # Briefing-id challenge passes (added to gate ordering 2026-06-20). Without this
        # mock, the challenge fires before any engagement gate the test is targeting.
        monkeypatch.setattr(briefing_id, "is_fresh", lambda *a, **k: True)
        # Hard / complex gates all pass.
        monkeypatch.setattr(hud_handoff, "compass_staleness_status", lambda: {"stale": False})
        monkeypatch.setattr(mansion_quiet_marker, "is_quiet_active", lambda: False)
        monkeypatch.setattr(stale_engagement, "blocked_areas", lambda: [])
        monkeypatch.setattr(pull_detection, "last_check", lambda: None)
        for mod in (correction_marker, compass_required_marker, hedge_marker):
            monkeypatch.setattr(mod, "marker_path", lambda _m=mod: tmp_path / f"{_m.__name__}.json")
        return monkeypatch

    def test_three_soft_gates_coalesce_into_one_deny(self, isolate):
        # Fire all three engagement-discipline gates.
        isolate.setattr(hud_state, "has_session_fresh_goal", lambda: False)
        isolate.setattr(
            hud_handoff,
            "engagement_status",
            lambda: {"engaged": False, "state": "drift", "code_actions_since": 42},
        )
        isolate.setattr(
            consultation_tracker, "consultation_gate_status", lambda *a, **k: {"stale": True}
        )
        isolate.setattr(
            consultation_tracker,
            "gate_channel_message",
            lambda: "BLOCKED: 6 responses without consulting the substrate.",
        )

        decision = pre_tool_use_gate._check_gates()
        assert decision is not None
        reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
        # One deny carrying ALL THREE — not just the first.
        assert "engagement checks" in reason
        assert "No goal set" in reason
        assert "42 code actions" in reason
        assert "6 responses without consulting" in reason

    def test_single_soft_gate_message_unchanged(self, isolate):
        # Only goal fails; engagement + consultation pass.
        isolate.setattr(hud_state, "has_session_fresh_goal", lambda: False)
        isolate.setattr(hud_handoff, "engagement_status", lambda: {"engaged": True})
        isolate.setattr(
            consultation_tracker, "consultation_gate_status", lambda *a, **k: {"stale": False}
        )
        decision = pre_tool_use_gate._check_gates()
        assert decision is not None
        reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
        # Unchanged single message — no coalescing header.
        assert reason.startswith("BLOCKED: No goal set")
        assert "engagement checks" not in reason
