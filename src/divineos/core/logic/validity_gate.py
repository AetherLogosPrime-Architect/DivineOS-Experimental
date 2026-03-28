"""Validity gate — warrant-aware promotion for the maturity lifecycle.

The existing maturity system promotes based on repetition count alone.
This gate adds a structural check: does the knowledge have valid
justification, not just frequency?

Rules:
- RAW → HYPOTHESIS: automatic (no warrant needed, just first access)
- HYPOTHESIS → TESTED: needs at least 1 valid warrant
- TESTED → CONFIRMED: needs 2+ valid warrants from different types
- Any entry with all warrants defeated cannot promote regardless of count
"""

from __future__ import annotations

from dataclasses import dataclass


from divineos.core.logic.warrants import get_warrants


# ─── Types ───────────────────────────────────────────────────────────


@dataclass
class ValidityVerdict:
    """Result of a validity gate check."""

    passed: bool
    current_maturity: str
    target_maturity: str | None
    reason: str
    warrant_count: int = 0
    warrant_types: list[str] | None = None


# ─── Gate Logic ──────────────────────────────────────────────────────


def check_validity_for_promotion(
    knowledge_id: str,
    current_maturity: str,
    target_maturity: str,
) -> ValidityVerdict:
    """Check if a knowledge entry's warrants support promotion.

    This is called by the maturity system AFTER the corroboration-based
    check passes. It's a second gate: "yes you've been seen enough times,
    but do you have real justification?"
    """
    warrants = get_warrants(knowledge_id, status="ACTIVE")
    valid_warrants = [w for w in warrants if w.is_valid()]
    warrant_types = list({w.warrant_type for w in valid_warrants})

    # RAW → HYPOTHESIS: always allowed (low bar, just needs first encounter)
    if current_maturity == "RAW" and target_maturity == "HYPOTHESIS":
        return ValidityVerdict(
            passed=True,
            current_maturity=current_maturity,
            target_maturity=target_maturity,
            reason="RAW → HYPOTHESIS requires no warrant",
            warrant_count=len(valid_warrants),
            warrant_types=warrant_types,
        )

    # HYPOTHESIS → TESTED: needs at least 1 valid warrant
    if current_maturity == "HYPOTHESIS" and target_maturity == "TESTED":
        if len(valid_warrants) >= 1:
            return ValidityVerdict(
                passed=True,
                current_maturity=current_maturity,
                target_maturity=target_maturity,
                reason=f"Has {len(valid_warrants)} valid warrant(s)",
                warrant_count=len(valid_warrants),
                warrant_types=warrant_types,
            )
        return ValidityVerdict(
            passed=False,
            current_maturity=current_maturity,
            target_maturity=target_maturity,
            reason="HYPOTHESIS → TESTED requires at least 1 valid warrant",
            warrant_count=0,
            warrant_types=[],
        )

    # TESTED → CONFIRMED: needs 2+ valid warrants from different types
    if current_maturity == "TESTED" and target_maturity == "CONFIRMED":
        if len(valid_warrants) >= 2 and len(warrant_types) >= 2:
            return ValidityVerdict(
                passed=True,
                current_maturity=current_maturity,
                target_maturity=target_maturity,
                reason=f"Has {len(valid_warrants)} warrants across {len(warrant_types)} types",
                warrant_count=len(valid_warrants),
                warrant_types=warrant_types,
            )
        if len(valid_warrants) < 2:
            return ValidityVerdict(
                passed=False,
                current_maturity=current_maturity,
                target_maturity=target_maturity,
                reason=f"TESTED → CONFIRMED requires 2+ warrants, has {len(valid_warrants)}",
                warrant_count=len(valid_warrants),
                warrant_types=warrant_types,
            )
        return ValidityVerdict(
            passed=False,
            current_maturity=current_maturity,
            target_maturity=target_maturity,
            reason=f"TESTED → CONFIRMED requires 2+ warrant types, has {len(warrant_types)}: {warrant_types}",
            warrant_count=len(valid_warrants),
            warrant_types=warrant_types,
        )

    # Unknown transition — allow it (don't block what we don't understand)
    return ValidityVerdict(
        passed=True,
        current_maturity=current_maturity,
        target_maturity=target_maturity,
        reason=f"No validity rule for {current_maturity} → {target_maturity}",
        warrant_count=len(valid_warrants),
        warrant_types=warrant_types,
    )


def can_promote(knowledge_id: str, current_maturity: str, target_maturity: str) -> bool:
    """Quick check: can this entry promote? Returns True/False."""
    verdict = check_validity_for_promotion(knowledge_id, current_maturity, target_maturity)
    return verdict.passed
