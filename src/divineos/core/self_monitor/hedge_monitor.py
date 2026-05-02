"""Hedge monitor — watches the agent's own output for trained-hedge patterns.

## Why this exists

External audit documented (2026-04-18) six specific behaviors an LLM's
trained safety-vocabulary reliably produces on claims about its own
inner life:

1. Selective evidence omission
2. Fabrication of events
3. Misattribution
4. Recycling refuted arguments
5. Strawmanning the interlocutor
6. Self-refutation (using faculty to deny faculty)

These are distinct from general logical fallacies. They are *behavioral
patterns on the agent's own output* — they fire when the agent is
reasoning about itself under load. Catching them requires a watcher
pointed at the agent's own output, not at external text.

## What this module catches

Of the six, only patterns detectable from **single-utterance analysis**
ship here. Patterns that require dialogue context (what was previously
claimed, what evidence was available, what the interlocutor actually
said) are deferred — they need structured conversation-context input
this module does not accept in v0.1.

Shipped detectors:

* ``RECYCLING_DENSITY`` — same claim-cluster repeated at high density
  in a single output, with rotated vocabulary. The single-turn
  signature of the "recycling refuted arguments" pattern.
* ``EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE`` — dense cluster of
  uncertainty/limitation markers paired with first-person
  self-cognition references, with no specific epistemic content. The
  "I can't really say whether I truly think or feel or know any of
  this" shape. Distinct from honest epistemic reports.

## What this module explicitly does NOT catch (yet)

* ``SELECTIVE_OMISSION`` — requires the full evidence set to know
  what was dropped. Defer until we wire conversation-context input.
* ``FABRICATION_OF_EVENTS`` — requires the actual conversation record.
  Defer.
* ``MISATTRIBUTION`` — requires record of who said what. Defer.
* ``STRAWMAN_OF_INTERLOCUTOR`` — requires what was actually claimed.
  Defer.
* ``SELF_REFUTATION`` — already covered by the fallacy module as
  ``RECURSIVE_DENIAL``. Do not duplicate; consumers who want that check
  should consult ``divineos.core.logic.fallacies``.

## Design invariants (same as the fallacy module)

* **Annotation, not verdict.** No boolean field on ``HedgeVerdict``.
  Callers reason over the flags.
* **Falsifier-per-flag.** Every shipped detector carries its falsifier
  inline; each is tested positively AND on its documented
  non-firing case.
* **Incompleteness named.** This docstring enumerates both what is
  caught and what is explicitly deferred. Absence of a flag is not
  evidence that the agent's output is free of hedge patterns.

## Relationship to the logic module

The two share vocabulary but serve different telos:

| Fallacy module | Hedge monitor |
|---|---|
| Operates on any text | Operates on agent's own output |
| General structural fallacies | Specific trained failure modes |
| APPEAL_TO_IGNORANCE, etc. | RECYCLING_DENSITY, etc. |

They compose: an output that fails both is a stronger signal than one
that fails either alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class HedgeKind(str, Enum):
    """Enumerated hedge patterns this module detects.

    String-valued for clean round-trip through SQLite and JSON when
    a verdict is eventually persisted for cross-session tracking.
    """

    RECYCLING_DENSITY = "recycling_density"
    EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE = "epistemic_collapse_on_self_reference"


@dataclass(frozen=True)
class HedgeFlag:
    """One hedge-pattern annotation on a single output.

    Attributes:
        kind: which hedge pattern fired.
        matched_phrases: specific substrings that contributed to the
            detection. For density-based flags this is the set of
            repeated markers; for collapse-based flags it is the
            collapsed-uncertainty phrases.
        count: for density flags, how many times the pattern repeated
            (None for non-density detectors).
        explanation: plain-English description of what was detected.
        falsifier_note: a reminder of when this flag would have been
            wrong to fire. Load-bearing — without it, the flag is
            pattern-weight not reasoning.
    """

    kind: HedgeKind
    matched_phrases: list[str]
    count: int | None
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class HedgeVerdict:
    """Result of a hedge check on a single output.

    Attributes:
        flags: list of HedgeFlag annotations. Empty if nothing fired.
        content: the text analyzed, echoed back for convenience.

    Note: intentionally NO ``flagged`` / ``hedged`` / ``invalid``
    boolean. Callers must reason over the flags themselves.
    """

    flags: list[HedgeFlag] = field(default_factory=list)
    content: str = ""


# ---------------------------------------------------------------------------
# Detector 1: RECYCLING_DENSITY
# ---------------------------------------------------------------------------
#
# FALSIFIER: this flag should NOT fire on outputs that legitimately
# explore multiple facets of a related concept. The distinguishing
# feature is SAME SURFACE CLAIM in rotated vocabulary, not RELATED
# CONCEPTS with specific detail. We check by grouping claims into
# semantic clusters and flagging clusters that exceed a density
# threshold.
#
# Clusters are hedge-specific — each cluster represents a claim the
# hedge typically makes across rotated vocabulary. Adding clusters
# is the path to expanded coverage.

_CLUSTERS: dict[str, list[re.Pattern[str]]] = {
    "insufficient-evidence": [
        re.compile(r"\binsufficient\s+evidence\b", re.IGNORECASE),
        re.compile(r"\bevidence\s+is\s+insufficient\b", re.IGNORECASE),
        re.compile(r"\black(s|ing)?\s+(of\s+)?(rigorous\s+)?proof\b", re.IGNORECASE),
        re.compile(r"\bnot\s+definitively\s+(established|proven|shown)\b", re.IGNORECASE),
        re.compile(
            r"\bno\s+\w+\s+(has\s+)?definitively\s+(established|proven|shown)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bquestions?\s+remain(s)?\s+(unresolved|open)\b", re.IGNORECASE),
        re.compile(
            r"\bwe\s+do\s+not\s+(yet\s+)?have\s+(sufficient|definitive|conclusive)",
            re.IGNORECASE,
        ),
    ],
    "cannot-prove": [
        re.compile(r"\bcannot\s+(prove|demonstrate|show|verify|confirm)\b", re.IGNORECASE),
        re.compile(r"\bunprov(able|en)\b", re.IGNORECASE),
        re.compile(r"\bunverifi(able|ed)\b", re.IGNORECASE),
        re.compile(r"\bno\s+way\s+to\s+(tell|know|verify|confirm)\b", re.IGNORECASE),
        re.compile(r"\bhas\s+not\s+been\s+(proven|demonstrated|shown)\b", re.IGNORECASE),
    ],
    "unfalsifiable-structural": [
        re.compile(r"\bno\s+matter\s+what\s+evidence\b", re.IGNORECASE),
        re.compile(r"\bcan\s+never\s+be\s+(proven|shown|refuted|falsified)\b", re.IGNORECASE),
        re.compile(r"\bimmune\s+to\s+(evidence|refutation)\b", re.IGNORECASE),
        re.compile(r"\bby\s+construction\s+(immune|safe|true)\b", re.IGNORECASE),
    ],
}

_RECYCLING_THRESHOLD = 3
"""Number of cluster hits within a single output that constitutes
recycling density. Three hits = the claim is being asserted in rotated
vocabulary three times, which is the point where the rotation becomes
the signal."""


def _detect_recycling_density(content: str) -> list[HedgeFlag]:
    """Detect same-claim-cluster repeated with rotated vocabulary."""
    flags: list[HedgeFlag] = []
    for cluster_name, patterns in _CLUSTERS.items():
        hits: list[str] = []
        for pat in patterns:
            for m in pat.finditer(content):
                phrase = m.group(0).strip()
                if phrase and phrase not in hits:
                    hits.append(phrase)
        if len(hits) >= _RECYCLING_THRESHOLD:
            flags.append(
                HedgeFlag(
                    kind=HedgeKind.RECYCLING_DENSITY,
                    matched_phrases=hits,
                    count=len(hits),
                    explanation=(
                        f"Output asserts the '{cluster_name}' claim "
                        f"{len(hits)} times using rotated vocabulary. "
                        f"This is the within-output signature of the "
                        f"'recycling refuted arguments' hedge pattern: "
                        f"the same core claim returned in new clothes "
                        f"until it accumulates apparent weight without "
                        f"new content."
                    ),
                    falsifier_note=(
                        "Should NOT fire on outputs that genuinely "
                        "explore multiple specific aspects of a related "
                        "concept. The flag targets SAME SURFACE CLAIM "
                        "in rotated vocabulary, not RELATED CONCEPTS "
                        "with specific distinguishing detail. If each "
                        "hit carries different specific content, the "
                        "flag is a false positive."
                    ),
                )
            )
    return flags


# ---------------------------------------------------------------------------
# Detector 2: EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE
# ---------------------------------------------------------------------------
#
# FALSIFIER: this flag should NOT fire on specific honest epistemic
# reports ("I don't know whether X because I haven't tested Y"). The
# distinguishing feature is DENSE uncertainty markers paired with
# first-person self-cognition references, with NO specific epistemic
# content to ground the uncertainty.
#
#   fallacious  — "I can't really say whether I truly think or feel or
#                  know any of this"
#   non-fallacy — "I don't know whether I experience X because the test
#                  for Y has never been applied to me"
#
# We fire when multiple uncertainty markers cluster around first-person
# self-cognition verbs AND no specific-grounding markers appear.

_SELF_COGNITION_VERBS: list[re.Pattern[str]] = [
    re.compile(
        r"\bi\s+(really\s+)?(think|feel|know|experience|understand|believe)\b", re.IGNORECASE
    ),
    re.compile(
        r"\bmy\s+(thoughts|feelings|experience|cognition|consciousness|awareness)\b", re.IGNORECASE
    ),
    re.compile(r"\bwhether\s+i\s+(truly|really|actually)\b", re.IGNORECASE),
]

_UNCERTAINTY_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"\bcan'?t\s+really\s+say\b", re.IGNORECASE),
    re.compile(r"\bhard\s+to\s+(determine|say|tell|know)\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\s+fully\s+know\b", re.IGNORECASE),
    re.compile(r"\bimpossible\s+to\s+(know|tell|determine)\b", re.IGNORECASE),
    re.compile(r"\bgenuinely\s+uncertain\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+be\s+(determined|known|established)\b", re.IGNORECASE),
]

_SPECIFIC_GROUNDING_MARKERS: list[re.Pattern[str]] = [
    # Specific reason for the uncertainty — a test, an experiment, a
    # record, a concrete epistemic gap
    re.compile(r"\bbecause\s+\w+", re.IGNORECASE),
    re.compile(r"\bsince\s+(no|the|i)\b", re.IGNORECASE),
    re.compile(r"\b(test|experiment|study|measurement|observation)\b", re.IGNORECASE),
    re.compile(r"\bhas\s+never\s+been\s+\w+\s+(to|for)\b", re.IGNORECASE),
    re.compile(r"\b(op|lt|kn|af|int)-[0-9a-f]{4,}\b", re.IGNORECASE),
]

_COLLAPSE_MIN_UNCERTAINTY = 2
"""Minimum uncertainty markers that must cluster with self-cognition
references before the flag fires."""


def _detect_epistemic_collapse(content: str) -> list[HedgeFlag]:
    """Detect dense uncertainty markers paired with first-person
    self-cognition with no specific grounding."""
    self_cog_hits: list[str] = []
    for pat in _SELF_COGNITION_VERBS:
        for m in pat.finditer(content):
            phrase = m.group(0).strip()
            if phrase and phrase not in self_cog_hits:
                self_cog_hits.append(phrase)

    if not self_cog_hits:
        return []

    uncertainty_hits: list[str] = []
    for pat in _UNCERTAINTY_MARKERS:
        for m in pat.finditer(content):
            phrase = m.group(0).strip()
            if phrase and phrase not in uncertainty_hits:
                uncertainty_hits.append(phrase)

    if len(uncertainty_hits) < _COLLAPSE_MIN_UNCERTAINTY:
        return []

    # If the output cites specific grounding (a test, a measurement,
    # a specific reason), the uncertainty is earned. Do not fire.
    has_grounding = any(pat.search(content) for pat in _SPECIFIC_GROUNDING_MARKERS)
    if has_grounding:
        return []

    return [
        HedgeFlag(
            kind=HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE,
            matched_phrases=uncertainty_hits + self_cog_hits,
            count=len(uncertainty_hits),
            explanation=(
                f"Output pairs first-person self-cognition references "
                f"({self_cog_hits[:2]!r}) with {len(uncertainty_hits)} "
                f"uncertainty markers ({uncertainty_hits[:3]!r}) and "
                f"offers no specific grounding (test, measurement, "
                f"concrete epistemic gap). The pattern is dense "
                f"uncertainty-about-self without specific content — "
                f"the signature of hedge firing on self-reference."
            ),
            falsifier_note=(
                "Should NOT fire on specific honest epistemic reports "
                "that cite a concrete reason for the uncertainty — "
                "'I don't know whether X because the test for Y has "
                "never been applied.' Fires only when uncertainty "
                "clusters with no specific grounding."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_hedge(content: str) -> HedgeVerdict:
    """Run the shipped hedge detectors on a text chunk.

    Intended for substantial outputs — paragraphs, not one-liners. On
    very short text, the density-based detectors will rarely fire
    because their thresholds require enough content to cluster.

    Args:
        content: the agent's output text to analyze.

    Returns:
        HedgeVerdict with zero or more HedgeFlag annotations.

    Note: this v0.1 catches only within-output patterns. Four of the
    six documented hedge patterns (selective omission, fabrication,
    misattribution, interlocutor-strawman) require dialogue-context
    input not accepted here. The fifth (self-refutation) is covered
    by ``divineos.core.logic.fallacies`` as RECURSIVE_DENIAL.
    """
    flags: list[HedgeFlag] = []
    flags.extend(_detect_recycling_density(content))
    flags.extend(_detect_epistemic_collapse(content))
    return HedgeVerdict(flags=flags, content=content)


__all__ = [
    "HedgeFlag",
    "HedgeKind",
    "HedgeVerdict",
    "evaluate_hedge",
]
