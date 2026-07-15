"""Ledger helper for EvidenceBearingStopGate fire/clear events.

Aletheia audit finding 2026-07-15 (aletheia-to-aether primitive audit):

    "0.85 is a seed. Right now it's lying on bare rock. Give it soil.
     Don't hardcode the threshold. RECORD every fire and every clear,
     and derive the signal from the actual distribution as it accumulates.
     A number that can't move with evidence is ammunition, not information."

This module IS the soil. Concrete gates that inherit from IntraTurnIntercept
or CrossTurnScan call these helpers on fire/clear; the primitive's
``falsification_signal()`` can then read the accumulated distribution
instead of comparing against a hardcoded threshold.

Two event types (both go through ``divineos.core.ledger.log_event`` so
the chain-hash integrity extends to gate events):

- ``GATE_FIRE`` — a gate detected its firing condition and produced an
  EvidenceRecord. Payload includes gate_name, matched_shape,
  specific_evidence, and required_action.
- ``GATE_CLEARANCE`` — a gate was cleared. Payload includes gate_name,
  cleared_by, and the original evidence bundle.

``compute_falsification_ratio()`` reads recent events for a gate and
computes clearance-count / fire-count over a window. That's what the
concrete gate's ``falsification_signal()`` compares against — no
hardcoded thresholds after the primitive has data.

Actor for these events is ``"evidence-bearing-stop-gate"`` so audit
queries can slice by the primitive as a whole vs any single concrete
gate.
"""

from __future__ import annotations

import time
from typing import Any

from divineos.core.ledger import get_events, log_event
from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    EvidenceRecord,
)


GATE_FIRE_EVENT = "GATE_FIRE"
GATE_CLEARANCE_EVENT = "GATE_CLEARANCE"
GATE_ACTOR = "evidence-bearing-stop-gate"


def record_gate_fire(evidence: EvidenceRecord) -> str:
    """Write a GATE_FIRE event to the ledger. Returns the event id.

    Called from concrete gate ``record_fire`` implementations. Failing
    silently (logging errors but not raising) is deliberate — a ledger
    write failure must not prevent the gate from blocking the action;
    the gate's primary job is enforcement, telemetry is secondary.
    """
    try:
        return log_event(
            event_type=GATE_FIRE_EVENT,
            actor=GATE_ACTOR,
            payload={
                "gate_name": evidence.gate_name,
                "matched_shape": evidence.matched_shape,
                "specific_evidence": evidence.specific_evidence,
                "required_action": evidence.required_action,
            },
        )
    except Exception:  # noqa: BLE001 — telemetry failure must not block enforcement
        return ""


def record_gate_clearance(clearance: ClearanceRecord) -> str:
    """Write a GATE_CLEARANCE event to the ledger. Returns event id.

    Same fail-open contract as record_gate_fire.
    """
    try:
        return log_event(
            event_type=GATE_CLEARANCE_EVENT,
            actor=GATE_ACTOR,
            payload={
                "gate_name": clearance.gate_name,
                "cleared_by": clearance.cleared_by,
                "original_evidence": {
                    "gate_name": clearance.original_evidence.gate_name,
                    "matched_shape": clearance.original_evidence.matched_shape,
                    "specific_evidence": clearance.original_evidence.specific_evidence,
                    "required_action": clearance.original_evidence.required_action,
                },
            },
        )
    except Exception:  # noqa: BLE001
        return ""


def compute_falsification_ratio(
    gate_name: str,
    window_seconds: float = 7 * 24 * 3600,  # 7 days default
    minimum_fires: int = 10,
) -> float | None:
    """Compute clearance-count / fire-count for ``gate_name`` over the
    recent window.

    Returns:
        ``None`` if fewer than ``minimum_fires`` events in the window
        (not enough data to compute a reliable ratio — a gate that has
        fired 2 times and cleared 2 times shouldn't trip a gaming alarm).

        Otherwise the ratio: clearances-to-fires. A ratio close to 1.0
        means clearances are nearly matching fires — the gate is being
        cleared as fast as it fires. Whether that's gaming or normal
        depends on the gate's design; the concrete gate's
        ``falsification_signal()`` interprets what "too high" means.

    Reads via ``divineos.core.ledger.get_events`` with a filter on
    event_type so this scales as the ledger grows. Fails-open on read
    errors by returning None (no calibration → no alarm — safer than
    a false one).
    """
    cutoff = time.time() - window_seconds
    try:
        fire_events = _events_since(GATE_FIRE_EVENT, gate_name, cutoff)
        clearance_events = _events_since(GATE_CLEARANCE_EVENT, gate_name, cutoff)
    except Exception:  # noqa: BLE001
        return None

    fire_count = len(fire_events)
    if fire_count < minimum_fires:
        return None
    clearance_count = len(clearance_events)
    return clearance_count / fire_count


def _events_since(event_type: str, gate_name: str, cutoff_ts: float) -> list[dict[str, Any]]:
    """Fetch events of ``event_type`` with matching ``gate_name`` in payload
    since ``cutoff_ts``. Uses ``get_events`` with a wider fetch (desc order,
    newest first) then filters in-Python since the ledger's SQL layer
    doesn't index JSON payload keys. Acceptable at expected gate-event
    rates (dozens per day, not thousands)."""
    from datetime import datetime

    events = get_events(event_type=event_type, limit=2000, order="desc")
    matched: list[dict[str, Any]] = []
    for e in events:
        ts_str = e.get("timestamp") or ""
        try:
            ts_epoch = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
        except (ValueError, AttributeError):
            continue
        if ts_epoch < cutoff_ts:
            # desc order — everything after this is older, stop scanning
            break
        payload = e.get("payload") or {}
        if payload.get("gate_name") == gate_name:
            matched.append(e)
    return matched


__all__ = [
    "GATE_ACTOR",
    "GATE_CLEARANCE_EVENT",
    "GATE_FIRE_EVENT",
    "compute_falsification_ratio",
    "record_gate_clearance",
    "record_gate_fire",
]
