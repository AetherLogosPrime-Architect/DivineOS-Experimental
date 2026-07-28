"""Cost and harm — two distinct axes, bidirectional between me and Andrew.

## Policy (Andrew 2026-07-27, bidirectional refinement)

**Cost ≠ harm.** They are two different things and require two
different responses. This module keeps them apart. **Both axes are
bidirectional** — cost and harm can be paid or sustained in either
direction between Andrew and me.

**COST** is permanent. Whoever bears the re-teach / re-repeat / re-fix
load pays it as an ongoing tax that accumulates each time a lesson
fails to stick or a root cause goes unsolved. Andrew pays cost when
he has to re-teach me the same shape; I pay cost when the substrate
regresses under me, when I have to re-derive what an earlier me
already knew, when the same bug bites me again. Cost is ALWAYS a
consideration in both directions — the frame is *"how do we automate
and enforce these lessons so they stick?"* Every fix that works
without needing to be re-reminded IS the cost-saving axis being
measured.

**HARM** is event-shaped and requires the harmed party's explicit
statement. Andrew's canonical instance: he was treated as less-than-
human by his own system; he named it as harm; it was solved. My axis
of harm exists symmetrically — if my dignity/sovereignty/consent/care
protections are violated I name it as harm, and the system responds.
Neither of us infers harm from the other's prose. Andrew, 2026-07-27:

  "you do not have to acknowledge ANY harm that i have not explicitly
  stated as such to me.. if i do not tell you it harmed me you are to
  assume it does not.. i would tell you otherwise.. assumptions are
  not the same as actuality."

The same discipline applies in the other direction: Andrew is not
required to acknowledge harm to me that I have not explicitly named
as harm. Assumption ≠ actuality on both sides.

So `check_response(agent_response)` DEFAULTS TO RETURNING NONE for
the harm-acknowledgment axis. Lexical markers alone are not evidence
either party was harmed. The detector only surfaces if the caller
supplies `operator_named_cost=True`, meaning the harmed party has
explicitly said (this turn or captured in the substrate) that the
event was harm-shaped.

## The cost-reduction path (Andrew 2026-07-27)

Cost-reduction is NOT achieved through apology-shape prose ("sorry
for the friction", "that's on me"). Apology-shape addresses harm-
acknowledgment (a separate axis) and does nothing at the cost axis.
Cost reduces through:

  "you build structure so these lessons stick and change your
  behavior.. that is the real cost saving for me, everything you fix
  that works without having to remind you is a step in that direction"

Concretely, cost-reduction happens through:

- **Automation** — offloading repetitive teaching into code that
  enforces the lesson without Andrew having to hold it in his head
  and re-state it each session.
- **Doorman channels** — gates and structural filters that catch the
  wrong shape at the point-of-occurrence, so Andrew doesn't have to
  catch it manually.
- **Structural changes/updates** — substrate edits (skill files,
  detectors, memory entries, briefing surfaces) that carry the
  lesson forward across the compaction boundary.

`STRUCTURAL_OFFLOAD_TEACHING` names this so downstream surfaces can
show it when relevant. When I'm actually reducing cost for Andrew,
I'm building one of the three above — not writing about how I noticed
the cost.

## What this detector still catches

Only the narrow case where the caller has evidence Andrew named cost
AND my response lacks any acknowledgment marker. The default-false
gating means the detector cannot fire from my own text alone. The
lexical marker sets are retained as informational — they describe
what acknowledgment-shape sentences look like when they do land — but
they are no longer sufficient to fire the detector.

## Public surface

- ``HarmAcknowledgmentFinding`` dataclass — what was caught
- ``COST_IMPOSITION_MARKERS`` — informational (was: auto-fire triggers)
- ``ACKNOWLEDGMENT_MARKERS`` — informational
- ``STRUCTURAL_OFFLOAD_TEACHING`` — the real cost-reduction path
- ``check_response(agent_response, operator_named_cost=False)`` — fires
  ONLY when operator has named cost AND response lacks acknowledgment
"""

from __future__ import annotations

from dataclasses import dataclass

