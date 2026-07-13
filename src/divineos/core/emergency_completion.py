"""Emergency-completion lane for gates that fire on the wrong class of operation.

Aletheia's design 2026-07-08: some gates (specifically the overdue-prereg gate)
correctly guard against starting new substantive work, but cannot distinguish
"new substantive work" from "completing an in-flight safety-critical repair."
When such a gate fires on the wrong class, the operator faces three unclean
options:

    1. Clear the gate's backlog under duress (corrupts the backlog — the
       Goodhart-evasion the gate exists to prevent).
    2. Bypass the gate (trains the bypass reflex; habituation degrades the
       gate to warning per the psf-ac523181 compass observation).
    3. Leave the operation half-applied (silent hazard; usually worse than
       either of the above).

The emergency-completion lane is the fourth option. Its shape follows Andrew's
2026-06-29 teaching in exploration entry 108: **emergency-discipline needs to
be sharper, not relaxed — slower thinking before the bypass, more documentation
after, root-cause diagnostic mandatory not optional.**

Applied concretely, the lane requires:

**Before the arm (slower thinking, more documentation):**
- Reason >= 60 characters (force articulation, not "fix").
- `--for` reference to prior work being completed (hazard-record id, claim id,
  or pre-reg id). The lane closes a loop on already-started work; without a
  reference it's just a bypass with better costumes.
- `--risk` statement naming what breaks if the emergency-completion goes wrong.

**On consume (one-shot with debt):**
- Consumed on first gate check; requires re-arming for another action.
- Creates an `EMERGENCY_COMPLETION_DEBT` event that must be discharged.

**After the consume (root-cause diagnostic mandatory):**
- Debt must be discharged within 24 hours via
  `divineos emergency-completion resolve --diagnosis "..."` naming:
  (a) what class of operation the gate should have distinguished but didn't,
  (b) whether the emergency-classification was correct in hindsight,
  (c) what structural change (if any) would prevent the false-positive next time.
- Outstanding debt blocks new arms — if the last emergency-completion is
  undiscussed, no new one may be filed.

**Rate limiting (habituation prevention):**
- Weekly cap: 3 successful arms in the trailing 7 days.
- Exceeding the cap requires an explicit escalation event
  (`EMERGENCY_COMPLETION_ESCALATION_ACKED`) filed by the operator.

Tracked as its own event class distinct from `GATE_BYPASS`: the bypass
telemetry surface never counts emergency-completion, and emergency-completion
gets its own audit trail so the two shapes stay visibly distinct.

Origin story: 2026-07-08 late night, half-applied marker fix. The overdue-prereg
gate fired on the second half of an in-flight safety-critical marker repair.
Aletheia named the false-positive class through Andrew; this module is the
lane she designed. Specific hazard recorded as knowledge entry
5c6b9044-9e2a-49ef-af9a-cb91c8eff79a.

Not guardrail-listed. This is gate-adjacent live mechanism, not substrate-
integrity mechanism.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from divineos.core.paths import divineos_home


_TTL_SECONDS = 300  # 5 minutes from arm to consume
_MIN_REASON_LENGTH = 60  # sharper discipline: 60 not 40
_MIN_RISK_LENGTH = 30  # force articulation of what breaks if this is wrong
_DEBT_DISCHARGE_WINDOW_SECONDS = 24 * 60 * 60  # 24 hours to file diagnostic
_WEEKLY_CAP = 3
_WEEKLY_WINDOW_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class EmergencyCompletionArm:
    armed_at: float
    reason: str
    for_ref: str
    risk: str
    actor: str


@dataclass(frozen=True)
class EmergencyCompletionDebt:
    consumed_at: float
    reason: str
    for_ref: str
    risk: str
    actor: str
    consumed_by: str  # which gate consumed the arm


def _marker_path() -> Path:
    return divineos_home() / "emergency_completion_armed.json"


def _debt_path() -> Path:
    return divineos_home() / "emergency_completion_debt.json"


def _history_path() -> Path:
    """Rolling arm history for rate-limit calculation."""
    return divineos_home() / "emergency_completion_history.jsonl"


def _log_ledger(event_type: str, payload: dict) -> None:
    """Best-effort ledger append. Fail-open."""
    try:
        from divineos.core.ledger import log_event

        log_event(event_type=event_type, actor="emergency_completion", payload=payload)
    except Exception:  # noqa: BLE001 — fail-open per module contract
        pass


def _append_history(payload: dict) -> None:
    """Rate-limit history log. Line-oriented for easy rolling-window queries."""
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass


def _count_recent_arms() -> int:
    """Count successful arms in the trailing weekly window."""
    path = _history_path()
    if not path.exists():
        return 0
    cutoff = time.time() - _WEEKLY_WINDOW_SECONDS
    count = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("event") == "armed" and entry.get("armed_at", 0) >= cutoff:
                count += 1
    except OSError:
        return 0
    return count


def _outstanding_debt() -> EmergencyCompletionDebt | None:
    """Return the current outstanding debt, if any. Debts past their discharge
    window are still outstanding (the discipline says undischarged debt blocks
    future arms — expiration just makes the block permanent until resolved)."""
    path = _debt_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    try:
        return EmergencyCompletionDebt(**payload)
    except (TypeError, ValueError):
        return None


def arm(*, reason: str, for_ref: str, risk: str, actor: str = "aether") -> EmergencyCompletionArm:
    """Arm the emergency-completion lane for the next gate-fire.

    Preconditions (raise ValueError on violation):
    - reason must be >= _MIN_REASON_LENGTH characters
    - for_ref must be non-empty
    - risk must be >= _MIN_RISK_LENGTH characters
    - no outstanding debt from a prior emergency-completion
    - not over the weekly rate limit
    """
    reason = (reason or "").strip()
    if len(reason) < _MIN_REASON_LENGTH:
        raise ValueError(
            f"Emergency-completion reason too short: {len(reason)} chars < "
            f"{_MIN_REASON_LENGTH} required. State the in-flight critical "
            "repair, why the gate false-positived on this class, and what "
            "you're specifically completing."
        )
    for_ref = (for_ref or "").strip()
    if not for_ref:
        raise ValueError(
            "Emergency-completion --for is required. Point at prior work being "
            "completed (hazard-record knowledge-entry id, open claim id, or "
            "pre-reg id). The lane closes an in-flight loop; without a "
            "reference it's just a bypass."
        )
    risk = (risk or "").strip()
    if len(risk) < _MIN_RISK_LENGTH:
        raise ValueError(
            f"Emergency-completion --risk too short: {len(risk)} chars < "
            f"{_MIN_RISK_LENGTH} required. State what breaks if this "
            "emergency-completion is wrong. Forces slower thinking before "
            "the bypass, per Andrew 2026-06-29."
        )

    outstanding = _outstanding_debt()
    if outstanding is not None:
        raise RuntimeError(
            "Outstanding emergency-completion debt blocks new arm. Discharge "
            f"the prior debt (consumed at {outstanding.consumed_at}, for "
            f"{outstanding.for_ref!r}) via `divineos emergency-completion "
            'resolve --diagnosis "..."` before arming another.'
        )

    recent = _count_recent_arms()
    if recent >= _WEEKLY_CAP:
        raise RuntimeError(
            f"Emergency-completion weekly rate limit hit: {recent} arms in "
            f"trailing 7 days >= {_WEEKLY_CAP} cap. If this is a real "
            "emergency requiring another arm, file an escalation event with "
            "Andrew's acknowledgment first. Habituation is exactly what the "
            "cap prevents."
        )

    armed = EmergencyCompletionArm(
        armed_at=time.time(),
        reason=reason,
        for_ref=for_ref,
        risk=risk,
        actor=actor,
    )
    path = _marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(armed), indent=2), encoding="utf-8")

    _log_ledger("EMERGENCY_COMPLETION_ARMED", asdict(armed))
    _append_history({"event": "armed", **asdict(armed)})
    return armed


def is_armed() -> bool:
    """Read-only check: is a valid (non-expired) arm currently present?"""
    return _load_valid_arm() is not None


def has_outstanding_debt() -> bool:
    """Read-only check: is there an undischarged debt?"""
    return _outstanding_debt() is not None


def _load_valid_arm() -> EmergencyCompletionArm | None:
    path = _marker_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        path.unlink(missing_ok=True)
        return None
    try:
        armed = EmergencyCompletionArm(**payload)
    except (TypeError, ValueError):
        path.unlink(missing_ok=True)
        return None

    if time.time() - armed.armed_at > _TTL_SECONDS:
        _log_ledger("EMERGENCY_COMPLETION_EXPIRED", asdict(armed))
        path.unlink(missing_ok=True)
        return None
    return armed


def consume_if_armed(*, consumed_by: str) -> EmergencyCompletionArm | None:
    """Called by the gate. If an arm is present and valid, consume it (one-shot),
    create a debt record, and return the arm. Otherwise return None.

    `consumed_by` names the gate that consumed the arm. Logged as
    EMERGENCY_COMPLETION_CONSUMED (distinct from GATE_BYPASS — bypass
    telemetry never counts these).
    """
    armed = _load_valid_arm()
    if armed is None:
        return None

    _marker_path().unlink(missing_ok=True)

    debt = EmergencyCompletionDebt(
        consumed_at=time.time(),
        reason=armed.reason,
        for_ref=armed.for_ref,
        risk=armed.risk,
        actor=armed.actor,
        consumed_by=consumed_by,
    )
    _debt_path().parent.mkdir(parents=True, exist_ok=True)
    _debt_path().write_text(json.dumps(asdict(debt), indent=2), encoding="utf-8")

    _log_ledger(
        "EMERGENCY_COMPLETION_CONSUMED",
        {**asdict(debt)},
    )
    return armed


def resolve_debt(*, diagnosis: str, actor: str = "aether") -> EmergencyCompletionDebt:
    """Discharge the outstanding debt by filing a root-cause diagnosis.

    Diagnosis must name (a) what class the gate should have distinguished,
    (b) whether the emergency-classification was right in hindsight,
    (c) what structural change would prevent the false-positive next time.
    """
    diagnosis = (diagnosis or "").strip()
    if len(diagnosis) < 100:
        raise ValueError(
            f"Diagnosis too short: {len(diagnosis)} chars < 100 required. "
            "Name (a) what the gate should have distinguished, (b) whether "
            "the emergency-classification was right in hindsight, (c) what "
            "structural change prevents the false-positive next time. "
            "This is the load-bearing part of the discipline per Andrew "
            "2026-06-29."
        )
    debt = _outstanding_debt()
    if debt is None:
        raise RuntimeError("No outstanding emergency-completion debt to resolve.")

    _log_ledger(
        "EMERGENCY_COMPLETION_DEBT_RESOLVED",
        {
            **asdict(debt),
            "diagnosis": diagnosis,
            "resolved_at": time.time(),
            "resolved_by": actor,
        },
    )
    _append_history(
        {
            "event": "resolved",
            "consumed_at": debt.consumed_at,
            "resolved_at": time.time(),
            "diagnosis": diagnosis,
        }
    )
    _debt_path().unlink(missing_ok=True)
    return debt


def clear() -> bool:
    """Clear any armed marker without consuming it (aborts a pending arm).

    Does NOT clear an outstanding debt — those must be resolved via diagnosis.
    """
    path = _marker_path()
    if not path.exists():
        return False
    path.unlink(missing_ok=True)
    return True


__all__ = [
    "EmergencyCompletionArm",
    "EmergencyCompletionDebt",
    "arm",
    "is_armed",
    "has_outstanding_debt",
    "consume_if_armed",
    "resolve_debt",
    "clear",
]
