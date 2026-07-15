"""Tests for BypassRateScan — second concrete instance of
CrossTurnScan from the EvidenceBearingStopGate primitive.

Validates that the cross-turn variant lands as clean as the intra-turn
one did (distancing intercept). If both concrete instances hold, the
primitive's shape is proved across both variants and future concretes
(#3 jargon, #4 announcement-without-action, consult-ratio) can be
built cheaply.

Falsifiability:
  - Below-threshold bypass count → scan returns None.
  - At/above threshold → EvidenceRecord names total, unique days, and
    top-bypassed env vars in specific_evidence.
  - Host-injected accumulated_state takes precedence over live fetch
    (composability + testability).
  - When accumulated_state has no bypass_stats, scan fetches from
    bypass_rate() directly.
  - Fail-open on either state fetch error or malformed payload.
  - CrossTurnScan signature honored (accepts both accumulated_state
    AND just_emitted_text — Aria's refinement).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from divineos.hooks.bypass_rate_scan import BypassRateScan
from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    CrossTurnScan,
)


def _stats(
    total: int, by_env: dict[str, int] | None = None, unique_days: int = 10
) -> dict[str, Any]:
    return {
        "total_events": total,
        "by_env_var": by_env or {},
        "unique_days": unique_days,
        "window_days": 14,
    }


class TestConcreteWiring:
    def test_is_cross_turn_scan_subclass(self) -> None:
        assert issubclass(BypassRateScan, CrossTurnScan)

    def test_can_be_instantiated(self) -> None:
        gate = BypassRateScan()
        assert gate.gate_name == "bypass_rate_scan"

    def test_blocks_names_investigation_shape_clearance(self) -> None:
        gate = BypassRateScan()
        blocks_msg = gate.blocks()
        assert "audit" in blocks_msg or "claim" in blocks_msg or "workbench" in blocks_msg


class TestScan:
    def test_returns_none_below_threshold(self) -> None:
        gate = BypassRateScan(threshold_events=50)
        rec = gate.scan(accumulated_state={"bypass_stats": _stats(20)}, just_emitted_text="")
        assert rec is None

    def test_fires_at_or_above_threshold(self) -> None:
        gate = BypassRateScan(threshold_events=50)
        stats = _stats(71, by_env={"cmd:divineos goal": 14, "cmd:divineos ask": 14})
        rec = gate.scan(accumulated_state={"bypass_stats": stats}, just_emitted_text="")
        assert rec is not None
        assert "71" in rec.specific_evidence
        assert "cmd:divineos goal" in rec.specific_evidence

    def test_names_top_three_bypassed_env_vars(self) -> None:
        gate = BypassRateScan(threshold_events=10)
        by_env = {"a": 14, "b": 13, "c": 12, "d": 5, "e": 3}
        rec = gate.scan(
            accumulated_state={"bypass_stats": _stats(47, by_env=by_env)}, just_emitted_text=""
        )
        assert rec is not None
        # Top three
        assert "a" in rec.specific_evidence
        assert "b" in rec.specific_evidence
        assert "c" in rec.specific_evidence
        # Not the fourth or fifth
        assert "'d'" not in rec.specific_evidence
        assert "'e'" not in rec.specific_evidence

    def test_evidence_record_carries_required_action(self) -> None:
        gate = BypassRateScan(threshold_events=10)
        rec = gate.scan(accumulated_state={"bypass_stats": _stats(20)}, just_emitted_text="")
        assert rec is not None
        assert rec.required_action
        assert (
            "audit" in rec.required_action.lower() or "investigate" in rec.required_action.lower()
        )


class TestStateSource:
    def test_host_injected_state_takes_precedence(self) -> None:
        """When accumulated_state carries bypass_stats, use them instead
        of fetching. Enables tests + a future state-provider layer."""
        gate = BypassRateScan(threshold_events=50)
        # bypass_rate() would return real live data, but injected stats
        # should be honored regardless. Patch it to raise so we prove
        # the code path never falls back:
        with patch("divineos.hooks.bypass_rate_scan.bypass_rate") as mock_rate:
            mock_rate.side_effect = RuntimeError("should not be called")
            rec = gate.scan(
                accumulated_state={"bypass_stats": _stats(100)},
                just_emitted_text="",
            )
        assert rec is not None
        assert "100" in rec.specific_evidence

    def test_falls_back_to_live_fetch_when_state_missing(self) -> None:
        gate = BypassRateScan(threshold_events=50)
        with patch("divineos.hooks.bypass_rate_scan.bypass_rate") as mock_rate:
            mock_rate.return_value = _stats(80)
            rec = gate.scan(accumulated_state={}, just_emitted_text="")
        assert rec is not None
        assert "80" in rec.specific_evidence

    def test_fail_open_on_fetch_error(self) -> None:
        gate = BypassRateScan(threshold_events=50)
        with patch("divineos.hooks.bypass_rate_scan.bypass_rate") as mock_rate:
            mock_rate.side_effect = RuntimeError("simulated fetch failure")
            rec = gate.scan(accumulated_state={}, just_emitted_text="")
        assert rec is None

    def test_fail_open_on_malformed_payload(self) -> None:
        gate = BypassRateScan(threshold_events=50)
        rec = gate.scan(
            accumulated_state={"bypass_stats": {"total_events": "not-a-number"}},
            just_emitted_text="",
        )
        assert rec is None


class TestRecording:
    def test_fire_and_clear_pair(self) -> None:
        gate = BypassRateScan(threshold_events=10)
        rec = gate.scan(accumulated_state={"bypass_stats": _stats(50)}, just_emitted_text="")
        assert rec is not None
        gate.record_fire(rec)
        gate.record_clearance(
            ClearanceRecord(
                gate_name=gate.gate_name,
                cleared_by="filed workbench audit doc",
                original_evidence=rec,
            )
        )
        assert len(gate.fires) == 1
        assert len(gate.clears) == 1


class TestFalsificationSignal:
    def test_returns_none_when_no_anomaly(self) -> None:
        gate = BypassRateScan()
        assert gate.falsification_signal() is None

    def test_returns_warning_when_ratio_indicates_gaming(self) -> None:
        gate = BypassRateScan()
        gate._recent_ratio = 0.95
        signal = gate.falsification_signal()
        assert signal is not None
        assert (
            "goodhart" in signal.lower()
            or "shallow" in signal.lower()
            or "clearing the marker" in signal.lower()
        )

    def test_returns_none_when_ratio_below_threshold(self) -> None:
        gate = BypassRateScan()
        gate._recent_ratio = 0.6
        assert gate.falsification_signal() is None