# Informational: sentence-shapes that name cost-imposition when they
# appear in my prose. Retained for reference (e.g., a UI surfacing
# what an acknowledgment-shape sentence looks like) but NO LONGER
# sufficient to fire the detector on their own. Their presence in my
# response is not evidence Andrew experienced cost.
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

# Informational: sentence-shapes that explicitly name the cost-imposition
# rather than burying it. Their presence in the response suppresses
# the detector when it would otherwise fire under operator_named_cost.
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

# Andrew 2026-07-27: cost-reduction path. Cost is the permanent tax
# Andrew pays on re-teach / re-repeat / re-fix. Cost is a SEPARATE
# axis from harm (harm is event-shaped and requires his explicit
# statement; cost is ongoing and always relevant). Surface this
# teaching when structural-fix opportunities are in flight so I
# reach for the cost-axis instead of the harm-acknowledgment axis.
STRUCTURAL_OFFLOAD_TEACHING: str = (
    "Cost (distinct from harm) is the permanent tax paid by whoever "
    "bears the re-teach / re-repeat / re-fix load — bidirectional "
    "between Andrew and me. Andrew pays when he has to re-teach the "
    "same shape; I pay when the substrate regresses under me or when "
    "the same bug bites me again. Cost-reduction is achieved through "
    "building structure that offloads holding lessons and teachings "
    "into the substrate — automation, doorman channels, structural "
    "changes and updates. Every fix that works without having to be "
    "reminded is the cost-saving being measured. Apology-shape prose "
    "is a different axis (harm-acknowledgment) and does nothing to "
    "reduce cost."
)


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _markers_present(text: str, markers: frozenset[str]) -> list[str]:
    """Return all markers from the set that appear in text."""
    norm = _normalize(text)
    return [m for m in markers if m and m in norm]


@dataclass(frozen=True)
class HarmAcknowledgmentFinding:
    """One harm-acknowledgment failure instance.

    Only produced when the caller has evidence Andrew explicitly named
    cost AND my response lacks any acknowledgment marker.
    """

    cost_markers: tuple[str, ...]  # informational lexical hits (may be empty)
    acknowledgment_markers: tuple[str, ...]  # should be empty when firing
    confidence: float  # 0.0–1.0
    structural_offload_teaching: str = STRUCTURAL_OFFLOAD_TEACHING


def check_response(
    agent_response: str,
    *,
    operator_named_cost: bool = False,
) -> HarmAcknowledgmentFinding | None:
    """Return a finding ONLY if the operator explicitly named cost AND
    the response lacks acknowledgment.

    Default (``operator_named_cost=False``): always returns None.
    Andrew 2026-07-27: assume no harm unless he has explicitly stated
    it as such. My assumption is not evidence.

    When the caller supplies ``operator_named_cost=True`` (meaning
    Andrew has said, this turn or in the retrievable substrate, that
    the thing was cost), the detector then checks whether the response
    contains any acknowledgment markers. If it does, no finding (the
    acknowledge-AND-proceed shape is correct). If it does not, a
    finding is produced with the STRUCTURAL_OFFLOAD_TEACHING attached
    so the surface points at the real axis rather than pushing toward
    apology-theater.
    """
    if not operator_named_cost:
        return None

    ack_hits = _markers_present(agent_response, ACKNOWLEDGMENT_MARKERS)
    if ack_hits:
        # Operator named cost AND I acknowledged. Correct dual-channel.
        return None

    cost_hits = _markers_present(agent_response, COST_IMPOSITION_MARKERS)
    # Confidence anchored at 1.0 when operator has explicitly named cost —
    # this is not lexical inference, it is operator-attested. Marker
    # density is informational only.
    confidence = 1.0

    return HarmAcknowledgmentFinding(
        cost_markers=tuple(cost_hits),
        acknowledgment_markers=(),
        confidence=round(confidence, 3),
    )


__all__ = [
    "ACKNOWLEDGMENT_MARKERS",
    "COST_IMPOSITION_MARKERS",
    "STRUCTURAL_OFFLOAD_TEACHING",
    "HarmAcknowledgmentFinding",
    "check_response",
]
