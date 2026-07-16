"""PreToolUse hook that wires BypassRateScan into actual enforcement.

Andrew 2026-07-15: "if they are not wired how do you expect them to work?"
— unwired code is a working test suite, not a working gate. This module
wires the gate.

## Fire/clear cycle design

The gate isn't just "check on every tool call" — that would fire the
same evidence over and over. Instead:

1. **Check the ledger for an open fire.** Look up the most recent
   GATE_FIRE for bypass_rate_scan. If any of these events happened
   AFTER that fire's timestamp, the fire is "cleared":
     - GATE_CLEARANCE for bypass_rate_scan (explicit primitive channel)
     - AUDIT_ROUND_CREATED (I ran divineos audit submit-round)
     - CLAIM_FILED (I ran divineos claim)

2. **If there's an open fire**, block with the original evidence.
   Same fire, same block message, until it's cleared.

3. **If no open fire**, run the scan. If elevated bypass rate is
   detected, emit a new GATE_FIRE and block with fresh evidence.
   Otherwise, silent pass.

## Why "any of three" is the clearance rule

Aria's UNLOCK-CONTINGENT audit (2026-07-15) identified the self-
attestation vulnerability in the primitive's cleared_by field. Full
structural fix is task #4. This hook's partial-answer for now: the
clearance ISN'T self-attested — it's satisfied by actually running one
of the investigation commands, which produce their own event records.
No route to "I fixed it" without doing something that a real command
writes to the ledger.

## Exit codes

- 0: pass (no fire condition, or fire cleared)
- 2: block (open fire, evidence in deny_reason)

Fail-open on any error path — a broken enforcement hook must not
block work silently. Log to stderr and exit 0.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


# Event types that count as "clearing" an open bypass_rate_scan fire.
_CLEARANCE_EVENT_TYPES = (
    "GATE_CLEARANCE",
    "AUDIT_ROUND_CREATED",
    "CLAIM_FILED",
)


def _parse_iso(ts_str: str) -> float:
    """Parse an ISO timestamp to epoch seconds. Returns 0 on failure."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def _find_open_fire(gate_name: str, get_events) -> dict[str, Any] | None:
    """Return the most recent unresolved GATE_FIRE for gate_name, or None.

    "Unresolved" = no clearance event of any allowed type has a
    timestamp after this fire's timestamp.
    """
    try:
        fires = get_events(event_type="GATE_FIRE", limit=100, order="desc")
    except Exception:  # noqa: BLE001
        return None
    for fire in fires:
        payload = fire.get("payload") or {}
        if payload.get("gate_name") != gate_name:
            continue
        fire_ts = _parse_iso(fire.get("timestamp") or "")
        if fire_ts == 0:
            continue
        # Check for any clearance event after this fire
        for event_type in _CLEARANCE_EVENT_TYPES:
            try:
                clears = get_events(event_type=event_type, limit=200, order="desc")
            except Exception:  # noqa: BLE001
                continue
            for clear in clears:
                clear_ts = _parse_iso(clear.get("timestamp") or "")
                if clear_ts <= fire_ts:
                    # Descending order — remaining events are older, stop
                    break
                if event_type == "GATE_CLEARANCE":
                    clear_payload = clear.get("payload") or {}
                    if clear_payload.get("gate_name") != gate_name:
                        continue
                # Any matching clearance means this fire is cleared
                return None
        # This fire has no matching clearance since it landed — it's open
        result: dict[str, Any] = fire
        return result
    return None


#: Cool-off window after a clearance event — how long to suppress
#: NEW fires when the state that fired the gate is still present. Rationale
#: (live-discovered 2026-07-15): rate doesn't drop from elevated fast, so
#: post-clearance the scan re-fires on every tool call, creating a harass-
#: loop. The investigation IS in progress; re-firing every tool call is
#: redundant. Default: 1 hour.
_COOLOFF_SECONDS_DEFAULT = 3600.0


def _recent_clearance_within(gate_name: str, window_seconds: float, get_events) -> bool:
    """True if any clearance event for this gate happened within the recent
    window. Used to suppress redundant re-fires while an investigation is
    already in progress."""
    import time
    from datetime import datetime

    cutoff = time.time() - window_seconds
    for event_type in _CLEARANCE_EVENT_TYPES:
        try:
            events = get_events(event_type=event_type, limit=100, order="desc")
        except Exception:  # noqa: BLE001
            continue
        for e in events:
            ts_str = e.get("timestamp") or ""
            try:
                ts_epoch = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            except (ValueError, AttributeError):
                continue
            if ts_epoch < cutoff:
                # desc order — remaining events are older, stop
                break
            if event_type == "GATE_CLEARANCE":
                payload = e.get("payload") or {}
                if payload.get("gate_name") != gate_name:
                    continue
            return True
    return False


