"""Tests for the EvidenceBearingStopGate primitive.

Falsifiability:
  - Instantiating the abstract base directly must fail (ABC enforcement).
  - Both variants (IntraTurnIntercept, CrossTurnScan) refuse instantiation
    without implementing all five slots.
  - A concrete IntraTurnIntercept produces an EvidenceRecord when its
    scan_text matches, None when it doesn't.
  - A concrete CrossTurnScan produces an EvidenceRecord when its scan()
    hits its threshold, and requires BOTH accumulated_state and
    just_emitted_text (Aria's refinement — a fresh in-turn signal must
    reach the scanner even if the ledger hasn't caught up yet).
  - EvidenceRecord and ClearanceRecord are frozen dataclasses (can't be
    mutated after write — audit integrity).
  - falsification_signal returns None when the gate is behaving as-designed
    and a non-empty string when the fire/clear pattern is anomalous.
"""

from __future__ import annotations

from typing import Any

import pytest

from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    CrossTurnScan,
    EvidenceBearingStopGate,
    EvidenceRecord,
    IntraTurnIntercept,
)


# ---------------------------------------------------------------------------
# Test doubles


class _StubIntraTurn(IntraTurnIntercept):
    """Minimal concrete IntraTurnIntercept for testing the shape."""

    def __init__(self, gate_name: str = "stub-intra", trigger_token: str = "trigger") -> None:
        self.gate_name = gate_name
        self._trigger_token = trigger_token
        self.fires: list[EvidenceRecord] = []
        self.clears: list[ClearanceRecord] = []
        self._falsification: str | None = None

    def blocks(self) -> str:
        return "emit of this reply"

    def scan_text(self, assistant_text: str) -> EvidenceRecord | None:
        if self._trigger_token in assistant_text:
            return EvidenceRecord(
                gate_name=self.gate_name,
                matched_shape=f"contains {self._trigger_token!r}",
                specific_evidence=f"found {self._trigger_token!r} in text",
                required_action=f"rewrite to remove {self._trigger_token!r}",
            )
        return None

    def record_fire(self, evidence: EvidenceRecord) -> None:
        self.fires.append(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)

    def falsification_signal(self) -> str | None:
        return self._falsification


class _StubCrossTurn(CrossTurnScan):
    """Minimal concrete CrossTurnScan for testing the shape."""

    def __init__(
        self, gate_name: str = "stub-cross", state_key: str = "count", threshold: int = 10
    ) -> None:
        self.gate_name = gate_name
        self._state_key = state_key
        self._threshold = threshold
        self.fires: list[EvidenceRecord] = []
        self.clears: list[ClearanceRecord] = []
        self._falsification: str | None = None

    def blocks(self) -> str:
        return "next non-consult tool call"

    def scan(
        self,
        accumulated_state: dict[str, Any],
        just_emitted_text: str,
    ) -> EvidenceRecord | None:
        # Aria's refinement: signal can come from EITHER state OR text.
        state_hit = accumulated_state.get(self._state_key, 0) >= self._threshold
        text_hit = "fresh-in-turn-signal" in just_emitted_text
        if state_hit or text_hit:
            source = "state" if state_hit else "text"
            return EvidenceRecord(
                gate_name=self.gate_name,
                matched_shape=f"threshold exceeded ({source})",
                specific_evidence=f"source={source}, state={accumulated_state}, text_hit={text_hit}",
                required_action="run investigation-shape action",
            )
        return None

    def record_fire(self, evidence: EvidenceRecord) -> None:
        self.fires.append(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)

    def falsification_signal(self) -> str | None:
        return self._falsification


# ---------------------------------------------------------------------------
# Abstract-class enforcement


class TestAbstractShape:
    def test_base_class_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            EvidenceBearingStopGate()  # type: ignore[abstract]

    def test_intra_turn_variant_cannot_be_instantiated_without_scan_text(self) -> None:
        class _MissingScanText(IntraTurnIntercept):
            def blocks(self) -> str:
                return "x"

            def record_fire(self, evidence: EvidenceRecord) -> None:
                pass

            def record_clearance(self, clearance: ClearanceRecord) -> None:
                pass

            def falsification_signal(self) -> str | None:
                return None

        with pytest.raises(TypeError):
            _MissingScanText()  # type: ignore[abstract]

    def test_cross_turn_variant_cannot_be_instantiated_without_scan(self) -> None:
        class _MissingScan(CrossTurnScan):
            def blocks(self) -> str:
                return "x"

            def record_fire(self, evidence: EvidenceRecord) -> None:
                pass

            def record_clearance(self, clearance: ClearanceRecord) -> None:
                pass

            def falsification_signal(self) -> str | None:
                return None

        with pytest.raises(TypeError):
            _MissingScan()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Dataclass integrity (audit-trail requirement)


