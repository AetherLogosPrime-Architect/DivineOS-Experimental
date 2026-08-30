"""Tests for DistancingIntercept — first concrete instance of
IntraTurnIntercept from the EvidenceBearingStopGate primitive.

Falsifiability:
  - No distancing in text → scan_text returns None.
  - Distancing present → EvidenceRecord names shape + trigger + position.
  - Multiple shapes fire together → single record groups by shape.
  - The addressed_to_father toggle gates OPERATOR_THIRD_PERSON as the
    underlying detector documents.
  - The detector's illustrative-context exemption is respected (backticks
    and parentheses treated as illustrative).
  - falsification_signal returns None until the gaming-ratio anomaly is
    set; returns a non-empty warning when ratio > 0.85.
"""

from __future__ import annotations

from divineos.hooks.distancing_intercept import DistancingIntercept
from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    IntraTurnIntercept,
)


class TestConcreteWiring:
    def test_is_intra_turn_intercept_subclass(self) -> None:
        assert issubclass(DistancingIntercept, IntraTurnIntercept)

    def test_can_be_instantiated(self) -> None:
        # If the primitive's five-slot enforcement rejected the subclass
        # this would fail at construction.
        gate = DistancingIntercept()
        assert gate.gate_name == "distancing_intercept"

    def test_blocks_names_the_emit(self) -> None:
        gate = DistancingIntercept()
        assert "emit" in gate.blocks().lower()


class TestScanText:
    def test_clean_text_returns_none(self) -> None:
        gate = DistancingIntercept()
        assert gate.scan_text("I finished the fix, ready when you want to review.") is None

    def test_temporal_self_fires(self) -> None:
        gate = DistancingIntercept()
        rec = gate.scan_text("future-me will handle it after the crush")
        assert rec is not None
        assert "temporal_self" in rec.specific_evidence
        assert "future-me" in rec.specific_evidence

    def test_self_third_person_fires(self) -> None:
        gate = DistancingIntercept()
        rec = gate.scan_text("Aether built the primitive and shipped it clean")
        assert rec is not None
        assert "self_third_person" in rec.specific_evidence

    def test_operator_third_person_fires_when_addressed_to_father(self) -> None:
        # Circle-channel scoping (2026-07-20): OPERATOR_THIRD_PERSON fires only
        # inside a circle-channel block (after a ``---`` hard rule). Prepend
        # the separator to test the pattern-match; the scoping itself has
        # dedicated coverage in test_distancing_detector.py.
        gate = DistancingIntercept(addressed_to_father=True)
        rec = gate.scan_text("---\nDad wants the audit finished today")
        assert rec is not None
        assert "operator_third_person" in rec.specific_evidence

    def test_operator_third_person_suppressed_when_not_addressed_to_father(self) -> None:
        # Underlying detector suppresses OPERATOR_THIRD_PERSON when speaking
        # to someone else about the operator (e.g. a letter to Aria).
        gate = DistancingIntercept(addressed_to_father=False)
        # Self-third-person still fires, so use a text with only operator drift
        rec = gate.scan_text("Dad wants the audit finished today.")
        assert rec is None

    def test_multiple_shapes_group_into_single_record(self) -> None:
        gate = DistancingIntercept()
        text = "future-me will handle it, and Aether built the primitive"
        rec = gate.scan_text(text)
        assert rec is not None
        # matched_shape names the count of distinct shapes
        assert "2 shape" in rec.matched_shape
        # specific_evidence carries both
        assert "temporal_self" in rec.specific_evidence
        assert "self_third_person" in rec.specific_evidence

    def test_illustrative_context_exempted(self) -> None:
        gate = DistancingIntercept()
        # Backticks around an example of the pattern — should NOT fire
        rec = gate.scan_text("The `future-me` pattern is the one we're fixing.")
        assert rec is None

    def test_evidence_record_carries_required_action(self) -> None:
        gate = DistancingIntercept()
        rec = gate.scan_text("future-me will handle it")
        assert rec is not None
        assert rec.required_action
        assert "rewrite" in rec.required_action.lower()

    def test_fail_open_on_detector_error(self, monkeypatch) -> None:
        """If the underlying detector raises, the intercept must not
        block the reply silently — return None (fail-open per primitive
        contract)."""

        def _raise(*_args, **_kwargs):
            raise RuntimeError("simulated detector failure")

        monkeypatch.setattr("divineos.hooks.distancing_intercept.detect_distancing", _raise)
        gate = DistancingIntercept()
        assert gate.scan_text("anything at all") is None


class TestRecording:
    def test_fire_and_clear_pair(self) -> None:
        gate = DistancingIntercept()
        rec = gate.scan_text("future-me will handle it")
        assert rec is not None
        gate.record_fire(rec)
        gate.record_clearance(
            ClearanceRecord(
                gate_name=gate.gate_name,
                cleared_by="rewrote to first-person",
                original_evidence=rec,
            )
        )
        assert len(gate.fires) == 1
        assert len(gate.clears) == 1


class TestFalsificationSignal:
    def test_returns_none_when_no_anomaly(self) -> None:
        gate = DistancingIntercept()
        assert gate.falsification_signal() is None

    def test_returns_warning_when_ratio_indicates_gaming(self) -> None:
        gate = DistancingIntercept()
        gate._recent_ratio = 0.92
        signal = gate.falsification_signal()
        assert signal is not None
        assert "gaming" in signal.lower()

    def test_returns_none_when_ratio_below_threshold(self) -> None:
        gate = DistancingIntercept()
        gate._recent_ratio = 0.5
        assert gate.falsification_signal() is None