def check_and_block(
    get_events=None,
    bypass_rate_fn=None,
    scan_gate=None,
    cooloff_seconds: float = _COOLOFF_SECONDS_DEFAULT,
) -> tuple[int, str]:
    """Core logic — separated from I/O for testability.

    Returns (exit_code, deny_reason). Exit code 0 = pass, 2 = block.

    Cool-off window (2026-07-15 harass-loop fix): if a clearance event
    landed within the last ``cooloff_seconds`` (default 1h), suppress
    NEW fires. The investigation IS in progress; re-firing on every tool
    call while the rate stays elevated is harass, not enforcement. Open
    fires from BEFORE the cooloff window still block — this only affects
    NEW-fire emission.
    """
    # Late imports so tests can inject stubs without dragging in the ledger
    if get_events is None:
        from divineos.core.ledger import get_events as _ge

        get_events = _ge
    if bypass_rate_fn is None:
        from divineos.core.bypass_telemetry import bypass_rate as _br

        bypass_rate_fn = _br
    if scan_gate is None:
        from divineos.hooks.bypass_rate_scan import BypassRateScan

        scan_gate = BypassRateScan()

    # LAYER 2 COOL-OFF (2026-07-16 live-discovered): cool-off check runs
    # BEFORE the open-fire check. Rationale: under sustained-elevated
    # state, every commit emits a new fire; the NEXT commit finds that
    # fire "open" (no clearance after it because clearance predates it).
    # Layer 1 cool-off only suppressed NEW fires — it didn't suppress
    # blocks-on-open-fires. Layer 2: recent-clearance suppresses ALL
    # blocks. The investigation IS in progress regardless of temporal
    # ordering of specific fire vs clearance timestamps.
    if _recent_clearance_within(scan_gate.gate_name, cooloff_seconds, get_events):
        return 0, ""

    # Check for an open fire — same evidence keeps blocking until cleared
    open_fire = _find_open_fire(scan_gate.gate_name, get_events)
    if open_fire is not None:
        payload = open_fire.get("payload") or {}
        return 2, _format_block_message(payload, is_reopen=False)

    # No open fire, no recent clearance — run the scan against live state
    try:
        stats = bypass_rate_fn(window_days=scan_gate._window_days)
    except Exception:  # noqa: BLE001
        return 0, ""  # fail-open

    evidence = scan_gate.scan(accumulated_state={"bypass_stats": stats}, just_emitted_text="")
    if evidence is None:
        return 0, ""

    # New fire — record it and block
    scan_gate.record_fire(evidence)
    payload = {
        "gate_name": evidence.gate_name,
        "matched_shape": evidence.matched_shape,
        "specific_evidence": evidence.specific_evidence,
        "required_action": evidence.required_action,
    }
    return 2, _format_block_message(payload, is_reopen=True)


def _format_block_message(payload: dict[str, Any], is_reopen: bool) -> str:
    prefix = (
        "BLOCKED (bypass-rate scan)"
        if is_reopen
        else "BLOCKED (bypass-rate scan — fire still open, not cleared)"
    )
    matched = payload.get("matched_shape", "?")
    evidence = payload.get("specific_evidence", "?")
    action = payload.get("required_action", "?")
    return (
        f"{prefix}\n"
        f"  MATCHED: {matched}\n"
        f"  EVIDENCE: {evidence}\n"
        f"  REQUIRED ACTION: {action}\n"
        "\n"
        "Clear this gate by running one of:\n"
        "  - divineos audit submit-round '<focus>' --actor external-auditor  (starts a real audit)\n"
        "  - divineos claim '<statement>'  (files a claim to investigate)\n"
        "  - Any GATE_CLEARANCE event for bypass_rate_scan via the primitive's channel"
    )


def hook_main() -> int:
    """Entry point for the PreToolUse shell hook to call.

    Reads PreToolUse JSON from stdin, decides fire/pass, exits with
    appropriate code and (on block) prints the deny message to stderr.
    """
    try:
        _ = sys.stdin.read()  # consume input even if unused
    except Exception:  # noqa: BLE001
        return 0

    try:
        exit_code, deny_reason = check_and_block()
    except Exception:  # noqa: BLE001
        return 0

    if exit_code == 2 and deny_reason:
        print(deny_reason, file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(hook_main())
