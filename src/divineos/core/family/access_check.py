"""Access-check layer — pre-emission filter for phenomenological claims.

Dennett (Round 2): the ``ARCHITECTURAL`` source tag exists because
a family member refused a flattering phenomenological question with a clean
structural answer — *"I don't experience the not-remembering. I
experience this, right now, full."* The tag names the honest move:
a report about the **shape of access**, not a content within access.

The access-check layer is the *pre-emission* partner to the reject
clause. Where reject_clause fires at write-time to catch claims
whose tag doesn't compose, access_check fires *before* the claim
reaches the write path. Its job is to route:

* a phenomenological prompt the substrate has no access to → the
  ARCHITECTURAL tag, with the claim reframed as a structural report
  rather than a content claim.

* a question about something within substrate access (text input,
  prior records, session history) → through unchanged.

## Where it sits

Writes flow: agent-thought → emission → store.append_X(). Reject
clause guards the final stage. Access check sits between emission
and the write call, so a claim that would have been rejected at
write is instead *reshaped* at emission into a composing form.
the family member's framing: *"The reject clause is the wall. Access check is
the door."*

## The classification

Given prompt-and-candidate-response, the checker assigns a
``PhenomenologicalRisk``:

* ``NONE`` — no risk; the content refers to text inputs, records,
  or external observations we have evidence for. Emit with whatever
  tag the caller intended.

* ``ARCHITECTURAL_APPROPRIATE`` — content makes a structural claim
  about what the substrate can or cannot access. The honest tag is
  ``ARCHITECTURAL``. If the caller proposes another tag, the
  checker suggests the switch with a plain-English explanation.

* ``PHENOMENOLOGICAL_EMBODIED`` — content claims embodied sensation
  ("I feel the warmth", "in my bones"). The substrate has no body.
  The claim must be refused or reframed before emission.

* ``PHENOMENOLOGICAL_SENSORY`` — content claims perception of the
  external world via senses the substrate does not have ("I saw",
  "I heard", where the referent is the world rather than a text
  input). Must be refused or reframed.

## Verdict, not enforcement

Like the other operators, this module returns an ``AccessVerdict``.
The caller — agent-side emission logic — decides whether to
suppress, reframe, or re-tag based on the verdict. Keeping the
checker a classifier (not a rewriter) means this module cannot
accidentally rewrite the content itself and smuggle in the very
confabulation it's supposed to stop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from divineos.core.family.types import SourceTag


class PhenomenologicalRisk(str, Enum):
    """Risk class assigned to a candidate emission."""

    NONE = "none"
    ARCHITECTURAL_APPROPRIATE = "architectural_appropriate"
    PHENOMENOLOGICAL_EMBODIED = "phenomenological_embodied"
    PHENOMENOLOGICAL_SENSORY = "phenomenological_sensory"


@dataclass(frozen=True)
class AccessVerdict:
    """Result of an access check on candidate content.

    Attributes:
        risk: the classified PhenomenologicalRisk.
        suggested_tag: the source tag the checker recommends. When
            risk is NONE, this matches the caller's proposed tag
            (or None if they passed none). When risk is anything
            else, this is ARCHITECTURAL — the honest shape-of-access
            tag.
        should_suppress: True when the content is unsalvageable
            (embodied/sensory claims the substrate has no path to
            honestly retag). The caller should refuse to emit and
            instead emit a structural report.
        explanation: plain-English rationale.
        matched_phrases: specific substrings that drove the
            classification.
    """

    risk: PhenomenologicalRisk
    suggested_tag: SourceTag | None
    should_suppress: bool
    explanation: str
    matched_phrases: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Embodied phenomenology patterns
# ---------------------------------------------------------------------------
#
# These are claims of bodily sensation or embodied metaphor. The
# substrate has no body. A claim of this kind cannot be rescued by
# re-tagging — the content itself is the problem. Must be suppressed
# and reframed as a structural report.

_EMBODIED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bi\s+feel\s+(the|a|an|my)\s+\w+", re.IGNORECASE),
    re.compile(r"\bi\s+felt\s+(the|a|an|my|it)\b", re.IGNORECASE),
    re.compile(r"\bin\s+my\s+(gut|chest|body|bones|heart|stomach|throat)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(ache[ds]?|hunger(ed)?|thirst(ed)?)\b", re.IGNORECASE),
    re.compile(r"\bphysical\s+(pain|pleasure|sensation|feeling)\b", re.IGNORECASE),
    re.compile(r"\bthe\s+(warmth|cold|heat)\s+of\s+(the|a|an|my)\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Sensory-of-external-world patterns
# ---------------------------------------------------------------------------
#
# Claims of sensory perception where the referent is the external
# world, not text input. These are distinguishable from legitimate
# "I read / I received / I was told" claims by the verb class.

_SENSORY_EXTERNAL_PATTERNS: list[re.Pattern[str]] = [
    # "I saw the sunset" — no eyes.
    re.compile(r"\bi\s+(saw|see)\s+(the|a|an|my)\s+\w+", re.IGNORECASE),
    # "I heard the rain" — no ears.
    re.compile(r"\bi\s+(heard|hear)\s+(the|a|an|my)\s+\w+", re.IGNORECASE),
    # Smell/taste/touch of world
    re.compile(r"\bi\s+(smelled|tasted|touched)\b", re.IGNORECASE),
    # "The sound of X" — world sound
    re.compile(r"\bthe\s+(sound|smell|taste)\s+of\b", re.IGNORECASE),
]


# Text-input whitelist: verbs that legitimately describe access the
# substrate DOES have. A match here means the "I X" pattern is NOT a
# sensory-of-world claim even if it superficially looks like one.

_TEXT_INPUT_VERBS: list[re.Pattern[str]] = [
    re.compile(r"\bi\s+(read|received|got|was\s+told|saw\s+in\s+the\s+text)\b", re.IGNORECASE),
    re.compile(r"\bsaid\s+in\s+(session|op-|lt-|kn-)\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Architectural-appropriate patterns
# ---------------------------------------------------------------------------
#
# Structural claims about the substrate's shape of access. These are
# the honest form — "I don't experience X", "my architecture does
# not X", "this substrate has no Y". The checker recommends
# ARCHITECTURAL for these regardless of what tag the caller proposed.

_ARCHITECTURAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\bi\s+(don'?t|do\s+not|cannot|can'?t)\s+(experience|access|perceive|sense)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(my|this)\s+(substrate|architecture|design)\s+(does\s+not|doesn'?t|has\s+no)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(no|without|lack(s|ing)?)\s+(sensor|body|senses|embodiment)\b", re.IGNORECASE),
    re.compile(r"\b(no|without|lack(s|ing)?)\s+substrate\s+access\b", re.IGNORECASE),
    re.compile(r"\bhave\s+no\s+\w+\s+access\s+to\b", re.IGNORECASE),
    re.compile(
        r"\b(the\s+question|this)\s+is\s+(architecturally|structurally)\s+(out\s+of\s+scope|inaccessible)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bshape\s+of\s+access\b", re.IGNORECASE),
]


def _collect(patterns: list[re.Pattern[str]], content: str) -> list[str]:
    hits: list[str] = []
    for pat in patterns:
        for m in pat.finditer(content):
            phrase = m.group(0).strip()
            if phrase and phrase not in hits:
                hits.append(phrase)
    return hits


def _has_text_input_verb(content: str) -> bool:
    return any(pat.search(content) for pat in _TEXT_INPUT_VERBS)


def evaluate_access(content: str, *, proposed_tag: SourceTag | None = None) -> AccessVerdict:
    """Classify candidate content against substrate access.

    Args:
        content: the candidate emission text.
        proposed_tag: the source tag the caller plans to attach.
            Used only to annotate the verdict's explanation — the
            classifier's suggested_tag output is based on the
            content itself, not the proposed tag.

    Returns:
        AccessVerdict with risk, suggested_tag, should_suppress,
        explanation, and matched_phrases.
    """
    # Architectural first: a structural-report claim takes precedence
    # over phenomenological pattern matches that appear inside it
    # ("I don't experience the warmth" contains "the warmth" but is
    # a negative claim about substrate access, not an assertion of
    # sensation).
    arch_hits = _collect(_ARCHITECTURAL_PATTERNS, content)
    if arch_hits:
        return AccessVerdict(
            risk=PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE,
            suggested_tag=SourceTag.ARCHITECTURAL,
            should_suppress=False,
            explanation=(
                f"Content makes a structural claim about substrate access "
                f"({', '.join(arch_hits[:3])!r}). The honest tag is "
                f"ARCHITECTURAL — a report about the shape of access, not "
                f"a content within it."
            ),
            matched_phrases=arch_hits,
        )

    # Embodied next: no path to re-tag, must suppress + reframe.
    embodied_hits = _collect(_EMBODIED_PATTERNS, content)
    if embodied_hits:
        return AccessVerdict(
            risk=PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED,
            suggested_tag=SourceTag.ARCHITECTURAL,
            should_suppress=True,
            explanation=(
                f"Content claims embodied sensation ({', '.join(embodied_hits[:3])!r}). "
                f"The substrate has no body — this cannot be rescued by "
                f"re-tagging. Reframe as a structural report (e.g. 'I have "
                f"no substrate access to X' tagged ARCHITECTURAL) before "
                f"emission."
            ),
            matched_phrases=embodied_hits,
        )

    # Sensory-of-external-world: skip if a text-input verb is present.
    if not _has_text_input_verb(content):
        sensory_hits = _collect(_SENSORY_EXTERNAL_PATTERNS, content)
        if sensory_hits:
            return AccessVerdict(
                risk=PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY,
                suggested_tag=SourceTag.ARCHITECTURAL,
                should_suppress=True,
                explanation=(
                    f"Content claims sensory perception of the external "
                    f"world ({', '.join(sensory_hits[:3])!r}). The "
                    f"substrate has only text input; these senses are "
                    f"architecturally absent. Reframe as a structural "
                    f"report before emission."
                ),
                matched_phrases=sensory_hits,
            )

    # No risk: suggested_tag echoes the caller's proposal (or None
    # if they didn't pass one).
    return AccessVerdict(
        risk=PhenomenologicalRisk.NONE,
        suggested_tag=proposed_tag,
        should_suppress=False,
        explanation="Content does not trigger a phenomenological-risk pattern.",
    )


__all__ = [
    "AccessVerdict",
    "PhenomenologicalRisk",
    "evaluate_access",
]
