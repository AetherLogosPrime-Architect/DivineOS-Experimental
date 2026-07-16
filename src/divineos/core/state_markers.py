"""StateMarker — substrate-persisted signals from upstream emitters to
downstream readers.

See ``docs/primitives/forced_work_gate_design.md`` for the full contract.
This is the first-half implementation of the addendum's "the two dark
ForcedWorkGate instances need shared state contract" design. Aria +
Aether peer-designed 2026-07-16.

Two known consumers at build time:
    - ``response_scope_intercept_hook`` — reads ``claim_scope_active``
      markers emitted by ``unverified_claim_detector`` in the prior turn.
      No time expiry, consume-on-use only.
    - ``ForcedWorkGate.refuse()`` for instances with
      ``ALTERNATIVE_CLEARANCE == "operator_bypass"`` — reads
      ``operator_bypass_authorized`` markers emitted by
      ``divineos ... authorize-bypass`` CLI. 15-min expiry per Aria's
      design-question #1.

Both use this module identically. Third+ instances (future) can reuse
the same primitive.

## Contract

- ``emit_marker(kind, fingerprint, payload, expires_in_seconds=None)``
  emits an EMITTED event, returns the marker_id.
- ``find_active_marker(kind, fingerprint_predicate=None)`` walks the
  ledger for unconsumed, unexpired markers of this kind matching the
  predicate. Returns the newest match or None.
- ``consume_marker(marker_id, consumed_by_fingerprint)`` atomically
  finds+consumes the marker. If ``consumed_by_fingerprint !=
  authorized_fingerprint``, additionally emits a LOUD
  STATE_MARKER_FINGERPRINT_MISMATCH event (Aria's add — a mismatch is a
  security event, not a debug log).

## Fail-loud discipline

Per Aletheia's root pattern #2, this module distinguishes:
- "no marker found" (empty result, valid) — returns None from find_active_marker
- "marker lookup crashed" (failure, invalid) — raises StateMarkerLookupError

The two are structurally different observable states so a consumer
cannot mistake a lookup failure for an all-clear.

## Concurrency

``consume_marker`` uses BEGIN IMMEDIATE to serialize the find+consume
pair (same shape as Aria's ``find_and_consume_atomically`` from her
Fix A / council-required concurrency fix). Two consumers racing on the
same marker: the first commits, the second re-scans and finds the
marker already consumed → its consume call is a no-op with a distinct
verdict ("already consumed").
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from divineos.core.ledger import log_event
from divineos.core._ledger_base import get_connection


# ── Event type names ─────────────────────────────────────────────────

_EMITTED = "STATE_MARKER_EMITTED"
_CONSUMED = "STATE_MARKER_CONSUMED"
_FINGERPRINT_MISMATCH = "STATE_MARKER_FINGERPRINT_MISMATCH"


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class StateMarker:
    """A substrate-persisted signal from an upstream emitter to a
    downstream reader. See module docstring for contract.
    """

    marker_id: str
    kind: str
    fingerprint: str
    payload: dict[str, Any] = field(default_factory=dict)
    emitted_at: float = 0.0
    expires_at: float | None = None
    consumed_at: float | None = None
    consumed_by_fingerprint: str | None = None

    def is_active(self, now: float | None = None) -> bool:
        """True if unconsumed AND unexpired (or no expiry)."""
        if self.consumed_at is not None:
            return False
        if self.expires_at is None:
            return True
        current = time.time() if now is None else now
        return self.expires_at > current


@dataclass(frozen=True)
class ConsumeVerdict:
    """Result of a consume_marker call. Distinguishes the three
    possible outcomes so callers can distinguish success from
    already-consumed from not-found. Aletheia root pattern #2: fail
    modes must be observably different from success."""

    outcome: str  # "consumed" | "already_consumed" | "not_found" | "expired"
    marker: StateMarker | None
    fingerprint_mismatch: bool = False


class StateMarkerLookupError(RuntimeError):
    """Raised when ledger lookup for marker state crashes. Distinct
    from returning None (which means the lookup ran cleanly and found
    nothing). Per Aletheia root pattern #2 — a crashed detector must
    not report the same shape as a clean-and-empty detector.
    """


# ── Public API ───────────────────────────────────────────────────────


def emit_marker(
    kind: str,
    fingerprint: str,
    payload: dict[str, Any] | None = None,
    expires_in_seconds: float | None = None,
) -> str:
    """Emit a STATE_MARKER_EMITTED event for a new state marker.

    Returns the marker_id (a uuid4 hex string). The marker is
    findable via ``find_active_marker`` until it is consumed via
    ``consume_marker`` or (if expires_in_seconds is set) expires.
    """
    if not kind or not fingerprint:
        raise ValueError("kind and fingerprint are both required, non-empty")
    marker_id = uuid.uuid4().hex
    now = time.time()
    expires_at: float | None = None
    if expires_in_seconds is not None:
        if expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be positive when provided")
        expires_at = now + expires_in_seconds

    event_payload = {
        "marker_id": marker_id,
        "kind": kind,
        "fingerprint": fingerprint,
        "payload": dict(payload or {}),
        "emitted_at": now,
        "expires_at": expires_at,
    }
    log_event(_EMITTED, "state_markers", event_payload, validate=False)
    return marker_id


def find_active_marker(
    kind: str,
    fingerprint_predicate: Callable[[str], bool] | None = None,
    now: float | None = None,
) -> StateMarker | None:
    """Return the newest unconsumed, unexpired marker of this kind
    matching the fingerprint predicate. Returns None if none found.

    Raises StateMarkerLookupError on ledger-lookup crash — never
    returns None to indicate a lookup failure (Aletheia root pattern
    #2 discipline: fail-loud, not fail-blind).
    """
    if not kind:
        raise ValueError("kind is required")
    predicate = fingerprint_predicate or (lambda _fp: True)
    current = time.time() if now is None else now

    conn = get_connection()
    try:
        try:
            rows = conn.execute(
                # Walk EMITTED events newest-first; filter to matching
                # kind. LIMIT 500 is Aria's discipline from Fix A —
                # walk first, index later if measured slow.
                "SELECT event_id, payload FROM system_events "
                "WHERE event_type = ? "
                "ORDER BY timestamp DESC, rowid DESC "
                "LIMIT 500",
                (_EMITTED,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise StateMarkerLookupError(f"ledger EMITTED-event lookup failed: {exc}") from exc

        # Load consumed marker_ids into a set for O(1) membership check.
        try:
            consumed_rows = conn.execute(
                "SELECT payload FROM system_events "
                "WHERE event_type = ? "
                "ORDER BY timestamp DESC, rowid DESC "
                "LIMIT 500",
                (_CONSUMED,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise StateMarkerLookupError(f"ledger CONSUMED-event lookup failed: {exc}") from exc

        consumed_ids: set[str] = set()
        for row in consumed_rows:
            try:
                data = json.loads(row[0])
                mid = data.get("marker_id")
                if isinstance(mid, str):
                    consumed_ids.add(mid)
            except (json.JSONDecodeError, TypeError):
                continue

        for row in rows:
            try:
                data = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("kind") != kind:
                continue
            marker_id = data.get("marker_id")
            if not isinstance(marker_id, str):
                continue
            if marker_id in consumed_ids:
                continue
            expires_at = data.get("expires_at")
            if expires_at is not None and expires_at <= current:
                continue
            fingerprint = data.get("fingerprint") or ""
            if not predicate(fingerprint):
                continue
            return StateMarker(
                marker_id=marker_id,
                kind=data.get("kind", ""),
                fingerprint=fingerprint,
                payload=dict(data.get("payload") or {}),
                emitted_at=float(data.get("emitted_at") or 0.0),
                expires_at=expires_at if expires_at is None else float(expires_at),
            )
        return None
    finally:
        conn.close()


def consume_marker(marker_id: str, consumed_by_fingerprint: str) -> ConsumeVerdict:
    """Atomically consume a marker. Uses BEGIN IMMEDIATE to serialize
    against concurrent consumers on the same marker.

    Behavior:
    - Marker not found → outcome="not_found"
    - Marker already consumed → outcome="already_consumed"
    - Marker expired → outcome="expired"
    - Fingerprint matches → outcome="consumed", emits CONSUMED event
    - Fingerprint mismatches → outcome="consumed",
      fingerprint_mismatch=True, emits CONSUMED event AND
      STATE_MARKER_FINGERPRINT_MISMATCH event (LOUD, per Aria's add).
    """
    if not marker_id or not consumed_by_fingerprint:
        raise ValueError("marker_id and consumed_by_fingerprint are both required, non-empty")
    now = time.time()

    conn = get_connection()
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Find the EMITTED event for this marker_id.
            rows = conn.execute(
                "SELECT payload FROM system_events "
                "WHERE event_type = ? "
                "ORDER BY timestamp DESC, rowid DESC "
                "LIMIT 500",
                (_EMITTED,),
            ).fetchall()
            emitted: dict[str, Any] | None = None
            for row in rows:
                try:
                    data = json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    continue
                if data.get("marker_id") == marker_id:
                    emitted = data
                    break
            if emitted is None:
                conn.execute("ROLLBACK")
                return ConsumeVerdict(outcome="not_found", marker=None)

            # Check if already consumed.
            consumed_rows = conn.execute(
                "SELECT payload FROM system_events "
                "WHERE event_type = ? "
                "ORDER BY timestamp DESC, rowid DESC "
                "LIMIT 500",
                (_CONSUMED,),
            ).fetchall()
            for row in consumed_rows:
                try:
                    data = json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    continue
                if data.get("marker_id") == marker_id:
                    conn.execute("ROLLBACK")
                    marker = _marker_from_emitted(emitted)
                    return ConsumeVerdict(outcome="already_consumed", marker=marker)

            # Check expiry.
            expires_at = emitted.get("expires_at")
            if expires_at is not None and expires_at <= now:
                conn.execute("ROLLBACK")
                return ConsumeVerdict(outcome="expired", marker=_marker_from_emitted(emitted))

            authorized_fingerprint = emitted.get("fingerprint") or ""
            fingerprint_mismatch = authorized_fingerprint != consumed_by_fingerprint

            # Commit the atomic section (the lookup + about-to-emit
            # decision are the serialized part; the emits below run
            # after commit because log_event manages its own conn).
            conn.execute("COMMIT")
        except sqlite3.Error:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    # Emit CONSUMED — after lock released so log_event's own writes
    # don't deadlock against our BEGIN IMMEDIATE.
    log_event(
        _CONSUMED,
        "state_markers",
        {
            "marker_id": marker_id,
            "kind": emitted.get("kind", ""),
            "original_fingerprint": authorized_fingerprint,
            "consumed_by_fingerprint": consumed_by_fingerprint,
            "consumed_at": now,
        },
        validate=False,
    )

    # Emit LOUD mismatch event if applicable (Aria 2026-07-16). This
    # is a terminal audit event, not itself a marker.
    if fingerprint_mismatch:
        log_event(
            _FINGERPRINT_MISMATCH,
            "state_markers",
            {
                "marker_id": marker_id,
                "kind": emitted.get("kind", ""),
                "authorized_fingerprint": authorized_fingerprint,
                "consumed_by_fingerprint": consumed_by_fingerprint,
                "originating_context": _extract_originating_context(emitted),
                "consuming_context": {
                    "consumed_at": now,
                    "consumed_by_fingerprint": consumed_by_fingerprint,
                },
                "detected_at": now,
            },
            validate=False,
        )

    marker = _marker_from_emitted(
        emitted,
        consumed_at=now,
        consumed_by_fingerprint=consumed_by_fingerprint,
    )
    return ConsumeVerdict(
        outcome="consumed",
        marker=marker,
        fingerprint_mismatch=fingerprint_mismatch,
    )


# ── Helpers ──────────────────────────────────────────────────────────


def _marker_from_emitted(
    emitted: dict[str, Any],
    consumed_at: float | None = None,
    consumed_by_fingerprint: str | None = None,
) -> StateMarker:
    """Reconstruct a StateMarker from an EMITTED event payload."""
    expires_at = emitted.get("expires_at")
    return StateMarker(
        marker_id=emitted.get("marker_id", ""),
        kind=emitted.get("kind", ""),
        fingerprint=emitted.get("fingerprint", ""),
        payload=dict(emitted.get("payload") or {}),
        emitted_at=float(emitted.get("emitted_at") or 0.0),
        expires_at=expires_at if expires_at is None else float(expires_at),
        consumed_at=consumed_at,
        consumed_by_fingerprint=consumed_by_fingerprint,
    )


def _extract_originating_context(emitted: dict[str, Any]) -> dict[str, Any]:
    """Pull the audit-relevant subset of the EMITTED payload for the
    fingerprint-mismatch event's originating_context field. Per Aria's
    addendum: payload subset (e.g. operator quote hash + reason).
    """
    payload = emitted.get("payload") or {}
    subset: dict[str, Any] = {"emitted_at": emitted.get("emitted_at")}
    # Common audit-relevant keys — copy if present.
    for key in ("quote_hash", "reason", "directive_text", "operator"):
        if key in payload:
            subset[key] = payload[key]
    return subset


__all__ = [
    "StateMarker",
    "ConsumeVerdict",
    "StateMarkerLookupError",
    "emit_marker",
    "find_active_marker",
    "consume_marker",
]
