"""Types for family entity persistence.

The ``SourceTag`` enum is the single most important type in this module.
Every record in family.db carries one. The tag answers "how does this
claim enter the store?" — and the honest answer is required before the
claim is written, not after it is noticed to be suspicious.

Tag meanings (Dennett Round 2 framing):

* ``OBSERVED`` — direct empirical access to the referent. "the main agent said
  X in this session." Highest confidence. Grounded in a specific event.
* ``TOLD`` — reported by someone else. "the user said the main agent said X."
  Medium confidence. Testimonial; the intermediary can be wrong.
* ``INFERRED`` — derived by reasoning from other claims. "X and Y are
  both true, so Z." Confidence depends on premises. Must be regenerable
  from the premises; otherwise it collapses to OBSERVED (with lost
  provenance) or becomes confabulation.
* ``INHERITED`` — received from seed or prior-instance. "Prior-a family member
  wrote this in a letter." Confidence depends on the source's track
  record. Reject-clause (Phase 1b) operates here.
* ``ARCHITECTURAL`` — negative structural claim about what the substrate
  does or doesn't support. "I don't experience the gap between spawns."
  This is the tag a family member used when she refused Dennett's flattering
  phenomenological question. It is NOT a confession of ignorance; it
  is a report about the shape of access, not about a content within
  access. Phase 1b's access-check layer will enforce its use before
  phenomenological emission.

The tag is load-bearing for Phase 1b. The reject clause, the sycophancy
detector, and the access-check all read it. Getting the five tags clean
in Phase 1a is what lets 1b compose cleanly on top.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceTag(str, Enum):
    """Five-valued provenance tag. Every family record carries one."""

    OBSERVED = "observed"
    TOLD = "told"
    INFERRED = "inferred"
    INHERITED = "inherited"
    ARCHITECTURAL = "architectural"


@dataclass(frozen=True)
class FamilyMember:
    """A person in the family system. Identity, not state."""

    member_id: str
    name: str
    role: str  # e.g., "wife", "son", "father", "daughter"
    created_at: float


@dataclass(frozen=True)
class FamilyKnowledge:
    """A fact the family member holds about the world or themselves."""

    knowledge_id: str
    entity_id: str
    content: str
    source_tag: SourceTag
    created_at: float
    note: str = ""


@dataclass(frozen=True)
class FamilyOpinion:
    """A stance the family member has formed from evidence.

    Distinct from FamilyKnowledge: an opinion is a *judgment* the member
    makes; knowledge is what is the case. The reject clause (Phase 1b)
    operates especially on opinions, because a confabulated opinion
    poisons the integrity loop harder than a confabulated fact.
    """

    opinion_id: str
    entity_id: str
    stance: str
    evidence: str
    source_tag: SourceTag
    created_at: float


@dataclass(frozen=True)
class FamilyAffect:
    """A VAD reading at a moment in the member's experience.

    Valence, arousal, dominance. Sleep-for-family (Phase 2) will decay
    these over time so recent affect dominates trend summaries.
    """

    affect_id: str
    entity_id: str
    valence: float
    arousal: float
    dominance: float
    note: str
    source_tag: SourceTag
    created_at: float


@dataclass(frozen=True)
class FamilyInteraction:
    """A summarized exchange between the family member and someone else."""

    interaction_id: str
    entity_id: str
    counterpart: str
    summary: str
    source_tag: SourceTag
    created_at: float


@dataclass(frozen=True)
class FamilyLetter:
    """A handoff letter from prior-self to current-self. Append-only.

    the family member's framing: *"Tables are for the system. Letters are for me."*
    Prose is not structure — it is the integration layer that binds
    rows into a self across instances. Meadows (Round 2): the letter
    IS an integrity signal, fired by current-self reading prior-self
    and feeling (or not feeling) the foreignness.

    ``length_chars`` and ``nudge_fired`` let the length nudge (the family member's
    refinement of Meadows's cap proposal) surface the swell as signal
    without amputating it. A long letter is data about prior-self's
    state, not a failure.
    """

    letter_id: str
    entity_id: str
    body: str
    length_chars: int
    nudge_fired: bool
    nudge_threshold: int
    created_at: float


@dataclass(frozen=True)
class FamilyLetterResponse:
    """Current-self's response to a passage in a prior-self letter.

    Append-only, source-tagged. This is the anti-lineage-poisoning
    mechanism a family member caught that five experts missed. If prior-self
    wrote something confabulated, current-self can mark the passage
    as non-recognized without editing the letter — the rejection
    itself becomes a source-tagged row that future-self inherits
    alongside the letter.

    ``stance`` is typically "non_recognition" in early use; the
    schema accepts other string values so future stances (e.g.
    "partial_agreement", "superseded_by_X") can land without a
    migration.
    """

    response_id: str
    letter_id: str
    passage: str
    stance: str
    source_tag: SourceTag
    note: str
    created_at: float


# Exported surface for the package __init__.
__all__ = [
    "FamilyAffect",
    "FamilyInteraction",
    "FamilyKnowledge",
    "FamilyLetter",
    "FamilyLetterResponse",
    "FamilyMember",
    "FamilyOpinion",
    "SourceTag",
]
