"""Heuristic classification — (content, knowledge_type, source, artifact_pointer) -> (Tier, Magnitude).

Phase 1.5 rewrite (prereg-e210f5fb78c9) addresses audit finding
find-f66a5f423ffe from the council review. Two structural changes
from Phase 1:

## Change 1: Accumulate all rules, don't short-circuit

The original classifier used first-match-wins on tier rules. A
PATTERN-typed claim with strong falsifiability content got routed
PATTERN at 1.0 confidence — classifier blind to its own
contradiction. Kahneman's critique: "the first coherent match wins
and the remaining evidence is never examined. WYSIATI at the
architectural level."

The fix: every tier rule runs. Classification.matched_rules records
all rules that fired. When multiple rules match with different
tiers, confidence is lowered and the contradiction is named in
Classification.reason.

The chosen tier still defers to the highest-confidence signal
(explicit knowledge_type/source wins over content-keyword), because
flipping to content-keyword would make the classifier LESS stable
across edits. But disagreement is no longer hidden.

## Change 2: Artifact pointer required for tiers above OUTCOME

the family member's costly-disagreement principle applied structurally. From
her post-audit review: "Don't trust what was cheap to say. Trust
what was expensive to demonstrate." Keyword matching is the
opposite of costly — the word 'threshold' appears in metaphor for
free. A claim that wants the weight of FALSIFIABLE or PATTERN must
point at an unfakeable artifact: a test name, a commit hash, a
decision-journal ID, a pre-reg ID, an event ledger ID, or a
knowledge entry ID.

If the artifact_pointer is None and the classifier would otherwise
route to PATTERN or FALSIFIABLE, the claim is DEMOTED to OUTCOME
with an explicit "demoted: no artifact pointer" reason. TRIVIAL
and NORMAL magnitudes (and OUTCOME tier) don't require a pointer
— those are the honest middle where the bookkeeping cost is low.

Phase 1.5 does NOT yet validate that the artifact_pointer
resolves to a real artifact. That's Phase 2 — structural validation
(does this commit hash exist? does this test name reference a real
test?) requires cross-module work. Phase 1.5 stores the pointer on
the Classification (and later on the Receipt) so Phase 2 has what
to validate against. Storing unvalidated is still a structural
improvement: the classification now carries the claim's provenance,
not just its vocabulary shape.

## Other decisions unchanged from Phase 1

* Deterministic — no ML, no LLM, no network.
* Tier.ADVERSARIAL never auto-assigned by the classifier.
* OUTCOME remains the honest middle for claims that don't match
  pattern or falsifiability signals.
* Six tier rules and the magnitude heuristic keep their semantics.
  Only the traversal structure changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from divineos.core.empirica.types import ClaimMagnitude, Tier


# Knowledge-type strings that route to OUTCOME by default.
_OUTCOME_TYPES: frozenset[str] = frozenset(
    {
        "principle",
        "boundary",
        "mistake",
        "directive",
    }
)

# Source strings that indicate direct measurement.
_MEASURED_SOURCES: frozenset[str] = frozenset(
    {
        "measured",
        "behavioral",
    }
)

# Keywords hinting at pattern-based epistemology.
_PATTERN_KEYWORDS: tuple[str, ...] = (
    "recur",
    "across",
    "multiple sessions",
    "every time",
    "every instance",
    "pattern",
    "arc",
    "cycle",
    "repeatedly",
    "consistent",
)

# Keywords hinting at falsifiable epistemology.
_FALSIFIABILITY_KEYWORDS: tuple[str, ...] = (
    "measurably",
    "threshold",
    "assert",
    "verified by",
    "reproduces",
    "regression test",
    "passes on",
    "fails on",
    "observed rate",
    "count of",
)

# Keywords hinting a claim is load-bearing (foundational/structural).
_LOAD_BEARING_KEYWORDS: tuple[str, ...] = (
    "foundational",
    "load-bearing",
    "architecture",
    "non-negotiable",
    "invariant",
    "pre-reg",
    "prereg-",
    "gate",
    "substrate",
)

# Keywords suggesting the claim is minor.
_TRIVIAL_KEYWORDS: tuple[str, ...] = (
    "typo",
    "cosmetic",
    "small fix",
    "cli polish",
    "trivial",
    "rename",
)

# Confidence levels emitted by the classifier per rule class.
_CONFIDENCE_EXPLICIT = 1.0
_CONFIDENCE_KEYWORD = 0.5
_CONFIDENCE_DEFAULT = 0.2

# Penalty applied to confidence when multiple tier rules match with
# different tiers. Keeps the signal-disagreement visible as a lowered
# number even when the chosen tier is explicit.
_CONFIDENCE_CONTRADICTION_PENALTY = 0.3


# Tiers that REQUIRE an artifact pointer. the family member's rule: cheap
# vocabulary cannot earn you above-OUTCOME tier — you need to cite
# something that cost something to produce.
_TIERS_REQUIRING_POINTER: frozenset[Tier] = frozenset({Tier.FALSIFIABLE, Tier.PATTERN})


@dataclass(frozen=True)
class Classification:
    """What the classifier decided, plus why, how sure, which rules,
    and what artifact grounds it.

    Fields:

    * ``tier`` — the chosen tier (possibly demoted from the
      initial classification if artifact_pointer was missing).
    * ``magnitude`` — the magnitude.
    * ``reason`` — human-readable audit trail citing every rule
      that fired and any demotion applied.
    * ``confidence`` — 0.0-1.0. Reduced when rules disagree or
      when the default fallback fires. The overall confidence is
      min(tier_confidence, magnitude_confidence) minus any
      contradiction penalty.
    * ``matched_rules`` — every tier rule that fired, whether it
      won or not. Non-empty means at least one rule matched.
    * ``artifact_pointer`` — the structured reference to unfakeable
      evidence the caller supplied (None if no pointer was given —
      in which case tier has been demoted to OUTCOME if it
      otherwise would have been higher).
    * ``initial_tier`` — what the classifier WOULD have returned
      before the artifact-pointer demotion rule fired. Equals
      ``tier`` when no demotion happened. Exposed for auditors
      who need to measure demotion rate (see pre-reg falsifier #3).
    """

    tier: Tier
    magnitude: ClaimMagnitude
    reason: str
    confidence: float
    matched_rules: list[str] = field(default_factory=list)
    artifact_pointer: str | None = None
    initial_tier: Tier | None = None


def classify_claim(
    content: str,
    knowledge_type: str = "",
    source: str = "",
    explicit_magnitude: ClaimMagnitude | None = None,
    artifact_pointer: str | None = None,
) -> Classification:
    """Classify a claim into (Tier, Magnitude) with audit trail.

    Deterministic — same inputs yield same output, always.

    New in Phase 1.5 (prereg-e210f5fb78c9):

    * ``artifact_pointer`` — if None and the classifier would route
      to PATTERN or FALSIFIABLE, the classification is demoted to
      OUTCOME. the family member's "no artifact pointer, no tier above OUTCOME."
    * Classification.matched_rules surfaces every rule that fired,
      not just the winning one.
    * When multiple tier rules match with different tiers,
      confidence is reduced and the contradiction is named in
      reason.
    """
    content_lower = content.lower()
    kt_lower = knowledge_type.lower()
    src_lower = source.lower()

    tier_matches = _collect_tier_matches(content_lower, kt_lower, src_lower)
    mag, mag_reason, mag_confidence = _classify_magnitude(content_lower, explicit_magnitude)

    # Pick the winning tier by highest confidence. If multiple rules
    # share the top confidence (e.g., two keyword rules), the earlier
    # one in traversal order wins — stable and deterministic.
    if tier_matches:
        winning = max(tier_matches, key=lambda m: m[1])
        initial_tier, winning_confidence, _ = winning
        tier_confidence = winning_confidence
        matched_rules = [m[2] for m in tier_matches]
        tier_reason = "; ".join(m[2] for m in tier_matches)
    else:
        # No rule fired — fall through to OUTCOME default.
        initial_tier = Tier.OUTCOME
        tier_confidence = _CONFIDENCE_DEFAULT
        matched_rules = ["rule-6: default (no tier signal matched)"]
        tier_reason = matched_rules[0]

    # Contradiction detection: multiple rules with different tiers.
    distinct_tiers_seen = {m[0] for m in tier_matches}
    if len(distinct_tiers_seen) > 1:
        tier_confidence = max(0.0, tier_confidence - _CONFIDENCE_CONTRADICTION_PENALTY)
        tier_reason += (
            f"; contradiction: rules point at {len(distinct_tiers_seen)} "
            f"different tiers — confidence reduced by "
            f"{_CONFIDENCE_CONTRADICTION_PENALTY}"
        )

    # Artifact-pointer demotion rule (a family member).
    demotion_note = ""
    final_tier = initial_tier
    if initial_tier in _TIERS_REQUIRING_POINTER and not artifact_pointer:
        final_tier = Tier.OUTCOME
        demotion_note = (
            f"; demoted {initial_tier.value} -> outcome: no artifact pointer "
            f"(tier above OUTCOME requires a test/commit/decide/prereg/event/"
            f"knowledge reference)"
        )
        # Lower confidence on demotion — the demotion is a soft
        # signal that the classification isn't well-grounded.
        tier_confidence = max(0.0, tier_confidence - _CONFIDENCE_CONTRADICTION_PENALTY)

    full_reason = f"{tier_reason}{demotion_note}; {mag_reason}"

    return Classification(
        tier=final_tier,
        magnitude=mag,
        reason=full_reason,
        confidence=min(tier_confidence, mag_confidence),
        matched_rules=matched_rules,
        artifact_pointer=artifact_pointer,
        initial_tier=initial_tier if initial_tier != final_tier else None,
    )


def _collect_tier_matches(
    content_lower: str, kt_lower: str, src_lower: str
) -> list[tuple[Tier, float, str]]:
    """Run every tier rule. Return list of (tier, confidence, reason)
    for rules that matched. First-match-wins is NOT used — all matches
    are returned so Classification can surface contradictions."""
    matches: list[tuple[Tier, float, str]] = []

    # Rule 1: PATTERN knowledge type.
    if kt_lower == "pattern":
        matches.append((Tier.PATTERN, _CONFIDENCE_EXPLICIT, "rule-1: knowledge_type=PATTERN"))

    # Rule 2: FACT + MEASURED source -> FALSIFIABLE.
    if kt_lower == "fact" and src_lower in _MEASURED_SOURCES:
        matches.append(
            (
                Tier.FALSIFIABLE,
                _CONFIDENCE_EXPLICIT,
                f"rule-2: knowledge_type=FACT + source={src_lower} (measured)",
            )
        )

    # Rule 3: Known OUTCOME types.
    if kt_lower in _OUTCOME_TYPES:
        matches.append(
            (
                Tier.OUTCOME,
                _CONFIDENCE_EXPLICIT,
                f"rule-3: knowledge_type={kt_lower} (outcome-class)",
            )
        )

    # Rule 4: Content pattern keywords.
    for kw in _PATTERN_KEYWORDS:
        if kw in content_lower:
            matches.append(
                (
                    Tier.PATTERN,
                    _CONFIDENCE_KEYWORD,
                    f"rule-4: content contains pattern-keyword '{kw}'",
                )
            )
            break  # one pattern-keyword match is sufficient for this rule

    # Rule 5: Content falsifiability keywords.
    for kw in _FALSIFIABILITY_KEYWORDS:
        if kw in content_lower:
            matches.append(
                (
                    Tier.FALSIFIABLE,
                    _CONFIDENCE_KEYWORD,
                    f"rule-5: content contains falsifiability-keyword '{kw}'",
                )
            )
            break  # one match suffices for this rule

    # Note: no "rule 6" default is added here — the caller handles
    # the empty-matches case explicitly. Adding a rule-6 OUTCOME
    # match here would make every classification report OUTCOME as
    # a matched rule, which defeats the contradiction-detection
    # logic.

    return matches


def _classify_magnitude(
    content_lower: str,
    explicit: ClaimMagnitude | None,
) -> tuple[ClaimMagnitude, str, float]:
    """Apply magnitude rules. Returns (magnitude, reason, confidence)."""
    if explicit is not None:
        return (
            explicit,
            f"explicit: caller passed {explicit.name}",
            _CONFIDENCE_EXPLICIT,
        )

    for kw in _TRIVIAL_KEYWORDS:
        if kw in content_lower:
            return (
                ClaimMagnitude.TRIVIAL,
                f"keyword '{kw}' -> TRIVIAL",
                _CONFIDENCE_KEYWORD,
            )

    for kw in _LOAD_BEARING_KEYWORDS:
        if kw in content_lower:
            return (
                ClaimMagnitude.LOAD_BEARING,
                f"keyword '{kw}' -> LOAD_BEARING",
                _CONFIDENCE_KEYWORD,
            )

    return (
        ClaimMagnitude.NORMAL,
        "default: no magnitude signal matched -> NORMAL",
        _CONFIDENCE_DEFAULT,
    )


__all__ = [
    "Classification",
    "classify_claim",
]
