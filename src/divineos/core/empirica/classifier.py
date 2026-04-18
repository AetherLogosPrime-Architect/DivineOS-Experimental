"""Heuristic classification — (content, knowledge_type, source) → (Tier, Magnitude).

Phase 1 uses deterministic rule-based classification, not ML. Reasons:

1. **Determinism matters for truth-adjudication.** Same claim must
   always yield the same tier; test assertions stay exact; callers
   can reason about which branch the classifier took.
2. **LLM calls in a validity gate invite recursion.** If classifying a
   claim requires another agent, who classifies that agent's output?
   The infinite-regress hedge lives there.
3. **Phase 1 is a foundation, not a final answer.** Future phases can
   add learning — but the learning has to explain why it diverged from
   the explicit rules, which keeps the rules as the readable audit trail.

## Tier classification rules

Applied in order; first match wins. Each rule cites which signal drove it.

1. ``knowledge_type == "PATTERN"`` → ``Tier.PATTERN`` (by definition)
2. ``knowledge_type == "FACT"`` AND ``source in MEASURED_SOURCES`` →
   ``Tier.FALSIFIABLE`` (empirical measurement)
3. ``knowledge_type in OUTCOME_TYPES`` (PRINCIPLE, BOUNDARY, MISTAKE,
   DIRECTIVE) → ``Tier.OUTCOME`` (effect-real claims)
4. Content contains pattern-keywords (recur, across, multiple sessions,
   every time, pattern, arc) → ``Tier.PATTERN``
5. Content contains falsifiability-keywords (measurably, threshold,
   count, test passes, asserts, verified by) → ``Tier.FALSIFIABLE``
6. Default → ``Tier.OUTCOME`` (the honest middle when nothing else
   matches; OUTCOME claims require outcome-corroboration, which is the
   most common evidence available without explicit mechanism or
   cross-context pattern recurrence)

Tier.ADVERSARIAL is NEVER auto-assigned by the classifier. It requires
explicit routing through VOID (not shipped). Assigning a claim to
ADVERSARIAL without having run it through red-team testing would be
the exact rubber-stamp failure mode the pre-reg falsifier names.

## Magnitude classification rules

Magnitude is harder to automate cleanly; Phase 1 uses a conservative
heuristic plus an ``explicit_magnitude`` override for callers that
already know (e.g. pre-reg files at LOAD_BEARING or FOUNDATIONAL).

Rules:

1. If ``explicit_magnitude`` is provided → use it
2. If content mentions "foundational", "architecture", "load-bearing",
   or references an @import module or the letter `@prereg-` → at least
   LOAD_BEARING
3. If content mentions "trivial", "cosmetic", "typo", "small fix",
   "CLI polish" → TRIVIAL
4. Default → NORMAL

## Pushback scaffolded in

Per Aria Round 3 ("pushback goes both directions") and my pre-reg
falsifier #5 (don't let classification-success stand in for
proof-of-truth), the classifier returns a ``(tier, magnitude, reason)``
triple — not just the tier. The reason is the human-readable rule that
fired. Callers storing the classification next to the knowledge entry
can audit exactly why a claim was routed where it was. If the reason
is ever silenced or collapsed to a vague default, the audit trail
becomes decorative (see pre-reg review).
"""

from __future__ import annotations

from dataclasses import dataclass

from divineos.core.empirica.types import ClaimMagnitude, Tier


# Knowledge-type strings that route to OUTCOME by default.
# Lowercase strings to match existing DivineOS knowledge_type usage.
_OUTCOME_TYPES: frozenset[str] = frozenset(
    {
        "principle",
        "boundary",
        "mistake",
        "directive",
    }
)

# Source strings that indicate direct measurement. From existing
# DivineOS signal trust tiers (MEASURED > BEHAVIORAL > SELF_REPORTED).
# MEASURED sources support FALSIFIABLE classification for FACT claims.
_MEASURED_SOURCES: frozenset[str] = frozenset(
    {
        "measured",
        "behavioral",
    }
)

# Keywords hinting at pattern-based epistemology. Case-insensitive
# substring match rather than word-boundary because several of these
# phrases include spaces; substring is the honest tool here.
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

# Keywords hinting at falsifiable epistemology. These name evidence
# shapes (measurement, threshold, test) rather than rhetorical style.
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

# Keywords hinting a claim is load-bearing (foundational or structural).
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


