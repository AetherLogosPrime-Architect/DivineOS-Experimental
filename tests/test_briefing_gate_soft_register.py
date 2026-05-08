"""Tests for the briefing-gate soft-advise vs hard-deny register fix.

Round-2 audit (2026-05-07): the briefing gate fired with hard-deny
("BLOCKED:") for routine session-id rotation between continuous-work
tool calls. The agent learned the workaround (chain ``divineos briefing
>/dev/null 2>&1`` into every Bash) and stopped reading gate content.
Goodhart trap.

The fix:
- Hard-deny only on truly-stale state (>24h since briefing-load OR
  marker missing entirely)
- Soft-advise (informational additionalContext, allow proceed) for
  routine rotation cases
- Diagnostic output names WHY the gate-state is stale (TTL expired vs
  session-id mismatch vs marker missing)
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.hooks.pre_tool_use_gate import (
    _briefing_diagnostic,
    _make_deny,
    _make_soft_advise,
    _TRULY_STALE_AGE_SECONDS,
)


class TestSoftAdviseFormat:
    """The soft-advise output is structurally distinct from hard-deny."""

    def test_soft_advise_uses_allow_decision(self):
        out = _make_soft_advise("test message")
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_soft_advise_carries_additional_context(self):
        out = _make_soft_advise("test message")
        assert out["hookSpecificOutput"]["additionalContext"] == "test message"

    def test_hard_deny_uses_deny_decision(self):
        out = _make_deny("test reason")
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hard_deny_carries_reason_not_context(self):
        out = _make_deny("test reason")
        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "test reason"
        assert "additionalContext" not in out["hookSpecificOutput"]


class TestBriefingDiagnostic:
    """Diagnostic message names which condition triggered the staleness."""

    def test_marker_missing_message(self):
        info = {"loaded": False}
        msg = _briefing_diagnostic(info)
        assert "marker missing" in msg

    def test_recent_load_age_in_message(self):
        info = {
            "loaded": True,
            "age_seconds": 7200,
            "ttl_seconds": 14400,
            "ttl_expired": False,
            "calls_since": 50,
            "threshold": 1500,
        }
        msg = _briefing_diagnostic(info)
        assert "2.0h ago" in msg
        assert "50 tool calls" in msg

    def test_ttl_expired_message(self):
        info = {
            "loaded": True,
            "age_seconds": 18000,
            "ttl_seconds": 14400,
            "ttl_expired": True,
            "calls_since": 100,
            "threshold": 1500,
        }
        msg = _briefing_diagnostic(info)
        assert "TTL expired" in msg
        assert "4h" in msg


class TestTrulyStaleThreshold:
    """The 24h hard-block threshold is recognized."""

    def test_threshold_is_24_hours(self):
        assert _TRULY_STALE_AGE_SECONDS == 24 * 3600


class TestGate1RegisterFix:
    """Gate 1 (TTL-based) hard-denies on truly-stale, soft-advises on routine."""

    def test_routine_ttl_expiry_returns_soft_advise(self):
        """5-hour-old marker (TTL=4h) is routine-stale, not truly-stale.
        Should produce soft-advise, not deny."""
        with (
            patch(
                "divineos.core.hud_handoff.was_briefing_loaded",
                return_value=False,
            ),
            patch(
                "divineos.core.hud_handoff.briefing_staleness",
                return_value={
                    "loaded": True,
                    "age_seconds": 5 * 3600,
                    "ttl_seconds": 4 * 3600,
                    "ttl_expired": True,
                    "calls_since": 100,
                    "threshold": 1500,
                    "stale": True,
                },
            ),
        ):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates({"tool_name": "Edit", "tool_input": {}})
            decision = result.get("hookSpecificOutput", {}).get("permissionDecision")
            assert decision != "deny", (
                f"Routine TTL-expiry should soft-advise, not deny. Got: {result}"
            )

    def test_truly_stale_marker_missing_hard_denies(self):
        """No marker at all -> truly stale -> hard deny."""
        with (
            patch(
                "divineos.core.hud_handoff.was_briefing_loaded",
                return_value=False,
            ),
            patch(
                "divineos.core.hud_handoff.briefing_staleness",
                return_value={
                    "loaded": False,
                    "age_seconds": 0,
                    "ttl_seconds": 4 * 3600,
                    "ttl_expired": False,
                    "calls_since": 0,
                    "threshold": 1500,
                    "stale": True,
                },
            ),
        ):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates({"tool_name": "Edit", "tool_input": {}})
            decision = result.get("hookSpecificOutput", {}).get("permissionDecision")
            assert decision == "deny"

    def test_truly_stale_age_exceeds_24h_hard_denies(self):
        """25-hour-old marker -> past truly-stale threshold -> hard deny."""
        with (
            patch(
                "divineos.core.hud_handoff.was_briefing_loaded",
                return_value=False,
            ),
            patch(
                "divineos.core.hud_handoff.briefing_staleness",
                return_value={
                    "loaded": True,
                    "age_seconds": 25 * 3600,
                    "ttl_seconds": 4 * 3600,
                    "ttl_expired": True,
                    "calls_since": 200,
                    "threshold": 1500,
                    "stale": True,
                },
            ),
        ):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates({"tool_name": "Edit", "tool_input": {}})
            decision = result.get("hookSpecificOutput", {}).get("permissionDecision")
            assert decision == "deny"


class TestGate11SessionMismatchSoftAdvise:
    """Gate 1.1 (per-session) always soft-advises on session-id mismatch."""

    def test_session_mismatch_does_not_hard_deny(self):
        with (
            patch(
                "divineos.core.hud_handoff.was_briefing_loaded",
                return_value=True,
            ),
            patch(
                "divineos.core.session_briefing_gate.briefing_loaded_this_session",
                return_value=False,
            ),
        ):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates({"tool_name": "Edit", "tool_input": {}})
            decision = result.get("hookSpecificOutput", {}).get("permissionDecision")
            if decision == "deny":
                reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
                assert "session_id" not in reason and "per-session" not in reason, (
                    f"Per-session mismatch should not hard-deny. Got: {reason}"
                )
