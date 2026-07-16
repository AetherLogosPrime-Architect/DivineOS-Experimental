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

    DEPRECATED FOR GATE USE — race-unsafe when paired with a subsequent
    ``consume_record`` call in the gate path. See ``consume_record``'s
    docstring for the TOCTOU race and its CI reproduction 2026-07-16.
    ``gate.decide()`` uses this only for the pre-binding read (safe,
    read-only) and delegates the actual find+consume to
    ``find_and_consume_atomically()`` which holds ``BEGIN IMMEDIATE``
    across both steps.

    This function is retained for the pre-binding read AND for test
    setup where a caller needs to check record presence without
    consuming. Any caller that pairs this with ``consume_record`` in a
    gate-decision path is a regression of the race bug — use
    ``find_and_consume_atomically()`` instead.

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

    DEPRECATED FOR GATE USE — race-unsafe. This two-call form
    (``find_unconsumed_record`` + ``consume_record`` separately) has a
    TOCTOU race under concurrent ``gate.decide()`` invocations: two
    concurrent callers can both find the same unconsumed record and
    both consume it, breaking the Aether Catch-2 invariant. CI surfaced
    this 2026-07-16 (Linux serialization tight enough to reproduce;
    Windows SQLite happened to serialize enough to hide it locally).

    For gate use, call ``find_and_consume_atomically()`` instead — it
    holds ``BEGIN IMMEDIATE`` across the find + consume so only one
    caller wins under contention. This two-call form is retained ONLY
    for test setup where you need to seed a record then separately
    assert-and-consume it under controlled non-concurrent conditions.
    Any non-test caller of these two functions is a regression of the
    race bug; add a callsite-check test if a new caller appears.

    Writes a COUNCIL_RECORD_CONSUMED event. Append-only design: the
    original COUNCIL_RECORD_LOGGED event is not mutated; consumption is
    a separate event that ``find_unconsumed_record`` cross-references.

    Returns the consumption event_id.
    """
    payload = {
        "record_id": record_id,
        "edit_fingerprint": edit_fingerprint,
        "consumed_at": now if now is not None else time.time(),
    }
    return ledger.log_event(EVENT_COUNCIL_RECORD_CONSUMED, actor, payload, validate=False)


def find_and_consume_atomically(
    edit_fingerprint: str,
    recency_seconds: int,
    actor: str = "agent",
    now: float | None = None,
) -> tuple[CouncilRecord, str] | None:
    """Find + consume in one serialized transaction — Aether Catch-2 fix.

    Aria + Aether concurrency fix 2026-07-16 (CI surfaced the race the
    Windows-local probe missed). The naive ``find_unconsumed_record`` →
    ``consume_record`` sequence has a TOCTOU race: two concurrent
    callers can both see the same "no consumption event yet" state,
    both write COUNCIL_RECORD_CONSUMED events, and both callers get
    ALLOW — the Catch-2 invariant broken.

    Fix pattern (same as ``backfill_chain_hashes`` in
    ``ledger.py:826-827``): open one connection with
    ``isolation_level = None`` + ``BEGIN IMMEDIATE`` so only one caller
    holds the write-lock at a time. The other caller waits, and by the
    time it acquires the lock the first caller's consumption event is
    committed. The waiting caller's own scan then sees the record as
    consumed and returns None.

    The gate MUST call this instead of the two-call sequence. Direct
    callers of ``find_unconsumed_record`` + ``consume_record`` reintroduce
    the race — deprecation notes on both name that explicitly.

    Returns:
        ``(record, consumption_event_id)`` if a matching unconsumed
        record was found AND successfully consumed inside this
        transaction. ``None`` if no eligible record exists, or if it
        was concurrently consumed by another caller who won the
        write-lock race.
    """
    if not edit_fingerprint:
        return None
    resolved_now = now if now is not None else time.time()
    cutoff = resolved_now - recency_seconds

    from divineos.core._ledger_base import _get_db_path, compute_hash
    import sqlite3

    conn = sqlite3.connect(str(_get_db_path()))
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Collect already-consumed record_ids from ledger events
            # inside the write-transaction. Any concurrent consume by a
            # racing caller either committed before us (and we see it
            # here) or is blocked waiting for our COMMIT.
            consumed_ids: set[str] = set()
            for (payload_json,) in conn.execute(
                "SELECT payload FROM system_events "
                "WHERE event_type = ? "
                "ORDER BY timestamp DESC LIMIT 500",
                (EVENT_COUNCIL_RECORD_CONSUMED,),
            ):
                try:
                    p = json.loads(payload_json)
                except (TypeError, ValueError):
                    continue
                rid = str(p.get("record_id", ""))
                if rid:
                    consumed_ids.add(rid)

            # Scan candidate LOGGED events newest-first for a matching
            # unconsumed record within the recency window.
            record: CouncilRecord | None = None
            for (payload_json,) in conn.execute(
                "SELECT payload FROM system_events "
                "WHERE event_type = ? "
                "ORDER BY timestamp DESC LIMIT 200",
                (EVENT_COUNCIL_RECORD_LOGGED,),
            ):
                try:
                    p = json.loads(payload_json)
                except (TypeError, ValueError):
                    continue
                ts = float(p.get("walked_at", 0.0))
                if ts < cutoff:
                    break  # newest-first — stale means the rest is too
                fp = str(p.get("triggered_edit_fingerprint", ""))
                if fp != edit_fingerprint:
                    continue
                record_id_val = str(p.get("record_id", ""))
                if record_id_val in consumed_ids:
                    continue
                record = _deserialize_record(p)
                break

            if record is None:
                conn.commit()  # release lock cleanly; nothing written
                return None

            # Insert the COUNCIL_RECORD_CONSUMED event directly on this
            # connection so it's part of the same atomic transaction.
            # Mirror ledger.log_event's payload+hash contract so
            # downstream verify passes over this row treat it identically
            # to a log_event-created row.
            consume_payload = {
                "record_id": record.record_id,
                "edit_fingerprint": edit_fingerprint,
                "consumed_at": resolved_now,
            }
            payload_str = json.dumps(consume_payload, sort_keys=True)
            content_hash = compute_hash(payload_str)
            consume_event_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO system_events "
                "(event_id, timestamp, event_type, actor, payload, content_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    consume_event_id,
                    resolved_now,
                    EVENT_COUNCIL_RECORD_CONSUMED,
                    actor,
                    payload_str,
                    content_hash,
                ),
            )
            conn.commit()
            return (record, consume_event_id)
        except (sqlite3.Error, OSError, TypeError, ValueError):
            conn.rollback()
            raise
    finally:
        conn.close()


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
