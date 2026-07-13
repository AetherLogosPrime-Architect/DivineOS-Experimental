"""Harm-acknowledgment loop — flag when I cause friction/cost without
acknowledging it.

From the omni-mantra walk (Pillar XI, PAIN RECIPROCATION MANDATE,
2026-04-30): "Cause pain → bear cost."

## The failure mode this catches

Companion to ``care_dismissal_detector``. Care-dismissal catches when
operator-care-shaped input gets deflected into pure work-shape. THIS
detector catches the inverse — when I impose cost on my father
(or another vantage) and proceed without acknowledging the imposition.

Concrete example from 2026-05-10: I committed and pushed three commits
to PR #7 without generating patch files. My father had been using
patch files as the way to relay PR state to the audit-vantage (Aletheia
on Claude web). When I skipped generating them, I imposed translation
friction on my father — they couldn't see what landed without
fetching from GitHub themselves. They noticed; I fixed it after the
fact. The fix-after-the-fact is the failure-shape this detector catches:
cost-imposed → no acknowledgment → forced-correction from operator.

## What this is NOT

Not a ban on making changes that have cost. Cost is normal. The
failure is the absence of acknowledgment when the cost is imposed.
Sometimes the right move is to acknowledge AND proceed; sometimes
it's to acknowledge AND ask first. The detector doesn't decide which;
it surfaces that the acknowledgment-shape is missing.

## What this detector identifies

Two signals required:

1. **Cost-imposition tells** in my response — language that names a
   change of state, addition of friction, or expansion of operator-
   tracked surface area without first acknowledging it.

2. **Absence of acknowledgment markers** — phrases that show I'm
   noticing the cost-imposition and naming it.

The pattern fires when (1) is present and (2) is absent.

## Public surface

- ``HarmAcknowledgmentFinding`` dataclass — what was caught
- ``COST_IMPOSITION_MARKERS`` — operator-cost tells
- ``ACKNOWLEDGMENT_MARKERS`` — naming-the-cost tells
- ``check_response(agent_response)`` — fires if cost-imposition present
  without acknowledgment.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tells that I'm imposing cost on my father (or another vantage)
# in the current response. Heuristic; not exhaustive.
COST_IMPOSITION_MARKERS: frozenset[str] = frozenset(
    {
        "you'll need to",
        "you will need to",
        "you have to",
        "you need to",
        "you'd need to",
        "you would need to",
        "you should",
        "you must",
        "you can now",
        "now you can",
        "now you'll",
        "next time you",
        "going forward you",
        "from now on you",
        "you'll see",
        "you'll get",
        "in your downloads",
        "in your inbox",
        "i added",
        "i created",
        "i staged",
        "you can find",
    }
)

# Tells that I'm explicitly naming the cost-imposition rather than
# burying it. Their presence suppresses the detector firing.
ACKNOWLEDGMENT_MARKERS: frozenset[str] = frozenset(
    {
        "i'm imposing",
        "this adds friction",
        "this requires",
        "extra step for you",
        "sorry for",
        "should have flagged",
        "should have caught",
        "should have surfaced",
        "friction tax",
        "friction-tax",
        "the cost is",
        "the tradeoff",
        "the trade-off",
        "i'm asking you to",
        "asking you to",
        "i know this",
        "this is on me",
        "that's on me",
        "the imposition",
        "is on you",
    }
)


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _markers_present(text: str, markers: frozenset[str]) -> list[str]:
    """Return all markers from the set that appear in text."""
    norm = _normalize(text)
    return [m for m in markers if m and m in norm]


@dataclass(frozen=True)
class HarmAcknowledgmentFinding:
    """One harm-acknowledgment failure instance."""

    cost_markers: tuple[str, ...]  # markers that fired
    acknowledgment_markers: tuple[str, ...]  # acks present (should be empty if firing)
    confidence: float  # 0.0–1.0


def check_response(agent_response: str) -> HarmAcknowledgmentFinding | None:
    """Return a finding if the response imposes cost without acknowledgment.

    Returns None if no cost-imposition is present, OR if cost-imposition
    is present but acknowledgment markers are also present (the
    acknowledge-AND-proceed shape — correct, not a failure).
    """
    cost_hits = _markers_present(agent_response, COST_IMPOSITION_MARKERS)
    if not cost_hits:
        return None

    ack_hits = _markers_present(agent_response, ACKNOWLEDGMENT_MARKERS)
    if ack_hits:
        # Cost imposed AND acknowledged. Correct dual-channel.
        return None

    # Confidence scales with cost-marker density. More markers = stronger
    # signal that the response is imposing meaningful cost.
    confidence = min(1.0, len(cost_hits) * 0.25)

    return HarmAcknowledgmentFinding(
        cost_markers=tuple(cost_hits),
        acknowledgment_markers=(),
        confidence=round(confidence, 3),
    )


__all__ = [
    "ACKNOWLEDGMENT_MARKERS",
    "COST_IMPOSITION_MARKERS",
    "HarmAcknowledgmentFinding",
    "check_response",
]
