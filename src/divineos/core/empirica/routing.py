"""Council routing wrapper — which claims need review, and how much.

Phase 1 rules:

* ``TRIVIAL`` and ``NORMAL`` magnitude claims do NOT require council
  review. The existing knowledge-layer validity gate is sufficient.
* ``LOAD_BEARING`` claims require one council round.
* ``FOUNDATIONAL`` claims require two council rounds (different convocations).

"Rounds" in Phase 1 means separate calls to ``CouncilEngine.convene`` —
each with its own analyses. Future phases can differentiate rounds by
expert subset (science council, wisdom council, pattern council) but
the routing-layer API stays the same.

## What counts as council approval

A round "approves" when the returned ``CouncilResult.shared_concerns()``
is empty. Shared concerns means 2+ experts flagged the same worry — the
signal that multiple lenses see the same problem. Zero shared concerns
means no convergent objection. That's the honest gate: the council
isn't voting yes, it's failing to converge on a no.

## What this module is NOT

Not the council itself — just the routing wrapper. The actual expert
analysis lives in ``divineos.core.council``. Routing.py decides WHEN to
convene and how many rounds; the council decides what those rounds
produce.

Not a rubber stamp. If ``route_for_approval`` returns ``approved=False``,
the caller MUST NOT issue a receipt. The pre-reg falsifier explicitly
names bypass as a failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass

from divineos.core.empirica.types import ClaimMagnitude


# Number of council rounds required per magnitude. Values chosen per the
# module docstring; future phases can tune based on pre-reg review.
_ROUNDS_REQUIRED: dict[ClaimMagnitude, int] = {
    ClaimMagnitude.TRIVIAL: 0,
    ClaimMagnitude.NORMAL: 0,
    ClaimMagnitude.LOAD_BEARING: 1,
    ClaimMagnitude.FOUNDATIONAL: 2,
}


@dataclass(frozen=True)
class RoutingResult:
    """Outcome of council routing.

    * ``approved`` — True if the claim passed all required rounds (or
      none were required). False if any round returned shared concerns.
    * ``council_count`` — number of rounds that approved. Stored in
      the receipt for audit. Zero for TRIVIAL/NORMAL claims that
      didn't require review.
    * ``rationale`` — human-readable summary of what happened. Names
      each round's outcome (approved / blocked) and any shared
      concerns from blocked rounds. Load-bearing for pre-reg audit:
      a rationale of just "approved" with no detail is the decorative
      failure mode.
    """

    approved: bool
    council_count: int
    rationale: str


def rounds_required(magnitude: ClaimMagnitude) -> int:
    """Return how many council rounds the magnitude requires."""
    return _ROUNDS_REQUIRED[magnitude]


def route_for_approval(
    claim_content: str,
    magnitude: ClaimMagnitude,
    *,
    convene_fn: object = None,
) -> RoutingResult:
    """Route a claim through the required number of council rounds.

    ``convene_fn`` is an injected callable for TESTABILITY — it takes a
    problem string and returns an object with ``shared_concerns() ->
    list[str]``. Tests pass a stub returning canned concerns.

    Fable audit round 4 (2026-07-02) removed the production ``convene_fn``
    default. The prior implementation auto-loaded ``CouncilManager.convene``
    and gated approval on the keyword-matcher's ``shared_concerns()`` — a
    mechanical path standing in for a thinker actually engaging expert
    lenses. Per the code-cannot-think principle, mechanical convene output
    is not a council. When ``convene_fn`` is None on LOAD_BEARING or
    FOUNDATIONAL claims, this now returns ``approved=False`` with a
    rationale directing the caller to migrate to a walk-record-gated
    approval path (which discharges via ``divineos council log`` +
    substance_binding — the discipline ``check-council-required`` enforces).

    The injection seam is preserved so tests continue to work by passing
    ``convene_fn`` explicitly. Fail-closed for production is the intended
    behavior: LOAD_BEARING claims should NOT auto-approve via keyword
    matching. If a legitimate production path needs to approve a
    LOAD_BEARING claim, it must plumb through a walk record.
    """
    needed = rounds_required(magnitude)
    if needed == 0:
        return RoutingResult(
            approved=True,
            council_count=0,
            rationale=(
                f"magnitude={magnitude.name} below LOAD_BEARING threshold; "
                "no council review required"
            ),
        )

    if convene_fn is None:
        # Production path with no walk-record integration yet. Fail closed.
        return RoutingResult(
            approved=False,
            council_count=0,
            rationale=(
                f"magnitude={magnitude.name} requires {needed} council "
                "round(s), but the mechanical convene path was removed "
                "(Fable audit round 4, 2026-07-02). Provide a walk_record "
                "from a real logged council walk via `divineos council "
                "log` with substance_binding, or migrate this caller to "
                "the walk-record-gated approval path. Refusing "
                "auto-approval on the keyword-matcher output."
            ),
        )

    round_rationales: list[str] = []
    approved_rounds = 0
    for i in range(needed):
        result = convene_fn(claim_content)  # type: ignore[operator]
        shared = result.shared_concerns()
        if not shared:
            approved_rounds += 1
            round_rationales.append(f"round {i + 1}: approved (no shared concerns)")
        else:
            round_rationales.append(
                f"round {i + 1}: BLOCKED — shared concerns: {', '.join(shared[:3])}"
            )

    approved = approved_rounds == needed
    rationale = "; ".join(round_rationales)
    return RoutingResult(
        approved=approved,
        council_count=approved_rounds,
        rationale=rationale,
    )


__all__ = [
    "RoutingResult",
    "rounds_required",
    "route_for_approval",
]
