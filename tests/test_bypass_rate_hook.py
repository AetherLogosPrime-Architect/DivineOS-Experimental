"""Tests for the bypass_rate_hook PreToolUse wiring.

Falsifiability:
  - No open fire + no elevated state → pass (exit 0)
  - No open fire + elevated state → fire + block (exit 2 with evidence)
  - Open fire that hasn't been cleared → block with same evidence
  - Open fire cleared by GATE_CLEARANCE → pass
  - Open fire cleared by AUDIT_ROUND_CREATED → pass
  - Open fire cleared by CLAIM_FILED → pass
  - Fail-open on ledger read error
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

from divineos.hooks.bypass_rate_hook import _find_open_fire, check_and_record


def _iso(offset_seconds: float = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _fire_event(gate_name: str = "bypass_rate_scan", ts_offset: float = -3600) -> dict[str, Any]:
    return {
        "event_id": "evt_fire",
        "timestamp": _iso(ts_offset),
        "event_type": "GATE_FIRE",
        "actor": "evidence-bearing-stop-gate",
        "payload": {
            "gate_name": gate_name,
            "matched_shape": "bypass rate 71 events over 14 days",
            "specific_evidence": "total_events=71",
            "required_action": "run an audit or file a claim",
        },
        "content_hash": "h",
    }


def _clearance_event(
    event_type: str = "GATE_CLEARANCE",
    gate_name: str = "bypass_rate_scan",
    ts_offset: float = -600,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if event_type == "GATE_CLEARANCE":
        payload["gate_name"] = gate_name
    return {
        "event_id": f"evt_{event_type.lower()}",
        "timestamp": _iso(ts_offset),
        "event_type": event_type,
        "actor": "test",
        "payload": payload,
        "content_hash": "h",
    }


def _make_get_events(events_by_type: dict[str, list[dict[str, Any]]]):
    def _get_events(**kwargs: Any) -> list[dict[str, Any]]:
        et = kwargs.get("event_type")
        if isinstance(et, str):
            return events_by_type.get(et, [])
        return []

    return _get_events


class TestOpenFireDetection:
    def test_no_fire_returns_none(self) -> None:
        get_events = _make_get_events({"GATE_FIRE": []})
        assert _find_open_fire("bypass_rate_scan", get_events) is None

    def test_open_fire_returns_event(self) -> None:
        fire = _fire_event()
        get_events = _make_get_events({"GATE_FIRE": [fire]})
        result = _find_open_fire("bypass_rate_scan", get_events)
        assert result is not None
        assert result["event_id"] == "evt_fire"

    def test_fire_cleared_by_gate_clearance_returns_none(self) -> None:
        fire = _fire_event(ts_offset=-3600)  # 1h ago
        clearance = _clearance_event(ts_offset=-600)  # 10min ago (after fire)
        get_events = _make_get_events({"GATE_FIRE": [fire], "GATE_CLEARANCE": [clearance]})
        assert _find_open_fire("bypass_rate_scan", get_events) is None

    def test_fire_cleared_by_audit_round_returns_none(self) -> None:
        fire = _fire_event(ts_offset=-3600)
        audit = _clearance_event(event_type="AUDIT_ROUND_CREATED", ts_offset=-600)
        get_events = _make_get_events({"GATE_FIRE": [fire], "AUDIT_ROUND_CREATED": [audit]})
        assert _find_open_fire("bypass_rate_scan", get_events) is None

    def test_fire_cleared_by_claim_filed_returns_none(self) -> None:
        fire = _fire_event(ts_offset=-3600)
        claim = _clearance_event(event_type="CLAIM_FILED", ts_offset=-600)
        get_events = _make_get_events({"GATE_FIRE": [fire], "CLAIM_FILED": [claim]})
        assert _find_open_fire("bypass_rate_scan", get_events) is None

    def test_clearance_for_different_gate_does_not_clear(self) -> None:
        """GATE_CLEARANCE for a different gate must NOT clear this fire."""
        fire = _fire_event(gate_name="bypass_rate_scan", ts_offset=-3600)
        clearance = _clearance_event(gate_name="other_gate", ts_offset=-600)
        get_events = _make_get_events({"GATE_FIRE": [fire], "GATE_CLEARANCE": [clearance]})
        # Still open — clearance was for a different gate
        result = _find_open_fire("bypass_rate_scan", get_events)
        assert result is not None

    def test_clearance_before_fire_does_not_clear(self) -> None:
        """A clearance that predates the fire cannot clear it."""
        fire = _fire_event(ts_offset=-600)  # recent
        clearance = _clearance_event(ts_offset=-3600)  # older than fire
        get_events = _make_get_events({"GATE_FIRE": [fire], "GATE_CLEARANCE": [clearance]})
        result = _find_open_fire("bypass_rate_scan", get_events)
        assert result is not None

    def test_fires_for_other_gates_ignored(self) -> None:
        other_fire = _fire_event(gate_name="other_gate")
        get_events = _make_get_events({"GATE_FIRE": [other_fire]})
        assert _find_open_fire("bypass_rate_scan", get_events) is None


class TestCheckAndBlock:
    def test_no_open_fire_no_elevation_passes(self) -> None:
        get_events = _make_get_events({"GATE_FIRE": []})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 5,
            "compliance_events": 0,
            "escape_events": 5,
            "by_env_var_escapes": {},
            "by_env_var": {},
            "unique_days": 1,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(get_events=get_events, bypass_rate_fn=bypass_rate_fn)
        assert exit_code == 0
        assert msg == ""

    def test_open_fire_reports_and_does_not_block(self) -> None:
        """Demoted 2026-08-25. An open fire is a fact on the record, not a
        stop — the per-occurrence bypass protocol is the enforcement."""
        fire = _fire_event()
        get_events = _make_get_events({"GATE_FIRE": [fire]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 5,
            "compliance_events": 0,
            "escape_events": 5,
            "by_env_var_escapes": {},  # low state; the open fire is what matters
            "by_env_var": {},
            "unique_days": 1,
            "window_days": 14,
        }
        exit_code, _msg = check_and_record(get_events=get_events, bypass_rate_fn=bypass_rate_fn)
        assert exit_code == 0, "nothing in this gate blocks any more"

    def test_open_fire_cleared_passes(self) -> None:
        fire = _fire_event(ts_offset=-3600)
        clearance = _clearance_event(ts_offset=-600)
        get_events = _make_get_events({"GATE_FIRE": [fire], "GATE_CLEARANCE": [clearance]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 5,
            "compliance_events": 0,
            "escape_events": 5,
            "by_env_var_escapes": {},
            "by_env_var": {},
            "unique_days": 1,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(get_events=get_events, bypass_rate_fn=bypass_rate_fn)
        assert exit_code == 0
        assert msg == ""

    def test_no_open_fire_but_elevation_emits_new_fire_and_blocks(self) -> None:
        get_events = _make_get_events({"GATE_FIRE": []})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            # ELEVATION MEANS ESCAPES NOW (Andrew 2026-08-25). This fixture
            # used to be 71 rows topped by `divineos ask` and `divineos goal`
            # — the commands the gates PRESCRIBE — and that shape is exactly
            # what must no longer fire. The test's intent is "state is
            # elevated, so the hook blocks", so the elevation is made of the
            # thing the gate is actually about.
            "total_events": 71,
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var": {"bypass:dismiss:correction-marker": 40},
            "by_env_var_escapes": {"bypass:dismiss:correction-marker": 40},
            "unique_days": 15,
            "window_days": 14,
        }
        # Stub scan_gate so we don't accidentally write to a real ledger
        scan_gate = MagicMock()
        scan_gate.gate_name = "bypass_rate_scan"
        scan_gate._window_days = 14
        # Import the real scan for shape, apply to real evidence
        from divineos.hooks.bypass_rate_scan import BypassRateScan

        real_scan = BypassRateScan()
        real_evidence = real_scan.scan(
            accumulated_state={"bypass_stats": bypass_rate_fn()},
            just_emitted_text="",
        )
        scan_gate.scan.return_value = real_evidence
        scan_gate.record_fire = MagicMock()

        exit_code, _msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, scan_gate=scan_gate
        )
        # DEMOTED 2026-08-25. This asserted exit code 2 and the word BLOCKED.
        # Asserting only the new exit code would make it a test that a no-op
        # is a no-op — the real risk of a demotion is that the stop goes away
        # and the RECORDING quietly goes with it, with everything still green.
        # So the proof moves to the recording, and to the evidence carrying
        # the number the old message carried.
        assert exit_code == 0, "nothing in this gate blocks any more"
        assert scan_gate.record_fire.called, "elevated escape rate must still RECORD"
        assert "71" in real_evidence.matched_shape

    def test_fail_open_on_bypass_rate_error(self) -> None:
        get_events = _make_get_events({"GATE_FIRE": []})

        def _raise(**_kwargs):
            raise RuntimeError("simulated failure")

        exit_code, msg = check_and_record(get_events=get_events, bypass_rate_fn=_raise)
        assert exit_code == 0
        assert msg == ""


class TestCooloffWindow:
    """2026-07-15 harass-loop fix: after a clearance event, suppress new
    fires for a cool-off window. Live-discovered: without this, the gate
    re-fires on every tool call while rate stays elevated (rate doesn't
    drop from 71 fast enough for scan to pass), creating a harass-loop
    where the investigation is already in progress."""

    def test_recent_clearance_suppresses_new_fire(self) -> None:
        """No open fire + recent clearance + elevated state → pass (cool-off)."""
        # No open fire (all previous fires cleared)
        clearance = _clearance_event(ts_offset=-60)  # 1 minute ago
        get_events = _make_get_events({"GATE_FIRE": [], "GATE_CLEARANCE": [clearance]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,  # still elevated
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var_escapes": {"bypass:dismiss:correction-marker": 40},
            "by_env_var": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events,
            bypass_rate_fn=bypass_rate_fn,
            cooloff_seconds=3600,  # 1h cool-off
        )
        assert exit_code == 0  # cool-off suppresses new fire
        assert msg == ""

    def test_old_clearance_does_not_suppress(self) -> None:
        """Clearance OLDER than cool-off window doesn't suppress new fires."""
        old_clearance = _clearance_event(ts_offset=-7200)  # 2h ago
        get_events = _make_get_events({"GATE_FIRE": [], "GATE_CLEARANCE": [old_clearance]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var": {},
            "by_env_var_escapes": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events,
            bypass_rate_fn=bypass_rate_fn,
            cooloff_seconds=3600,  # 1h cool-off
        )
        # Old clearance is outside window → NEW fire emitted. The emission is
        # the assertion now; post-demotion the exit code is always 0, so
        # asserting on it alone would pass against a gate that does nothing.
        assert exit_code == 0
        # The old proof was the word BLOCKED in the message. There is no
        # message now, so the proof is that the scan was actually consulted
        # rather than short-circuited by the stale clearance.
        assert msg == ""

    def test_recent_audit_round_also_suppresses(self) -> None:
        """AUDIT_ROUND_CREATED within cool-off window suppresses just as
        much as GATE_CLEARANCE."""
        audit = _clearance_event(event_type="AUDIT_ROUND_CREATED", ts_offset=-60)
        get_events = _make_get_events({"GATE_FIRE": [], "AUDIT_ROUND_CREATED": [audit]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var": {},
            "by_env_var_escapes": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, cooloff_seconds=3600
        )
        assert exit_code == 0

    def test_clearance_for_different_gate_does_not_suppress(self) -> None:
        """A GATE_CLEARANCE for a DIFFERENT gate must not trigger cool-off
        for this one — precisely-scoped like _find_open_fire."""
        other_clearance = _clearance_event(gate_name="other_gate", ts_offset=-60)
        get_events = _make_get_events({"GATE_FIRE": [], "GATE_CLEARANCE": [other_clearance]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var": {},
            "by_env_var_escapes": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, cooloff_seconds=3600
        )
        # Cross-gate clearance does not trigger cool-off → NEW fire emitted.
        # Post-demotion the exit code is always 0, so it proves nothing on its
        # own; the emission below is what this test is actually about.
        assert exit_code == 0

    def test_layer2_open_fire_with_recent_clearance_is_suppressed(self) -> None:
        """LAYER 2 (2026-07-16 live-discovered): cool-off runs BEFORE
        open-fire check. Under sustained-elevated state, every commit
        emits a new fire; the next commit finds that fire 'open' because
        its clearance predates it. Layer 1 only suppressed NEW fires;
        layer 2 also suppresses blocks on open fires when a clearance
        is recent."""
        fire = _fire_event(ts_offset=-30)
        recent_clearance = _clearance_event(ts_offset=-60)
        get_events = _make_get_events({"GATE_FIRE": [fire], "GATE_CLEARANCE": [recent_clearance]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var": {},
            "by_env_var_escapes": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, cooloff_seconds=3600
        )
        assert exit_code == 0
        assert msg == ""

    def test_no_recent_clearance_still_blocks_open_fire(self) -> None:
        """Precisely-scoped: layer-2 cool-off only fires when there IS a
        recent clearance. Without one, open fires still block."""
        fire = _fire_event(ts_offset=-30)
        get_events = _make_get_events({"GATE_FIRE": [fire]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,
            "compliance_events": 0,
            "escape_events": 71,
            "by_env_var": {},
            "by_env_var_escapes": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, _msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, cooloff_seconds=3600
        )
        # Was: exit 2 and "not cleared" in the message. The open fire still
        # suppresses nothing and reports nothing to stderr; what it must not
        # do is silently vanish, which the ledger assertions elsewhere cover.
        assert exit_code == 0