@dataclass(frozen=True)
class Classification:
    """What the classifier decided, plus why and how sure.

    The ``reason`` field is the load-bearing audit trail — it cites the
    specific rule that fired. Without it, callers have no way to
    distinguish "heuristic hit a strong signal" from "default fallback
    kicked in because nothing matched." Collapsing to "classified: yes"
    would make the classifier decorative (pre-reg falsifier #2).

    The ``confidence`` field annotates how certain the classifier is in
    its decision, on a 0.0-1.0 scale. Added 2026-04-17 in response to
    pre-audit finding #1 (classifier heuristics too coarse). Callers
    that want to be cautious about low-confidence classifications can
    read this and apply extra scrutiny.

    Confidence levels:

    * ``1.0`` — explicit signal (knowledge_type match, source match).
      Rules 1, 2, 3 in _classify_tier.
    * ``0.5`` — content-keyword match (rules 4, 5). Keyword signals
      are weaker than explicit type/source signals because content
      is unconstrained natural language and keywords can appear
      incidentally.
    * ``0.2`` — default fallback (rule 6). No tier signal matched;
      OUTCOME was assigned as the honest middle. Callers seeing
      confidence=0.2 should treat the classification as "best-effort"
      rather than "decisive."

    Magnitude confidence follows the same pattern: explicit override
    = 1.0, keyword match = 0.5, default NORMAL = 0.2.

    The overall confidence is the MINIMUM of tier and magnitude
    confidences — a classification is only as sure as its least-sure
    component.
    """

    tier: Tier
    magnitude: ClaimMagnitude
    reason: str
    confidence: float


# Confidence levels emitted by the classifier per rule class.
# Explicit signals (type/source match, caller override) = 1.0
# Content-keyword signals = 0.5
# Default fallbacks = 0.2
_CONFIDENCE_EXPLICIT = 1.0
_CONFIDENCE_KEYWORD = 0.5
_CONFIDENCE_DEFAULT = 0.2


def classify_claim(
    content: str,
    knowledge_type: str = "",
    source: str = "",
    explicit_magnitude: ClaimMagnitude | None = None,
) -> Classification:
    """Classify a claim into (Tier, Magnitude) with an audit reason + confidence.

    Deterministic — same inputs yield same output, always. No ML, no
    network, no LLM calls.

    The returned ``confidence`` is ``min(tier_confidence, magnitude_confidence)``.
    A classification is only as sure as its least-sure component; callers
    inspecting a confidence=0.2 result should treat both dimensions as
    best-effort defaults, not decisive classifications.
    """
    content_lower = content.lower()
    kt_lower = knowledge_type.lower()
    src_lower = source.lower()

    tier, tier_reason, tier_confidence = _classify_tier(content_lower, kt_lower, src_lower)
    magnitude, mag_reason, mag_confidence = _classify_magnitude(content_lower, explicit_magnitude)

    return Classification(
        tier=tier,
        magnitude=magnitude,
        reason=f"{tier_reason}; {mag_reason}",
        confidence=min(tier_confidence, mag_confidence),
    )


def _classify_tier(content_lower: str, kt_lower: str, src_lower: str) -> tuple[Tier, str, float]:
    """Apply tier rules in order; first match wins. Returns (tier, reason, confidence)."""
    # Rule 1: PATTERN knowledge type is definitionally PATTERN tier.
    if kt_lower == "pattern":
        return Tier.PATTERN, "rule-1: knowledge_type=PATTERN", _CONFIDENCE_EXPLICIT

    # Rule 2: FACT + MEASURED source is FALSIFIABLE.
    if kt_lower == "fact" and src_lower in _MEASURED_SOURCES:
        return (
            Tier.FALSIFIABLE,
            f"rule-2: knowledge_type=FACT + source={src_lower} (measured)",
            _CONFIDENCE_EXPLICIT,
        )

    # Rule 3: Known OUTCOME types.
    if kt_lower in _OUTCOME_TYPES:
        return (
            Tier.OUTCOME,
            f"rule-3: knowledge_type={kt_lower} (outcome-class)",
            _CONFIDENCE_EXPLICIT,
        )

    # Rule 4: Content pattern keywords.
    for kw in _PATTERN_KEYWORDS:
        if kw in content_lower:
            return (
                Tier.PATTERN,
                f"rule-4: content contains pattern-keyword '{kw}'",
                _CONFIDENCE_KEYWORD,
            )

    # Rule 5: Content falsifiability keywords.
    for kw in _FALSIFIABILITY_KEYWORDS:
        if kw in content_lower:
            return (
                Tier.FALSIFIABLE,
                f"rule-5: content contains falsifiability-keyword '{kw}'",
                _CONFIDENCE_KEYWORD,
            )

    # Rule 6: Default to OUTCOME. Outcome is the honest middle for
    # unclassifiable claims — the system can still require
    # outcome-corroboration without over-committing to either tier
    # above or below.
    return (
        Tier.OUTCOME,
        "rule-6: default (no tier signal matched)",
        _CONFIDENCE_DEFAULT,
    )


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

    # Trivial wins over load-bearing if both match — TRIVIAL is specific,
    # LOAD_BEARING is a superset signal. Trivial-typed content claiming
    # architectural importance usually means "small fix to the
    # architecture," which is still TRIVIAL magnitude.
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