class TestRecordImmutability:
    def test_evidence_record_is_frozen(self) -> None:
        rec = EvidenceRecord(
            gate_name="g", matched_shape="s", specific_evidence="e", required_action="a"
        )
        with pytest.raises(Exception):  # FrozenInstanceError subclasses AttributeError
            rec.gate_name = "different"  # type: ignore[misc]

    def test_clearance_record_is_frozen(self) -> None:
        ev = EvidenceRecord(
            gate_name="g", matched_shape="s", specific_evidence="e", required_action="a"
        )
        cl = ClearanceRecord(gate_name="g", cleared_by="action", original_evidence=ev)
        with pytest.raises(Exception):
            cl.cleared_by = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IntraTurnIntercept behavior


class TestIntraTurnScan:
    def test_returns_none_when_pattern_absent(self) -> None:
        gate = _StubIntraTurn(trigger_token="future-me")
        assert gate.scan_text("I finished the work") is None

    def test_returns_evidence_when_pattern_present(self) -> None:
        gate = _StubIntraTurn(trigger_token="future-me")
        rec = gate.scan_text("future-me will handle it")
        assert rec is not None
        assert rec.gate_name == "stub-intra"
        assert "future-me" in rec.specific_evidence
        assert rec.required_action  # required_action non-empty

    def test_evidence_record_carries_required_action(self) -> None:
        """KEY slot must be populated — a gate without a required_action
        is a jailer (has LOCK, missing KEY)."""
        gate = _StubIntraTurn(trigger_token="x")
        rec = gate.scan_text("x")
        assert rec is not None
        assert rec.required_action != ""

    def test_record_fire_and_clearance_pair(self) -> None:
        gate = _StubIntraTurn(trigger_token="x")
        rec = gate.scan_text("x")
        assert rec is not None
        gate.record_fire(rec)
        gate.record_clearance(
            ClearanceRecord(gate_name=gate.gate_name, cleared_by="rewrote", original_evidence=rec)
        )
        assert len(gate.fires) == 1
        assert len(gate.clears) == 1
        assert gate.clears[0].original_evidence == rec


# ---------------------------------------------------------------------------
# CrossTurnScan behavior — Aria's refinement (state OR text)


class TestCrossTurnScan:
    def test_scan_fires_on_state_threshold(self) -> None:
        gate = _StubCrossTurn(state_key="count", threshold=10)
        rec = gate.scan(accumulated_state={"count": 15}, just_emitted_text="")
        assert rec is not None
        assert "state" in rec.matched_shape

    def test_scan_fires_on_just_emitted_text_even_when_state_below_threshold(self) -> None:
        """Aria's catch: fresh-in-turn signal must reach the scanner
        even if ledger hasn't caught up yet. Missing this = commitments
        made in the just-completed turn get missed until next turn."""
        gate = _StubCrossTurn(state_key="count", threshold=10)
        rec = gate.scan(
            accumulated_state={"count": 0},
            just_emitted_text="here is a fresh-in-turn-signal that just landed",
        )
        assert rec is not None
        assert "text" in rec.matched_shape

    def test_scan_returns_none_when_neither_input_matches(self) -> None:
        gate = _StubCrossTurn(state_key="count", threshold=10)
        assert gate.scan(accumulated_state={"count": 0}, just_emitted_text="normal reply") is None

    def test_scan_signature_requires_both_inputs(self) -> None:
        """The interface must have both accumulated_state AND
        just_emitted_text — Aria's #4 sketch requires both."""
        import inspect

        sig = inspect.signature(CrossTurnScan.scan)
        params = list(sig.parameters.keys())
        assert "accumulated_state" in params
        assert "just_emitted_text" in params


# ---------------------------------------------------------------------------
# FALSIFIER slot — recurrence-check baked in


class TestFalsificationSignal:
    def test_returns_none_when_gate_behaves_as_designed(self) -> None:
        gate = _StubIntraTurn()
        assert gate.falsification_signal() is None

    def test_returns_string_when_anomaly_present(self) -> None:
        gate = _StubIntraTurn()
        gate._falsification = "clearance-to-fire ratio 1:1 — likely gaming"
        signal = gate.falsification_signal()
        assert signal is not None
        assert "gaming" in signal
