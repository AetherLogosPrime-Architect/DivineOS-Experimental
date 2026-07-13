"""Substrate-ledger interaction for council_record events.

All persistence rides on the existing event-ledger (append-only,
hash-chained). No new tables; each council artifact is a typed event:

- ``COUNCIL_RECORD_LOGGED`` — a passing council walk
- ``COUNCIL_RECORD_CONSUMED`` — record was used to clear a specific edit
- ``COUNCIL_WALK_REJECTED`` — substance-binding failed at log-time
- ``EMERGENCY_COUNCIL_SKIP`` — corroborated emergency carve-out fired
- ``DECISION_WALK_LINKED_COUNCIL`` — opportunistic link to decision-walk

Storing through the ledger gives us tamper-evidence (hash chain),
append-only semantics, and queryability via the existing ``get_events``
API — exactly the substrate properties the gate's audit trail needs.

The find_unconsumed_record + consume_record pair implements Aether's
Catch 2 (consume-on-use): one council walk clears at most one edit,
so the cheap path "walk once and reuse for many edits" is closed by
the ledger event sequence itself.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from divineos.core import ledger
from divineos.core.council_required.types import (
    EVENT_COUNCIL_RECORD_CONSUMED,
    EVENT_COUNCIL_RECORD_LOGGED,
    EVENT_COUNCIL_WALK_REJECTED,
    EVENT_EMERGENCY_COUNCIL_SKIP,
    CheckResult,
    CouncilRecord,
    LensFinding,
)


def _serialize_record(record: CouncilRecord) -> dict[str, Any]:
    """Convert a CouncilRecord to a ledger-payload-shaped dict."""
    return {
        "record_id": record.record_id,
        "walked_at": record.walked_at,
        "walker": record.walker,
        "triggered_edit_fingerprint": record.triggered_edit_fingerprint,
        "lenses_surfaced": list(record.lenses_surfaced),
        "lens_findings": [
            {"lens_name": f.lens_name, "finding_text": f.finding_text} for f in record.lens_findings
        ],
        "synthesis": record.synthesis,
        "confirmed_by": record.confirmed_by,
        # consumed_at is intentionally NOT serialized here — consumption is
        # a separate event (COUNCIL_RECORD_CONSUMED), so the original
        # COUNCIL_RECORD_LOGGED event remains immutable and consume-state
        # is derived by querying for the consumption event.
    }


def _deserialize_record(payload: dict[str, Any]) -> CouncilRecord:
    """Build a CouncilRecord from a ledger-payload dict."""
    return CouncilRecord(
        record_id=str(payload.get("record_id", "")),
        walked_at=float(payload.get("walked_at", 0.0)),
        walker=str(payload.get("walker", "")),
        triggered_edit_fingerprint=str(payload.get("triggered_edit_fingerprint", "")),
        lenses_surfaced=tuple(payload.get("lenses_surfaced") or []),
        lens_findings=tuple(
            LensFinding(
                lens_name=str(f.get("lens_name", "")),
                finding_text=str(f.get("finding_text", "")),
            )
            for f in (payload.get("lens_findings") or [])
        ),
        synthesis=str(payload.get("synthesis", "")),
        confirmed_by=payload.get("confirmed_by"),
        consumed_at=None,  # see note in _serialize_record
    )


def log_council_record(record: CouncilRecord, actor: str = "agent") -> str:
    """Write a passing council walk to the ledger.

    The caller is responsible for substance-binding BEFORE calling this —
    walks that fail substance-binding go through ``log_walk_rejection``
    instead. This function does NOT re-validate substance; it persists
    what was already accepted.

    Returns the ledger event_id (distinct from record.record_id; the
    event_id is the substrate-write artifact, record_id is the walk's
    own identifier).
    """
    payload = _serialize_record(record)
    return ledger.log_event(EVENT_COUNCIL_RECORD_LOGGED, actor, payload, validate=False)


def find_unconsumed_record(
    edit_fingerprint: str,
    recency_seconds: int,
    now: float | None = None,
) -> CouncilRecord | None:
    """Find a council_record matching the proposed edit's fingerprint,
    within the recency window, that has not yet been consumed.

    Returns the most recent matching record, or None if no eligible
    record exists. Caller checks substance-binding before allowing.

    The consumed-state check works by collecting all consumption events
    for matching records and excluding records whose record_id appears
    among them. Append-only semantics: nothing is mutated; the absence
    of a consumption event is what makes the record clearable.
    """
    if not edit_fingerprint:
        return None
    now = now if now is not None else time.time()
    cutoff = now - recency_seconds

    candidates = ledger.get_events(
        limit=200,
        event_type=EVENT_COUNCIL_RECORD_LOGGED,
        order="desc",
    )
    consumption_events = ledger.get_events(
        limit=500,
        event_type=EVENT_COUNCIL_RECORD_CONSUMED,
        order="desc",
    )
    consumed_record_ids: set[str] = set()
    for ev in consumption_events:
        payload = _payload_from_event(ev)
        rid = str(payload.get("record_id", ""))
        if rid:
            consumed_record_ids.add(rid)

    for ev in candidates:
        payload = _payload_from_event(ev)
        ts = float(payload.get("walked_at", 0.0))
        if ts < cutoff:
            # Newest-first ordering — once stale, the rest will be too.
            break
        fp = str(payload.get("triggered_edit_fingerprint", ""))
        if fp != edit_fingerprint:
            continue
        record_id = str(payload.get("record_id", ""))
        if record_id in consumed_record_ids:
            continue
        return _deserialize_record(payload)
    return None


def consume_record(
    record_id: str,
    edit_fingerprint: str,
    actor: str = "agent",
    now: float | None = None,
) -> str:
    """Mark a council_record as consumed by a specific edit.

    Writes a COUNCIL_RECORD_CONSUMED event. Append-only design: the
    original COUNCIL_RECORD_LOGGED event is not mutated; consumption is
    a separate event that find_unconsumed_record cross-references.

    Returns the consumption event_id.
    """
    payload = {
        "record_id": record_id,
        "edit_fingerprint": edit_fingerprint,
        "consumed_at": now if now is not None else time.time(),
    }
    return ledger.log_event(EVENT_COUNCIL_RECORD_CONSUMED, actor, payload, validate=False)


def log_walk_rejection(
    record: CouncilRecord,
    check_result: CheckResult,
    actor: str = "agent",
) -> str:
    """Write a COUNCIL_WALK_REJECTED event for a walk that failed
    substance-binding (Aether Catch 5).

    Carries the proposed council_record contents, the specific check that
    fired, and the pointer to what would clear it. Two reasons it matters:
    the agent gets a debuggable rejection rather than opaque silence, AND
    a pattern of repeated rejections surfaces the optimizer attempting to
    pass without engaging.
    """
    payload = {
        "proposed_record": _serialize_record(record),
        "failed_check_name": check_result.failed_check_name,
        "what_would_clear_it": check_result.what_would_clear_it,
        "rejected_at": time.time(),
    }
    return ledger.log_event(EVENT_COUNCIL_WALK_REJECTED, actor, payload, validate=False)


def log_emergency_skip(
    edit_fingerprint: str,
    reason: str,
    corroborator_event_id: str,
    actor: str = "agent",
) -> str:
    """Write an EMERGENCY_COUNCIL_SKIP event (Aether Catch 4).

    Caller validates the corroborator exists BEFORE calling this; this
    function only records the decision, it does not re-validate. The
    corroborator_event_id binds the skip to a substrate-fact (compaction,
    hook-failure, or scheduled-task), closing the self-attestation
    route-around at design-time.
    """
    payload = {
        "edit_fingerprint": edit_fingerprint,
        "reason": reason,
        "corroborator_event_id": corroborator_event_id,
        "skipped_at": time.time(),
    }
    return ledger.log_event(EVENT_EMERGENCY_COUNCIL_SKIP, actor, payload, validate=False)


def count_emergency_skips_in_window(window_days: int, now: float | None = None) -> int:
    """Count EMERGENCY_COUNCIL_SKIP events in the trailing window.

    Numerator for the falsifier-E rate check (emergency carve-out used
    routinely >5% over 7 days = emergency becomes the cheap path). The
    rate denominator is total gate-fires; this function returns the
    numerator only — callers divide.
    """
    now = now if now is not None else time.time()
    cutoff = now - (window_days * 86400)
    events = ledger.get_events(
        limit=1000,
        event_type=EVENT_EMERGENCY_COUNCIL_SKIP,
        order="desc",
    )
    count = 0
    for ev in events:
        payload = _payload_from_event(ev)
        ts = float(payload.get("skipped_at", 0.0))
        if ts < cutoff:
            break  # ordered newest-first
        count += 1
    return count


def find_corroborator_event(
    corroborator_event_id: str,
    accepted_event_types: frozenset[str],
    accepted_actors: frozenset[str],
) -> dict[str, Any] | None:
    """Resolve a corroborator event_id against the substrate ledger and
    verify it matches an accepted event-type OR an accepted actor.

    Returns the matched event dict, or None if the id does not resolve
    to a real event of an accepted shape. Aether Catch 4 — self-attested
    "unreachable" is closed at design-time by requiring the corroborator
    be a real substrate-fact.
    """
    if not corroborator_event_id:
        return None
    type_candidates = ledger.get_events(
        limit=500,
        event_type=accepted_event_types,
        order="desc",
    )
    actor_candidates = []
    for actor in accepted_actors:
        actor_candidates.extend(ledger.get_events(limit=500, actor=actor, order="desc"))
    for ev in (*type_candidates, *actor_candidates):
        if str(ev.get("event_id", "")) == corroborator_event_id:
            return ev
    return None


def new_record_id() -> str:
    """Generate a fresh council record_id."""
    return f"council-{uuid.uuid4().hex[:12]}"


def _payload_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Pull the payload dict out of a ledger event row.

    The ledger stores payload as a JSON string; ``get_events`` returns
    the raw row. This helper parses it. Returns empty dict if the
    payload is missing or unparseable — a corrupt event should not
    crash the gate, only fail-to-find.
    """
    raw = ev.get("payload")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


__guardrail_required__ = True
