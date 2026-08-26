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

2. **If there's an open fire**, report the original evidence.
   Same fire, same line, until it's cleared.

3. **If no open fire**, run the scan. If an elevated ESCAPE rate is
   detected, emit a new GATE_FIRE with fresh evidence. Otherwise,
   silent pass.

## DEMOTED TO A RECORDER, 2026-08-25

Nothing here blocks any more. Andrew: *"we probably need to just have it
record the numbers not block or warn, this was created early on as a
scaffolding before the gates were being developed properly and were being
bypassed.. now there is a bypass protocol.. so bypasses get authorized..
logged and the root cause investigated and fixed, so a 3 strike rule is
pretty pointless.. however many strikes you give.. you will max them out
before anything is done.. so making the protocol trigger on any bypass is
the better fix."*

The per-occurrence protocol he describes already exists and predates this
demotion: ``bypass_telemetry.record_bypass`` files a root-cause
investigation obligation on EVERY non-compliance bypass, with a separate
branch for defect-escapes where the repair is owed to the gate rather
than to my discipline. Checked before building — the thing worth building
was already there.

So this gate was scaffolding from before that protocol, and a threshold
on top of per-occurrence enforcement is three-strikes with a bigger
number: however many strikes are given, they max out before anything is
done. It contradicted Andrew 2026-07-20 — *"not 3 times.. every time..
every single occurence gets investigated"* — for as long as it existed.

What remains is the count, written to the ledger as a GATE_FIRE carrying
its evidence, and surfaced by the narrative telemetry block. The event
holds matched_shape, specific_evidence and required_action, so demoting
loses no information — only the stop.

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


def check_and_record(
    get_events=None,
    bypass_rate_fn=None,
    scan_gate=None,
    cooloff_seconds: float = _COOLOFF_SECONDS_DEFAULT,
) -> tuple[int, str]:
    """Core logic — separated from I/O for testability.

    Returns (exit_code, message). The exit code is now always 0 — see the
    module docstring for the 2026-08-25 demotion. The tuple shape is kept
    so the callers and tests that read a second element keep working, and
    so a future decision to re-arm has somewhere to put the reason.

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

    # An open fire used to keep blocking until cleared. It now reports and
    # steps aside — see the module docstring for why the whole gate was
    # demoted 2026-08-25.
    open_fire = _find_open_fire(scan_gate.gate_name, get_events)
    if open_fire is not None:
        # The fire's evidence is already on the ledger from when it was
        # raised; nothing is re-emitted and nothing is stopped. The lookup
        # stays because "is there an open fire" still decides whether the
        # scan re-runs below.
        return 0, ""

    # No open fire, no recent clearance — run the scan against live state
    try:
        stats = bypass_rate_fn(window_days=scan_gate._window_days)
    except Exception:  # noqa: BLE001
        return 0, ""  # fail-open

    evidence = scan_gate.scan(accumulated_state={"bypass_stats": stats}, just_emitted_text="")
    if evidence is None:
        return 0, ""

    # New fire — record it. The recording is the whole job now.
    # The GATE_FIRE event carries matched_shape, specific_evidence and
    # required_action into the ledger, so recording loses nothing the old
    # stderr message used to say — only the stop.
    scan_gate.record_fire(evidence)
    return 0, ""


def hook_main() -> int:
    """Entry point for the PreToolUse shell hook to call.

    Reads PreToolUse JSON from stdin, records a GATE_FIRE when the escape
    rate is elevated, and always exits 0. It stopped blocking 2026-08-25;
    the per-occurrence bypass protocol in ``bypass_telemetry.record_bypass``
    is the enforcement, and this is the count beside it.
    """
    try:
        _ = sys.stdin.read()  # consume input even if unused
    except Exception:  # noqa: BLE001
        return 0

    try:
        exit_code, _unused = check_and_record()
    except Exception:  # noqa: BLE001
        return 0

    return exit_code


if __name__ == "__main__":
    sys.exit(hook_main())
