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

    # REMOVED 2026-06-20 (Aether): test_routine_ttl_expiry_returns_soft_advise
    # pinned the old wall-clock TTL behavior (5h marker → soft-advise) which
    # the Gate 1 rewrite explicitly replaced. The new gate uses briefing-ID
    # recall, not wall-clock — there is no "routine TTL-expiry" state to
    # pin. Behavior pin for the new gate lives in
    # test_pre_tool_use_gate_enforcement_pin.py (block emission literal)
    # and in TestGate1BriefingIdRecall below (fresh-passes, stale-denies).

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


class TestGate1BriefingIdRecall:
    """Pin for the Gate 1 rewrite 2026-06-20 (consult-9a8ba69e9598,
    prereg-933233700f06). The wall-clock TTL gate was replaced with
    briefing-ID recall: the gate fires when ``is_fresh()`` returns
    False, regardless of wall-clock time-passed."""

    def test_fresh_briefing_id_allows_proceed(self):
        """When the recall-window is fresh, the gate does NOT hard-deny
        on briefing-staleness grounds."""
        with patch("divineos.core.briefing_id.is_fresh", return_value=True):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.py"}})
            reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
            assert "BRIEFING-ID CHALLENGE" not in reason, (
                f"Fresh briefing-ID should not trigger recall challenge. Got: {reason}"
            )

    def test_stale_briefing_id_hard_denies(self):
        """When the recall-window is stale, the gate hard-denies with
        the recall-challenge message."""
        with patch("divineos.core.briefing_id.is_fresh", return_value=False):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.py"}})
            decision = result.get("hookSpecificOutput", {}).get("permissionDecision")
            reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
            assert decision == "deny", f"Stale briefing-ID should hard-deny. Got: {result}"
            assert "BRIEFING-ID CHALLENGE" in reason, (
                f"Deny should carry the recall-challenge message. Got: {reason}"
            )

    def test_low_friction_write_exempt_from_recall_challenge(self):
        """Letters to family and exploration writes bypass the recall
        gate even when the briefing-ID is stale. Preserves the operator
        directive 2026-04-27 exemption across the gate swap.

        _check_gates returns None when no gate fires (the exemption
        succeeded). If it returns a dict, assert the recall-challenge
        is not the reason."""
        with patch("divineos.core.briefing_id.is_fresh", return_value=False):
            from divineos.hooks.pre_tool_use_gate import _check_gates

            result = _check_gates(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "family/letters/aether-to-aria-2026-06-20-test.md"},
                }
            )
            if result is None:
                return
            reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
            assert "BRIEFING-ID CHALLENGE" not in reason, (
                f"Low-friction write should bypass recall-challenge. Got: {reason}"
            )
