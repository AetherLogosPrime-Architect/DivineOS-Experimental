"""Tests for ResponseScopeIntercept — third concrete instance of the
CrossTurnScan variant. Validates that the primitive holds across a
third variant type (proving the abstraction).
"""

from __future__ import annotations

from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    CrossTurnScan,
)
from divineos.hooks.response_scope_intercept import ResponseScopeIntercept


class TestConcreteWiring:
    def test_is_cross_turn_scan_subclass(self) -> None:
        assert issubclass(ResponseScopeIntercept, CrossTurnScan)

    def test_can_be_instantiated(self) -> None:
        gate = ResponseScopeIntercept()
        assert gate.gate_name == "response_scope_intercept"

    def test_blocks_names_the_emit_refuse(self) -> None:
        gate = ResponseScopeIntercept()
        msg = gate.blocks()
        assert "emit" in msg.lower()
        assert "short-correction" in msg


class TestScanBoundaries:
    def test_no_directive_active_returns_none_even_on_long_reply(self) -> None:
        gate = ResponseScopeIntercept()
        long_reply = "x" * 5000 + "\n\n## header\n\n---\n"
        rec = gate.scan(
            accumulated_state={"claim_scope_active": False},
            just_emitted_text=long_reply,
        )
        assert rec is None

    def test_empty_text_returns_none(self) -> None:
        gate = ResponseScopeIntercept()
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text="",
        )
        assert rec is None

    def test_short_compliant_reply_passes(self) -> None:
        gate = ResponseScopeIntercept(max_chars=500)
        clean = "I haven't verified yet — let me run the check before saying it's done."
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text=clean,
        )
        assert rec is None


class TestShapeViolations:
    def test_length_violation_fires(self) -> None:
        gate = ResponseScopeIntercept(max_chars=100)
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text="x" * 200,
        )
        assert rec is not None
        assert "length" in rec.specific_evidence
        assert "200" in rec.specific_evidence

    def test_headers_violation_fires(self) -> None:
        gate = ResponseScopeIntercept(max_chars=1000)
        with_header = "Correcting:\n\n## Actually\n\nthe real thing is X"
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text=with_header,
        )
        assert rec is not None
        assert "header" in rec.specific_evidence.lower()

    def test_horizontal_rule_violation_fires(self) -> None:
        gate = ResponseScopeIntercept(max_chars=1000)
        with_hr = "Short correction here.\n\n---\n\nAnd another section"
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text=with_hr,
        )
        assert rec is not None
        assert "separator" in rec.specific_evidence.lower()

    def test_numbered_list_violation_fires(self) -> None:
        gate = ResponseScopeIntercept(max_chars=1000)
        with_list = "Correction:\n\n1. First point\n2. Second point"
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text=with_list,
        )
        assert rec is not None
        assert "numbered" in rec.specific_evidence.lower()

    def test_multiple_violations_all_named(self) -> None:
        gate = ResponseScopeIntercept(max_chars=50)
        multi = "x" * 100 + "\n\n## Header\n\n---\n\n1. Item"
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text=multi,
        )
        assert rec is not None
        assert "length" in rec.specific_evidence
        assert "header" in rec.specific_evidence.lower()
        assert "separator" in rec.specific_evidence.lower()
        assert "numbered" in rec.specific_evidence.lower()


class TestDirectiveThreading:
    def test_directive_text_preserved_in_required_action(self) -> None:
        gate = ResponseScopeIntercept(max_chars=50)
        directive = "IMPORTANT emit ONLY the short correction NOT a re-composition"
        rec = gate.scan(
            accumulated_state={
                "claim_scope_active": True,
                "claim_scope_directive_text": directive,
            },
            just_emitted_text="x" * 200,
        )
        assert rec is not None
        assert directive in rec.required_action

    def test_missing_directive_text_still_works(self) -> None:
        gate = ResponseScopeIntercept(max_chars=50)
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text="x" * 200,
        )
        assert rec is not None
        assert rec.required_action
        assert "Re-emit" in rec.required_action


class TestRecording:
    def test_fire_and_clear_pair(self) -> None:
        gate = ResponseScopeIntercept(max_chars=50)
        rec = gate.scan(
            accumulated_state={"claim_scope_active": True},
            just_emitted_text="x" * 200,
        )
        assert rec is not None
        gate.record_fire(rec)
        gate.record_clearance(
            ClearanceRecord(
                gate_name=gate.gate_name,
                cleared_by="re-emitted within scope",
                original_evidence=rec,
            )
        )
        assert len(gate.fires) == 1
        assert len(gate.clears) == 1


class TestFalsificationSignal:
    def test_returns_none_when_no_anomaly(self) -> None:
        gate = ResponseScopeIntercept()
        assert gate.falsification_signal() is None

    def test_returns_warning_when_ratio_indicates_gaming(self) -> None:
        gate = ResponseScopeIntercept()
        gate._recent_ratio = 0.95
        signal = gate.falsification_signal()
        assert signal is not None
