"""Tests for gate_event_ledger — the soil for the 0.85 seed.

Aletheia's frame (2026-07-15 audit): 'Don't hardcode the threshold.
RECORD every fire and every clear, and derive the signal from the
actual distribution as it accumulates.' These tests confirm the
recording and derivation shape.

Falsifiability:
  - record_gate_fire writes a GATE_FIRE event with the evidence payload.
  - record_gate_clearance writes a GATE_CLEARANCE event with the
    clearance + original evidence bundle.
  - Failures in the ledger layer are swallowed (fail-open per the
    telemetry-must-not-block-enforcement contract).
  - compute_falsification_ratio returns None when fire count is below
    the minimum-fires threshold (not enough data to trust).
  - Returns clearances / fires when enough data exists.
  - Filters by gate_name so multiple gates using the ledger don't
    contaminate each other's ratios.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    EvidenceRecord,
)
from divineos.hooks.gate_event_ledger import (
    GATE_ACTOR,
    GATE_CLEARANCE_EVENT,
    GATE_FIRE_EVENT,
    compute_falsification_ratio,
    record_gate_clearance,
    record_gate_fire,
)


def _make_evidence(gate_name: str = "test_gate") -> EvidenceRecord:
    return EvidenceRecord(
        gate_name=gate_name,
        matched_shape="test shape",
        specific_evidence="test evidence",
        required_action="test action",
    )


def _make_clearance(gate_name: str = "test_gate") -> ClearanceRecord:
    return ClearanceRecord(
        gate_name=gate_name,
        cleared_by="test clearance",
        original_evidence=_make_evidence(gate_name),
    )


class TestRecording:
    def test_record_gate_fire_calls_log_event_with_fire_type(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.log_event") as mock_log:
            mock_log.return_value = "evt_123"
            result = record_gate_fire(_make_evidence())
        assert result == "evt_123"
        _, kwargs = mock_log.call_args
        assert kwargs["event_type"] == GATE_FIRE_EVENT
        assert kwargs["actor"] == GATE_ACTOR
        assert kwargs["payload"]["gate_name"] == "test_gate"
        assert kwargs["payload"]["matched_shape"] == "test shape"

    def test_record_gate_clearance_calls_log_event_with_clearance_type(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.log_event") as mock_log:
            mock_log.return_value = "evt_456"
            result = record_gate_clearance(_make_clearance())
        assert result == "evt_456"
        _, kwargs = mock_log.call_args
        assert kwargs["event_type"] == GATE_CLEARANCE_EVENT
        assert kwargs["payload"]["cleared_by"] == "test clearance"
        assert kwargs["payload"]["original_evidence"]["gate_name"] == "test_gate"

    def test_record_gate_fire_swallows_log_event_failure(self) -> None:
        """Fail-open: telemetry failure must not propagate."""
        with patch("divineos.hooks.gate_event_ledger.log_event") as mock_log:
            mock_log.side_effect = RuntimeError("simulated ledger failure")
            result = record_gate_fire(_make_evidence())
        assert result == ""

    def test_record_gate_clearance_swallows_log_event_failure(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.log_event") as mock_log:
            mock_log.side_effect = RuntimeError("simulated ledger failure")
            result = record_gate_clearance(_make_clearance())
        assert result == ""


class TestFalsificationRatio:
    def _mock_events(
        self,
        event_type: str,
        count: int,
        gate_name: str,
        age_seconds: float = 60,
    ) -> list[dict[str, Any]]:
        from datetime import datetime, timezone

        ts_iso = datetime.fromtimestamp(time.time() - age_seconds, tz=timezone.utc).isoformat()
        return [
            {
                "event_id": f"evt_{i}",
                "timestamp": ts_iso,
                "event_type": event_type,
                "actor": GATE_ACTOR,
                "payload": {"gate_name": gate_name},
                "content_hash": "abc",
            }
            for i in range(count)
        ]

    def test_returns_none_when_below_minimum_fires(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.get_events") as mock_get:
            mock_get.return_value = self._mock_events(GATE_FIRE_EVENT, 3, "g")
            ratio = compute_falsification_ratio("g", minimum_fires=10)
        assert ratio is None

    def test_returns_ratio_when_enough_data(self) -> None:
        def _side_effect(**kwargs: Any) -> list[dict[str, Any]]:
            et = kwargs.get("event_type")
            if et == GATE_FIRE_EVENT:
                return self._mock_events(GATE_FIRE_EVENT, 20, "g")
            if et == GATE_CLEARANCE_EVENT:
                return self._mock_events(GATE_CLEARANCE_EVENT, 15, "g")
            return []

        with patch("divineos.hooks.gate_event_ledger.get_events", side_effect=_side_effect):
            ratio = compute_falsification_ratio("g", minimum_fires=10)
        assert ratio == 0.75  # 15 / 20

    def test_filters_by_gate_name(self) -> None:
        """Two gates sharing the ledger must not contaminate each other's ratios."""

        def _side_effect(**kwargs: Any) -> list[dict[str, Any]]:
            et = kwargs.get("event_type")
            if et == GATE_FIRE_EVENT:
                return self._mock_events(GATE_FIRE_EVENT, 20, "a") + self._mock_events(
                    GATE_FIRE_EVENT, 5, "b"
                )
            if et == GATE_CLEARANCE_EVENT:
                return self._mock_events(GATE_CLEARANCE_EVENT, 4, "a") + self._mock_events(
                    GATE_CLEARANCE_EVENT, 5, "b"
                )
            return []

        with patch("divineos.hooks.gate_event_ledger.get_events", side_effect=_side_effect):
            ratio_a = compute_falsification_ratio("a", minimum_fires=10)
            ratio_b = compute_falsification_ratio("b", minimum_fires=3)
        assert ratio_a == 0.2  # 4 / 20 for gate a
        assert ratio_b == 1.0  # 5 / 5 for gate b

    def test_excludes_events_outside_window(self) -> None:
        """Events older than window_seconds should not count."""

        def _side_effect(**kwargs: Any) -> list[dict[str, Any]]:
            et = kwargs.get("event_type")
            if et == GATE_FIRE_EVENT:
                return self._mock_events(GATE_FIRE_EVENT, 100, "g", age_seconds=30 * 24 * 3600)
            return []

        with patch("divineos.hooks.gate_event_ledger.get_events", side_effect=_side_effect):
            ratio = compute_falsification_ratio("g", window_seconds=7 * 24 * 3600, minimum_fires=10)
        assert ratio is None  # 0 events in window → below minimum

    def test_returns_none_on_get_events_failure(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.get_events") as mock_get:
            mock_get.side_effect = RuntimeError("simulated ledger read failure")
            ratio = compute_falsification_ratio("g")
        assert ratio is None
