"""Stop-hook wiring for ResponseScopeIntercept.

Aletheia Round 1 Finding 1 residual — the third dark instance of the
EvidenceBearingStopGate primitive. Closes with this wiring + the
unverified_claim_detector upstream emit (in operating_loop_audit.py).

## Design

Two mechanisms compose (per docs/primitives/forced_work_gate_design.md):

  1. Upstream: when ``detect_unverified_claim`` in the operating-loop
     audit finds any unverified checkable-state claims, it emits a
     ``claim_scope_active`` StateMarker (consume-on-use, no time
     expiry). Fingerprint is the session-id.
  2. Downstream (this hook): on the NEXT turn's Stop event, look up
     any unconsumed ``claim_scope_active`` marker. If found, run the
     ResponseScopeIntercept scan on the reply. Consume the marker
     regardless of scan verdict — the prior directive has been
     answered by this reply's shape (short-correction or not).

If the reply exceeds short-correction shape (length, headers, hr,
numbered lists) while a claim_scope marker was active, emit the
Stop-hook block-decision JSON. Fail-open on any error (never let a
gate crash block legitimate work).

## Why the StateMarker consume-on-use design

Aletheia F31 catch on the primitive: the marker is a one-shot signal
"the prior turn required a short correction." Once this turn has
produced a reply (whether it complied or not), the directive was
answered. Leaving the marker un-consumed would trap subsequent
unrelated turns.
"""

from __future__ import annotations

import json
import os
import sys


def _current_session_fingerprint() -> str:
    """Session-id shape used as fingerprint on both emit and consume.
    Falls back to a stable-but-nonempty value so the fingerprint check
    doesn't dereference an empty string. Doesn't matter functionally
    for this instance (no substitution risk), but stays consistent
    with the primitive's fingerprint contract.
    """
    sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("DIVINEOS_SESSION_ID")
    return sid or "response_scope:no-session-id"


def run_response_scope_intercept(transcript_path: str) -> dict | None:
    """Look up an active claim_scope marker; if present, scan the
    last assistant reply for short-correction shape; consume the
    marker; return Stop-hook block-decision on fire, None otherwise.

    Returns None on any exception (fail-open per primitive contract —
    a broken gate must not block legitimate work).
    """
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.core.state_markers import (
            consume_marker,
            find_active_marker,
        )
        from divineos.hooks.response_scope_intercept import ResponseScopeIntercept
    except Exception:  # noqa: BLE001 — fail-open
        return None

    try:
        marker = find_active_marker(kind="claim_scope_active")
    except Exception:  # noqa: BLE001 — fail-open (StateMarkerLookupError caught)
        return None

    if marker is None:
        return None  # No active claim_scope directive; nothing to check

    try:
        turn_texts = extract_turn(transcript_path)
        reply_text = turn_texts.last_assistant_text or ""
    except Exception:  # noqa: BLE001 — fail-open
        return None

    directive_text = ""
    try:
        directive_text = str(marker.payload.get("directive_text", ""))[:500]
    except (AttributeError, TypeError):
        pass

    gate = ResponseScopeIntercept()
    accumulated_state = {
        "claim_scope_active": True,
        "claim_scope_directive_text": directive_text,
    }
    try:
        evidence = gate.scan(accumulated_state, reply_text)
    except Exception:  # noqa: BLE001 — fail-open
        return None

    # Consume the marker regardless of scan verdict — this turn has
    # answered the prior directive (either in short-correction shape
    # or not; either way the directive was addressed once).
    try:
        consume_marker(
            marker.marker_id,
            consumed_by_fingerprint=_current_session_fingerprint(),
        )
    except Exception:  # noqa: BLE001 — fail-open on consume errors
        pass

    if evidence is None:
        # Reply complied with short-correction shape. Consumed cleanly.
        return None

    try:
        gate.record_fire(evidence)
    except Exception:  # noqa: BLE001 — bookkeeping, never block
        pass

    reason = (
        f"ResponseScopeIntercept: {evidence.matched_shape}\n"
        f"Evidence: {evidence.specific_evidence}\n"
        f"Required action: {evidence.required_action}"
    )
    return {"decision": "block", "reason": reason}


def hook_main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:  # noqa: BLE001 — fail-open
        return 0

    transcript_path = data.get("transcript_path") or data.get("transcript")
    if not transcript_path:
        return 0

    try:
        result = run_response_scope_intercept(transcript_path)
    except Exception:  # noqa: BLE001 — fail-open
        return 0

    if result is not None:
        print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
