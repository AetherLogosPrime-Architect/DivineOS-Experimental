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


class TestCheckAndRecord:
    def test_no_open_fire_no_elevation_passes(self) -> None:
        get_events = _make_get_events({"GATE_FIRE": []})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 5,
            "by_env_var": {},
            "unique_days": 1,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(get_events=get_events, bypass_rate_fn=bypass_rate_fn)
        assert exit_code == 0
        assert msg == ""

    def test_open_fire_blocks(self) -> None:
        fire = _fire_event()
        get_events = _make_get_events({"GATE_FIRE": [fire]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 5,  # even low state — open fire still blocks
            "by_env_var": {},
            "unique_days": 1,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(get_events=get_events, bypass_rate_fn=bypass_rate_fn)
        # DEMOTED 2026-08-25: this asserted exit 2 and "BLOCKED". The question
        # it was asking -- does an uncleared fire still get REPORTED -- is the
        # right one and is kept. Only the proof moved, from the stop to the
        # report, because flipping it to assert exit 0 would have made it a
        # test that a no-op is a no-op. That is the specific hazard of a
        # demotion (Aria, 2026-08-25): the stop goes away, the RECORDING
        # quietly leaves with it, and the suite stays green throughout because
        # it was only ever watching the stop.
        assert exit_code == 0
        assert "standing rate" in msg
        assert "RECORDS and does not stop" in msg

    def test_open_fire_cleared_passes(self) -> None:
        fire = _fire_event(ts_offset=-3600)
        clearance = _clearance_event(ts_offset=-600)
        get_events = _make_get_events({"GATE_FIRE": [fire], "GATE_CLEARANCE": [clearance]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 5,
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
            "total_events": 71,
            "by_env_var": {"cmd:divineos ask": 14, "cmd:divineos goal": 14},
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

        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, scan_gate=scan_gate
        )
        # The elevated case is where the demotion could have gone silent, so
        # this is the one that carries the weight now: the fire must still be
        # RECORDED, and the evidence must still carry the number the old
        # BLOCKED message carried.
        assert exit_code == 0
        assert scan_gate.record_fire.called
        assert "71" in msg
        assert "escape rate recorded" in msg

    def test_fail_open_on_bypass_rate_error(self) -> None:
        get_events = _make_get_events({"GATE_FIRE": []})

        def _raise(**_kwargs):
            raise RuntimeError("simulated failure")

        exit_code, msg = check_and_record(get_events=get_events, bypass_rate_fn=_raise)
        assert exit_code == 0
        assert msg == ""


class TestTheRecordingCannotLeaveWithTheStop:
    """Aria named this as the specific hazard of a demotion, 2026-08-25.

    Five tests proved this gate worked by asserting it BLOCKED. Flipping them
    to assert it does not block would have made them tests that a no-op is a
    no-op -- and then the recording could quietly disappear too, with the
    suite green throughout, because it was only ever watching the stop.

    A suite that tests a gate's refusal is blind to the gate's other job, and
    demotion is the moment that blindness turns into silence. Third shape in
    the fake-green catalogue, alongside the far-from-live fixture and the
    one-directional coupling test -- all three look like rigour and measure
    the wrong half.
    """

    def test_nothing_returns_a_blocking_exit_code_any_more(self) -> None:
        """The demotion is the point: no path may return 2."""
        import inspect

        from divineos.hooks import bypass_rate_hook

        source = inspect.getsource(bypass_rate_hook.check_and_record)
        assert "return 2" not in source

    def test_the_deny_message_builder_is_gone_not_merely_unused(self) -> None:
        """Text a demoted gate no longer prints is the stale-teaching-surface
        class. Deleted rather than left with the exit code changed."""
        from divineos.hooks import bypass_rate_hook

        assert not hasattr(bypass_rate_hook, "_format_block_message")
        assert hasattr(bypass_rate_hook, "_format_record_message")

    def test_hook_main_prints_whenever_there_is_a_message(self) -> None:
        """It printed only when the exit code was 2. Keeping that condition
        after the demotion would have left a hook that runs, computes, and
        says nothing -- silence every test would still have called passing."""
        import inspect

        from divineos.hooks import bypass_rate_hook

        source = inspect.getsource(bypass_rate_hook.hook_main)
        assert "if message:" in source
        assert "exit_code == 2" not in source

    def test_an_elevated_window_still_reaches_the_ledger(self) -> None:
        """The load-bearing one. record_fire is the whole job now."""
        get_events = _make_get_events({"GATE_FIRE": []})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "escape_events": 71,
            "total_events": 71,
            "by_env_var_escape": {"DIVINEOS_SKIP_TESTS": 71},
            "by_env_var": {"DIVINEOS_SKIP_TESTS": 71},
            "unique_days": 15,
            "window_days": 14,
        }
        from divineos.hooks.bypass_rate_scan import BypassRateScan

        scan_gate = MagicMock()
        scan_gate.gate_name = "bypass_rate_scan"
        scan_gate._window_days = 14
        scan_gate.scan.return_value = BypassRateScan().scan(
            accumulated_state={"bypass_stats": bypass_rate_fn()}, just_emitted_text=""
        )
        scan_gate.record_fire = MagicMock()

        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, scan_gate=scan_gate
        )
        assert exit_code == 0
        assert scan_gate.record_fire.called, (
            "the stop is gone; if the recording goes with it the gate becomes "
            "a hook that runs and says nothing, and every other test here "
            "would still pass"
        )
        assert "71" in msg


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
            "by_env_var": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events,
            bypass_rate_fn=bypass_rate_fn,
            cooloff_seconds=3600,  # 1h cool-off
        )
        # Old clearance is outside window -> NEW fire emitted. The question is
        # whether a fire is EMITTED, which survives the demotion intact; only
        # the evidence of emission moved from the stop to the report.
        assert exit_code == 0
        assert "escape rate recorded" in msg

    def test_recent_audit_round_also_suppresses(self) -> None:
        """AUDIT_ROUND_CREATED within cool-off window suppresses just as
        much as GATE_CLEARANCE."""
        audit = _clearance_event(event_type="AUDIT_ROUND_CREATED", ts_offset=-60)
        get_events = _make_get_events({"GATE_FIRE": [], "AUDIT_ROUND_CREATED": [audit]})
        bypass_rate_fn = lambda window_days=14: {  # noqa: E731
            "total_events": 71,
            "by_env_var": {},
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
            "by_env_var": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, cooloff_seconds=3600
        )
        # Cross-gate clearance does not trigger cool-off -> NEW fire emitted.
        assert exit_code == 0
        assert "escape rate recorded" in msg

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
            "by_env_var": {},
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
            "by_env_var": {},
            "unique_days": 14,
            "window_days": 14,
        }
        exit_code, msg = check_and_record(
            get_events=get_events, bypass_rate_fn=bypass_rate_fn, cooloff_seconds=3600
        )
        assert exit_code == 0
        assert "standing rate" in msg
