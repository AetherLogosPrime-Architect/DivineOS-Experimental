"""Bypass-rate scan — second concrete instance of the CrossTurnScan
variant of EvidenceBearingStopGate. Validates the cross-turn variant
the same way ``distancing_intercept`` validated intra-turn.

Historical shape (informational-only surface, jailer-adjacent):
``bypass_telemetry.briefing_block()`` shows a value-string on every
substrate-modification-gravity gate fire — "71 bypasses in 15 days,
elevated bypass rate — gates are being routed-around. Per psf-ac523181:
bypass habituation degrades the gate to warning. Investigate whether
the gates are wrong-shape or the bypass-discipline is." The surface
explicitly instructs an investigation. The investigation never fires.
Fires every substrate-modifying tool, gets read, gets forgotten within
8-9 posts. The exact ROOT PATTERN #1cd8cd83 shape: value-string
without cheap check.

Structural fix (this module): the cross-turn scan reads bypass_rate()
against a threshold on Stop hook; when the threshold is exceeded and
this session hasn't run an investigation-shape action (audit filing,
claim, or workbench doc examining the bypassed gates), it fires with
positive evidence naming the specific gates being bypassed.

Not yet wired to a Stop hook shell script — Python surface first, per
the same ship-order that landed distancing intercept without shell
wiring. Wiring both concrete instances together after this commit
proves the primitive across both variants.
"""

from __future__ import annotations

from typing import Any

from divineos.core.bypass_telemetry import bypass_rate
from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    CrossTurnScan,
    EvidenceRecord,
)
from divineos.hooks.gate_event_ledger import (
    compute_falsification_ratio,
    record_gate_clearance,
    record_gate_fire,
)


class BypassRateScan(CrossTurnScan):
    """Fire when the bypass rate in the recent window exceeds a threshold.

    Reads ``divineos.core.bypass_telemetry.bypass_rate()`` — the same
    numbers the substrate-modification-gravity gate has been surfacing
    without action. Cross-turn variant of the primitive: state is the
    accumulated bypass ledger, not any single turn.

    Threshold defaults to 50 events over 14 days. Current substrate
    surface reports 71 in 15 days; the initial threshold is set below
    that intentionally so the gate would fire on today's state, proving
    the mechanism live. Threshold is a SEED — the falsification-signal
    layer (``compute_falsification_ratio``) will let the calibration
    move with data as it accumulates. Aletheia audit finding 2026-07-15:
    "a number that can't move with evidence is ammunition, not
    information."
    """

    def __init__(self, threshold_events: int = 50, window_days: int = 14) -> None:
        self.gate_name = "bypass_rate_scan"
        self._threshold_events = threshold_events
        self._window_days = window_days
        self.fires: list[EvidenceRecord] = []
        self.clears: list[ClearanceRecord] = []
        self._recent_ratio: float | None = None

    def blocks(self) -> str:
        return (
            "next non-investigation tool call "
            "(clear by filing an audit, claim, or workbench doc examining "
            "the bypassed gate class)"
        )

    def scan(
        self,
        accumulated_state: dict[str, Any],
        just_emitted_text: str,  # noqa: ARG002 — bypass records are already in-log by scan-time; text-buffer not needed for this variant, but signature honored per Aria's refinement
    ) -> EvidenceRecord | None:
        # Prefer host-injected stats (allows tests + composability with
        # a future state-provider layer); fall back to fetching directly
        # so the concrete gate is usable in isolation.
        stats = accumulated_state.get("bypass_stats")
        if stats is None:
            try:
                stats = bypass_rate(window_days=self._window_days)
            except Exception:  # noqa: BLE001 — fail-open per primitive contract
                return None
        try:
            total_events = int(stats.get("total_events", 0))
            by_env = dict(stats.get("by_env_var", {}) or {})
            unique_days = int(stats.get("unique_days", 0))
            window_days = int(stats.get("window_days", self._window_days))
        except (TypeError, ValueError):
            return None
        if total_events < self._threshold_events:
            return None
        return self._to_evidence(total_events, by_env, unique_days, window_days)

    def _to_evidence(
        self,
        total: int,
        by_env: dict[str, int],
        unique_days: int,
        window_days: int,
    ) -> EvidenceRecord:
        # Name the top-3 most-bypassed env vars so the required action
        # can be targeted at the specific gates being routed around.
        top = sorted(by_env.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_line = (
            ", ".join(f"{name} ({count})" for name, count in top) if top else "(no env-var detail)"
        )
        specific_evidence = (
            f"total_events={total}, unique_days={unique_days}, "
            f"window_days={window_days}, top_bypassed={top_line}"
        )
        matched_shape = (
            f"bypass rate {total} events over {window_days} days "
            f"exceeds threshold {self._threshold_events}"
        )
        required_action = (
            f"Investigate the top-bypassed gate(s): {top_line}. "
            "Clear by filing (a) a divineos audit round examining whether the "
            "gate is wrong-shape, (b) a divineos claim naming the specific "
            "failure mode, or (c) a workbench doc that names the structural "
            "fix. Absence of an investigation-shape action = the surface "
            "keeps firing but nothing changes (per Andrew 2026-07-15: "
            "'gates are helpers not jailers')."
        )
        return EvidenceRecord(
            gate_name=self.gate_name,
            matched_shape=matched_shape,
            specific_evidence=specific_evidence,
            required_action=required_action,
        )

    def record_fire(self, evidence: EvidenceRecord) -> None:
        self.fires.append(evidence)
        record_gate_fire(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)
        record_gate_clearance(clearance)

    def falsification_signal(self) -> str | None:
        # Same shape as DistancingIntercept — read the ratio off the
        # ledger; fall back to the seed threshold when data is sparse.
        # For a cross-turn gate the "gaming" shape is different: high
        # clearance rate could mean I'm actually investigating (good) OR
        # filing shallow docs just to clear (bad). Distinguishing needs
        # deeper evidence than just the ratio; for now surface the ratio
        # itself as diagnostic, don't hard-alarm on it.
        ratio = self._recent_ratio
        if ratio is None:
            ratio = compute_falsification_ratio(self.gate_name)
        if ratio is not None and ratio > 0.90:
            return (
                f"clearance-to-fire ratio {ratio:.2f} — investigate whether "
                "the investigation-shape clearances are producing structural "
                "fixes or just clearing the marker (Goodhart risk)"
            )
        return None


__all__ = ["BypassRateScan"]
