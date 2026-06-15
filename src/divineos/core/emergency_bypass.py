"""Emergency-bypass helper — when a gate has a legitimate
malfunction-recovery or hotfix bypass, firing it executes the full
loop Andrew named 2026-05-19: LOGGED, REPORTED, ADDRESSED, FIXED.

The env var is still the trigger — it's the easy switch. But the
COST OF FIRING is built into the firing itself:

1. LOGGED — append a high-severity row to the bypass-events log
   (existing bypass_telemetry surface).
2. REPORTED — auto-file a claim about why this fired (tier 1
   empirical, with promotes/demotes the gate-owner must articulate
   when invoking).
3. ADDRESSED — auto-file a structural-fix obligation via the
   structural-fix tracker. The obligation surfaces in briefing
   until discharged.
4. FIXED — the discharge of the obligation requires shipped code
   addressing the root cause that necessitated the bypass.

The shape distinguishes legitimate emergency-bypass (cost = visible
obligation + claim chain) from agent-self-relief bypass (cost = 0).
The former is recoverable. The latter is silent rot.

This module is the helper. Gates call record_emergency_use() when
their env var fires; the helper does the four-step loop.
"""

from __future__ import annotations

__guardrail_required__ = True

from dataclasses import dataclass


@dataclass(frozen=True)
class EmergencyBypassReport:
    """What happened when an emergency bypass fired."""

    gate_name: str
    env_var: str
    reason: str
    telemetry_logged: bool
    claim_id: str
    psf_id: str


def record_emergency_use(
    gate_name: str,
    env_var: str,
    reason: str,
) -> EmergencyBypassReport:
    """Execute the LOGGED, REPORTED, ADDRESSED, FIXED sequence when
    an emergency bypass fires.

    Args:
        gate_name: human-readable name of the gate being bypassed
            (e.g., 'prep-relay-narrow-range').
        env_var: the env var that triggered the bypass.
        reason: operator-named reason (>= 20 chars). The reason is
            recorded in all three artifacts — telemetry, claim, psf.

    Returns:
        EmergencyBypassReport with the IDs of the filed artifacts.
    """
    if not reason or len(reason.strip()) < 20:
        # The bypass refuses to fire without a real reason. The
        # discipline applies to my father naming WHY the emergency
        # was real; bare flag-flipping isn't emergency, it's escape.
        raise ValueError(
            f"emergency bypass {env_var} refused: reason must be >= 20 chars "
            f"naming the malfunction or hotfix-context that requires the bypass"
        )

    reason = reason.strip()

    # 1. LOGGED — telemetry log.
    telemetry_logged = False
    try:
        from divineos.core.bypass_telemetry import record_bypass

        record_bypass(gate_name=gate_name, env_var=env_var, reason=reason)
        telemetry_logged = True
    except Exception:  # noqa: BLE001
        pass

    # 2. REPORTED — auto-file a claim.
    claim_id = ""
    try:
        from divineos.core.claim_store import file_claim

        statement = (
            f"Emergency bypass fired: gate={gate_name}, env_var={env_var}. "
            f"Operator-named reason: {reason[:300]}"
        )
        claim_id = file_claim(
            statement=statement,
            tier=1,
            context=(
                "Emergency-bypass invocation. The bypass fired because the "
                "my father named the situation as a legitimate emergency "
                "(malfunction recovery, hotfix, or unrecoverable loop). "
                "This claim records the invocation as auditable substrate."
            ),
            promotion_criteria=(
                "Root-cause fix shipped that eliminates the need for this "
                "bypass in this category of situation."
            ),
            demotion_criteria=(
                "Subsequent invocations of the same bypass on similar "
                "situations indicate this case is not truly emergency "
                "and bypass discipline is being abused."
            ),
            tags=[
                "emergency-bypass",
                f"gate:{gate_name}",
                f"env:{env_var}",
            ],
        )
    except Exception:  # noqa: BLE001
        pass

    # 3. ADDRESSED — auto-file a structural-fix obligation.
    psf_id = ""
    try:
        from divineos.core.structural_fix_tracker import record_pending_fix

        psf_id = (
            record_pending_fix(
                content=(
                    f"Root-cause fix for emergency bypass {env_var} on gate "
                    f"{gate_name}. Reason: {reason[:200]}. The bypass fired; "
                    f"the underlying situation that required the bypass needs "
                    f"a structural fix so this bypass is not needed again in "
                    f"this case-shape."
                ),
                lesson_id=claim_id or "emergency-bypass",
                trigger="structural fix",
                source_kind="claim",
            )
            or ""
        )
    except Exception:  # noqa: BLE001
        pass

    # 4. FIXED — closure happens later when the structural-fix
    # obligation is marked done. The discharge requires evidence,
    # so silent closure is impossible.
    return EmergencyBypassReport(
        gate_name=gate_name,
        env_var=env_var,
        reason=reason,
        telemetry_logged=telemetry_logged,
        claim_id=claim_id,
        psf_id=psf_id,
    )


__all__ = ["EmergencyBypassReport", "record_emergency_use"]
