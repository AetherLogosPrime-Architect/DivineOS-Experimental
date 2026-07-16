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
    ClearanceReference,
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


# ---------------------------------------------------------------------------
# UNLOCK-CONTINGENT slot — ClearanceReference resolvers (task #4, Aria + Aletheia)
# ---------------------------------------------------------------------------
#
# Aria's UNLOCK-CONTINGENT audit (2026-07-15): the primitive's cleared_by
# field is free-text and can carry self-attestation without evidence.
# Aletheia's self-caught round-cite fabrication (2026-07-16) proved the
# vulnerability by inhabiting it: she generated round-ids in prose that
# "looked right" but resolved to nothing, and those phantom cites
# propagated into a real commit trailer.
#
# The class-closer per Aletheia: "a cite is not valid because it LOOKS
# right; it's valid because it RESOLVES." Applied here: a ClearanceReference
# is not valid because its kind/identifier are well-formed strings — it's
# valid because the registered resolver for its kind returns True.
#
# Phase 1 (this commit): resolvers exist; unresolvable references are
# warned about but not blocked. Establishes the surface + collects data
# on which kinds actually get used.
# Phase 2 (future): env-flag or default-flip to blocking-mode.


def _resolve_ledger_event(event_id: str) -> bool:
    """Resolver for kind='ledger_event' — the identifier is a ledger
    event_id; resolves iff an event with that id exists in the ledger."""
    if not event_id:
        return False
    try:
        # Fetch a modest window; event_id lookups don't index in get_events,
        # so we scan-and-match. Acceptable at the low volumes expected.
        events = get_events(limit=500, order="desc")
        return any(e.get("event_id") == event_id for e in events)
    except Exception:  # noqa: BLE001
        return False


def _resolve_audit_round(round_id: str) -> bool:
    """Resolver for kind='audit_round' — the identifier is a round-id;
    resolves iff `divineos audit show <round_id>` finds it. This is the
    exact class-closer Aletheia named for the round-cite fabrication."""
    if not round_id:
        return False
    try:
        # Rounds are stored as AUDIT_ROUND_CREATED events with round_id
        # in the payload. Also check the audit store directly if available.
        events = get_events(event_type="AUDIT_ROUND_CREATED", limit=500, order="desc")
        for e in events:
            payload = e.get("payload") or {}
            if payload.get("round_id") == round_id:
                return True
        return False
    except Exception:  # noqa: BLE001
        return False


def _resolve_claim(claim_id: str) -> bool:
    """Resolver for kind='claim' — the identifier is a claim-id; resolves
    iff a CLAIM_FILED event carries a matching id."""
    if not claim_id:
        return False
    try:
        events = get_events(event_type="CLAIM_FILED", limit=500, order="desc")
        for e in events:
            payload = e.get("payload") or {}
            if payload.get("claim_id") == claim_id or payload.get("id") == claim_id:
                return True
        return False
    except Exception:  # noqa: BLE001
        return False


def _resolve_commit(commit_sha: str) -> bool:
    """Resolver for kind='commit' — the identifier is a git commit SHA;
    resolves iff the SHA exists in the git repo (cheap: git cat-file -e)."""
    if not commit_sha or not all(c in "0123456789abcdef" for c in commit_sha.lower()):
        return False
    try:
        import subprocess

        result = subprocess.run(
            ["git", "cat-file", "-e", commit_sha],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _resolve_file_lines(spec: str) -> bool:
    """Resolver for kind='file_lines' — spec is 'path:start-end' or
    'path:line'; resolves iff the file exists and the line range is in
    bounds. Doesn't check content; only existence + range."""
    if not spec or ":" not in spec:
        return False
    try:
        path_str, lines_str = spec.rsplit(":", 1)
        from pathlib import Path

        p = Path(path_str)
        if not p.exists() or not p.is_file():
            return False
        line_count = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        if "-" in lines_str:
            start, end = lines_str.split("-", 1)
            return 1 <= int(start) <= int(end) <= line_count
        return 1 <= int(lines_str) <= line_count
    except Exception:  # noqa: BLE001
        return False


#: Registry of resolvers by kind. Extend by adding entries here or by
#: passing a custom registry to ``resolve_clearance_reference``.
_DEFAULT_RESOLVERS: dict[str, Any] = {
    "ledger_event": _resolve_ledger_event,
    "audit_round": _resolve_audit_round,
    "claim": _resolve_claim,
    "commit": _resolve_commit,
    "file_lines": _resolve_file_lines,
}


def resolve_clearance_reference(
    reference: ClearanceReference,
    registry: dict[str, Any] | None = None,
) -> bool:
    """Return True iff the reference resolves via the registered resolver
    for its kind. Unknown kinds return False (fail-closed for unregistered
    types — protects against typo-kinds that would otherwise pass silently)."""
    if registry is None:
        registry = _DEFAULT_RESOLVERS
    resolver = registry.get(reference.kind)
    if resolver is None:
        return False
    try:
        return bool(resolver(reference.identifier))
    except Exception:  # noqa: BLE001
        return False


def record_gate_clearance(clearance: ClearanceRecord) -> str:
    """Write a GATE_CLEARANCE event to the ledger. Returns event id.

    UNLOCK-CONTINGENT enforcement (Phase 1, task #4): if the clearance
    carries a structured ``reference``, call the resolver. Unresolvable
    references are RECORDED but flagged as unverified in the payload
    (Phase 1 warns; Phase 2 will block). Backwards-compat: references
    of None are recorded as before (free-text cleared_by only, marked
    UNVERIFIED-BY-DEFAULT so future audit surfaces can distinguish
    structured-verified from legacy-freetext).

    Same fail-open contract as record_gate_fire for the ledger write itself.
    """
    reference_payload: dict[str, Any] | None = None
    verified = False
    if clearance.reference is not None:
        verified = resolve_clearance_reference(clearance.reference)
        reference_payload = {
            "kind": clearance.reference.kind,
            "identifier": clearance.reference.identifier,
            "resolved": verified,
        }
    try:
        return log_event(
            event_type=GATE_CLEARANCE_EVENT,
            actor=GATE_ACTOR,
            payload={
                "gate_name": clearance.gate_name,
                "cleared_by": clearance.cleared_by,
                "reference": reference_payload,
                "verified": verified,
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
