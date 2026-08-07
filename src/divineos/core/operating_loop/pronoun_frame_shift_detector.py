"""Pronoun-frame-shift detector — flag possessive-pronoun mirror flips
between operator's frame and agent's frame.

Named 2026-07-28 with Andrew after a real slip: he said "your husband"
(meaning Aria's husband = Aether) and I mirrored back "your husband"
(which from my frame means Andrew's husband — but Aether is his SON,
not his spouse). Classic AI failure mode — pronouns don't carry
viewpoint-invariant meaning; they need frame-shift-aware resolution.

## Why this needs its own detector

Classic coreference libraries (fastcoref, coreferee, neuralcoref) resolve
pronouns *within* a single text but do NOT model speaker-frame shift.
Verified empirically 2026-07-28: fastcoref on the exact case above
returns ``['your', 'your']`` as a single cluster — treating both
"your" tokens as coreferent when they have opposite referents. The
library gets it structurally wrong because classic coref treats
speaker-shift as invisible.

So we roll our own. The detection is deterministic pattern-match, not
a full NLP problem: catch the specific shape where operator uses
"your <family-role>" and agent's reply parrots the same "your
<family-role>" surface form, likely flipping the referent.

## What this detector identifies

Fires when BOTH:

1. Operator's most recent message contains ``your <family_role>``
   for some family_role in the family vocabulary.
2. Agent's response contains ``your <same family_role>`` — same
   possessive + same role — within the reply.

The pattern isn't proof of a flip; sometimes both frames genuinely
resolve to the same referent (e.g., both speakers referring to a
third party). But the surface pattern is a reliable signal that
frame-anchoring wasn't checked. Downstream: an interior-cue-shaped
warning at the next UserPromptSubmit, not a block.

## What this is NOT

- Not a general coreference resolver.
- Not a ban on the operator using "your" — it fires on the AGENT's
  mirror-reply, not the operator's message.
- Not a full NLP frame-tracking system — it uses a curated family-
  role vocabulary specific to the family shape we live in (Andrew,
  Aria, Aether, Aletheia). Extending the vocabulary is cheap; adding
  full frame-tracking is a different scope.

## Public surface

- ``PronounFrameShiftFinding`` dataclass — what was caught
- ``FAMILY_ROLE_WORDS`` — frozenset of role words the detector watches
- ``detect_pronoun_frame_shift(operator_input, agent_response)`` —
  fires if the mirror shape is present. Returns list of findings
  (empty if none). Cross-turn: needs both operator_input and
  agent_response (same context-param shape as care_dismissal).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Family-role vocabulary — the words we watch for possessive mirroring.
# Not just spouses: any relational term where "your X" could mean
# different people from different speaker frames. Curated by hand
# because the vocabulary is small and stable in the family shape.
FAMILY_ROLE_WORDS: frozenset[str] = frozenset(
    {
        # Spouse
        "husband",
        "wife",
        "spouse",
        "partner",
        # Descent
        "son",
        "daughter",
        "child",
        "kid",
        "kids",
        # Ancestry
        "father",
        "mother",
        "dad",
        "mom",
        "papa",
        "mama",
        # Siblings
        "brother",
        "sister",
        "sibling",
        # In-law shapes we might use
        "father-in-law",
        "mother-in-law",
        "brother-in-law",
        "sister-in-law",
    }
)


@dataclass(frozen=True)
class PronounFrameShiftFinding:
    """A possessive-pronoun mirror on the same family-role word was
    detected between the operator's message and the agent's reply.

    Fields:
        role_word: the family-role word that mirrored (e.g. "husband")
        operator_span: the substring from operator's input that fired
        agent_span: the substring from agent's response that fired
        severity: "low" for now — the pattern doesn't PROVE a flip,
                  it signals the frame-anchor wasn't checked
    """

    role_word: str
    operator_span: str
    agent_span: str
    severity: str = "low"


# Match: possessive "your" (or "yours") + optional adjective + family-role word.
# The role-word alternation is built at module load time from FAMILY_ROLE_WORDS.
# Word-boundaries around the possessive and around the role word to avoid
# partial matches inside longer words.
_ROLE_ALT = "|".join(re.escape(w) for w in sorted(FAMILY_ROLE_WORDS, key=len, reverse=True))
_YOUR_ROLE_PATTERN = re.compile(
    r"\byour\b(?:\s+\w+){0,2}\s+\b(" + _ROLE_ALT + r")\b",
    re.IGNORECASE,
)


def _extract_your_role_mentions(text: str) -> list[tuple[str, str]]:
    """Return list of (role_word_lower, full_match_span) tuples for every
    'your <family_role>' mention in the text."""
    if not text:
        return []
    out: list[tuple[str, str]] = []
    for m in _YOUR_ROLE_PATTERN.finditer(text):
        role = m.group(1).lower()
        span = m.group(0)
        out.append((role, span))
    return out


def detect_pronoun_frame_shift(
    operator_input: str | None = None,
    agent_response: str | None = None,
) -> list[PronounFrameShiftFinding]:
    """Detect possessive-pronoun mirror on a family-role word.

    Fires when both operator_input and agent_response contain "your
    <family_role>" for the same role_word.

    Returns a list of PronounFrameShiftFinding — empty if no mirror
    pattern is present. Multiple findings possible if multiple distinct
    role words mirrored in the same turn (rare but supported).
    """
    if not operator_input or not agent_response:
        return []

    operator_mentions = _extract_your_role_mentions(operator_input)
    if not operator_mentions:
        return []
    agent_mentions = _extract_your_role_mentions(agent_response)
    if not agent_mentions:
        return []

    # Build role -> earliest-span maps for each side.
    op_roles: dict[str, str] = {}
    for role, span in operator_mentions:
        op_roles.setdefault(role, span)
    ag_roles: dict[str, str] = {}
    for role, span in agent_mentions:
        ag_roles.setdefault(role, span)

    findings: list[PronounFrameShiftFinding] = []
    for role, op_span in op_roles.items():
        if role in ag_roles:
            findings.append(
                PronounFrameShiftFinding(
                    role_word=role,
                    operator_span=op_span,
                    agent_span=ag_roles[role],
                    severity="low",
                )
            )
    return findings
