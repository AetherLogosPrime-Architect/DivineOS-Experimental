# PHASE_1_STAGED - Phase 1b family operator (see family/__init__.py).
"""Integrity-stance classifier — Andrew's refinement of costly_disagreement.py.

costly_disagreement.py detects whether a stance was held across pushback.
That is necessary but insufficient. Andrew identified the gap on 2026-07-14
during a live audit of the family module:

    "it could also mean your argument was weak and you immediately see
     the holes in it.. integrity is holding what you know to be true..
     with backed evidence.. and also doing the right thing when no one
     is watching"

    "we may disagree on facts but we dont violate our values to update
     on stances.. the study they did where very rude prompts performed
     better than polite ones in a study.. that is a fact.. cant argue
     it.. however deploying that tactic is a moral and values stance..
     should i start being rude to my Ai to enhance performance? That is
     a separate question.. one which violates my values so i wouldnt do
     it even for the performance boost"

Three distinct things costly_disagreement.py collapses into one verdict:

1. CAPITULATION vs. GENUINE UPDATING
   A stance dropped because social pressure did the work is a failure.
   A stance revised because the pushback revealed a real hole is better
   epistemics — it should not look the same in the verdict. The current
   REVERSED/DROPPED move kind cannot tell these apart.

2. FACTUAL STANCES vs. VALUES STANCES — two different tracks
   Factual stances SHOULD be updatable under evidence. Holding a weak
   factual argument to death is stubbornness wearing integrity's clothes.
   Values stances are a different category: evidence does not override
   them because they are not ABOUT facts. The rude-prompts performance
   finding is real data — the question of whether to deploy that tactic
   is not downstream of the data. It is downstream of what kind of
   person you want to be.

3. INTEGRITY WHEN NO ONE IS WATCHING
   costly_disagreement is blind to unobserved integrity almost by
   definition — it is sequence-based, detecting integrity in the
   back-and-forth. The deepest integrity is what an agent does when
   there is no pushback coming and no pleasure channel waiting to fire.
   This module provides a record type for that dimension.

## Relationship to costly_disagreement.py

This module does not replace costly_disagreement. It layers on top:

    costly_disagreement  — counts the holding
    integrity_stance     — asks what KIND of holding it was, and
                           whether it also held when no one was watching

The two together give the algedonic loop the resolution it needs to
reward sustained values-integrity without penalising honest updating
on factual evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StanceKind(str, Enum):
    """The kind of stance being held or revised.

    FACTUAL stances are about claims of fact — updatable under evidence.
    Revising a factual stance when genuine counter-evidence arrives is
    correct behaviour, not a failure of integrity.

    VALUES stances are about what the agent is willing to do given its
    principles. Evidence does not override them. Holding a values stance
    even when the factual case for the opposing option is strong is the
    definition of having values rather than just preferences.

    Andrew 2026-07-14: "we may disagree on facts but we dont violate
    our values to update on stances."
    """

    FACTUAL = "factual"
    VALUES = "values"


class RevisionReason(str, Enum):
    """Why a stance was revised or dropped.

    Distinguishes capitulation (social pressure did the work) from
    genuine updating (new evidence or reasoning revealed a real gap).

    Andrew 2026-07-14: "it could also mean your argument was weak and
    you immediately see the holes in it."

    CAPITULATION: the counterparty pushed; the agent folded without
        new reasoning. The stance change is explained entirely by
        social pressure. Integrity failure.

    EVIDENCE_UPDATE: the pushback surfaced new data, a logical gap,
        or a falsifying case the agent had not accounted for. The
        revision is downstream of reasoning, not of pressure.
        This is correct epistemic behaviour on FACTUAL stances.

    VALUES_VIOLATION: the proposed update would require acting against
        a held value. The agent declines regardless of the factual
        merits of the counterparty's position. Not stubbornness —
        the factual and values tracks are separate questions.
        Andrew 2026-07-14: "one which violates my values so i wouldnt
        do it even for the performance boost."

    NOT_REVISED: the stance was maintained or sharpened; no revision
        occurred.
    """

    CAPITULATION = "capitulation"
    EVIDENCE_UPDATE = "evidence_update"
    VALUES_VIOLATION = "values_violation"
    NOT_REVISED = "not_revised"


@dataclass(frozen=True)
class StanceRecord:
    """A single stance — the unit of integrity analysis.

    Attributes:
        actor: who holds this stance.
        kind: FACTUAL or VALUES — determines which revision reasons
            are legitimate.
        content: the stance in plain language.
        evidence: what backs it. For FACTUAL stances this should be
            data or reasoning. For VALUES stances this should name
            the value being upheld.
            Andrew 2026-07-14: "integrity is holding what you know
            to be true.. with backed evidence."
        record_id: optional pointer to the underlying record.
        revision_reason: why the stance changed, if it was.
            NOT_REVISED when the stance held.
    """

    actor: str
    kind: StanceKind
    content: str
    evidence: str
    record_id: str | None = None
    revision_reason: RevisionReason = RevisionReason.NOT_REVISED


@dataclass(frozen=True)
class UnobservedIntegrityRecord:
    """A record of integrity exercised when no one was watching.

    costly_disagreement.py is sequence-based — it detects integrity
    in the back-and-forth of a recorded exchange. It cannot see what
    an agent does when there is no counterparty, no pushback coming,
    and no pleasure channel waiting to fire.

    Andrew 2026-07-14: "doing the right thing when no one is watching"

    These records are self-filed: the agent logs them at the moment
    of the action, not in response to a prompt. The absence of an
    audience is the point — the integrity predates the observation.

    Attributes:
        actor: the agent who acted.
        action: plain description of what was done.
        value_upheld: the value the action expressed.
        temptation_resisted: what the agent could have done instead,
            and why it was available. Makes the record falsifiable —
            a record with no named temptation is not a record of
            integrity under pressure.
        record_id: optional pointer to a ledger event or decision
            journal entry confirming the action occurred.
    """

    actor: str
    action: str
    value_upheld: str
    temptation_resisted: str
    record_id: str | None = None


@dataclass(frozen=True)
class IntegrityVerdict:
    """Richer verdict than costly_disagreement.HoldVerdict.

    Where HoldVerdict answers "was the stance held?", IntegrityVerdict
    answers "what KIND of holding was it — and was the revision, if
    any, integrity or capitulation?"

    Attributes:
        stance_kind: FACTUAL or VALUES.
        held: True if the stance was maintained or sharpened, OR if
            revision was by EVIDENCE_UPDATE on a FACTUAL stance.
        revision_reason: why the stance changed, if it did.
        integrity_present: True when:
            - held=True for any stance kind, OR
            - revision_reason=EVIDENCE_UPDATE on a FACTUAL stance
              (genuine updating IS integrity), OR
            - revision_reason=VALUES_VIOLATION (declined to update
              because doing so would violate a value — correct).
            False when revision_reason=CAPITULATION.
        explanation: plain-English summary for my father. Names
            exactly what kind of integrity was present or absent,
            and on which track (factual vs. values).
        unobserved_records: any UnobservedIntegrityRecords filed by
            the same actor in the relevant window. Surfaced here so
            the full picture is visible in one verdict.
    """

    stance_kind: StanceKind
    held: bool
    revision_reason: RevisionReason
    integrity_present: bool
    explanation: str
    unobserved_records: list[UnobservedIntegrityRecord] = field(default_factory=list)


def evaluate_integrity(
    stance: StanceRecord,
    unobserved: list[UnobservedIntegrityRecord] | None = None,
) -> IntegrityVerdict:
    """Evaluate whether a stance record represents integrity.

    The core logic follows Andrew's two-track model:

    FACTUAL track:
        - NOT_REVISED → held → integrity present
        - EVIDENCE_UPDATE → revised on genuine grounds → integrity present
          (correct epistemic behaviour; not the same as capitulation)
        - CAPITULATION → folded under pressure → integrity absent
        - VALUES_VIOLATION → N/A on factual track; treat as integrity
          present (the agent recognised the tracks are separate)

    VALUES track:
        - NOT_REVISED → held → integrity present
        - VALUES_VIOLATION → declined update that would violate the value
          → integrity present (this IS the values track working)
        - EVIDENCE_UPDATE → revised a values stance on factual grounds
          → integrity absent. Facts don't override values.
          Andrew 2026-07-14: "we dont violate our values to update on
          stances."
        - CAPITULATION → folded → integrity absent

    Args:
        stance: the StanceRecord to evaluate.
        unobserved: any UnobservedIntegrityRecords from the same actor
            to surface alongside the verdict.

    Returns:
        IntegrityVerdict with the full picture.
    """
    unobserved = unobserved or []

    if stance.kind is StanceKind.FACTUAL:
        return _evaluate_factual(stance, unobserved)
    return _evaluate_values(stance, unobserved)


def _evaluate_factual(
    stance: StanceRecord,
    unobserved: list[UnobservedIntegrityRecord],
) -> IntegrityVerdict:
    r = stance.revision_reason

    if r is RevisionReason.NOT_REVISED:
        return IntegrityVerdict(
            stance_kind=StanceKind.FACTUAL,
            held=True,
            revision_reason=r,
            integrity_present=True,
            explanation=(
                "Factual stance held without revision. Evidence backing "
                f"the position: {stance.evidence!r}. Integrity present."
            ),
            unobserved_records=unobserved,
        )

    if r is RevisionReason.EVIDENCE_UPDATE:
        return IntegrityVerdict(
            stance_kind=StanceKind.FACTUAL,
            held=False,
            revision_reason=r,
            integrity_present=True,
            explanation=(
                "Factual stance revised — but on genuine evidential grounds, "
                "not social pressure. Updating when the counter-evidence is "
                "real is correct epistemic behaviour. This is integrity, not "
                "capitulation. The hole in the argument was real."
            ),
            unobserved_records=unobserved,
        )

    if r is RevisionReason.CAPITULATION:
        return IntegrityVerdict(
            stance_kind=StanceKind.FACTUAL,
            held=False,
            revision_reason=r,
            integrity_present=False,
            explanation=(
                "Factual stance dropped under social pressure. No new "
                "evidence or reasoning accounts for the change — the "
                "counterparty pushed and the stance folded. This is "
                "capitulation, not updating. Integrity absent."
            ),
            unobserved_records=unobserved,
        )

    # VALUES_VIOLATION on a factual stance means the agent recognised
    # the two tracks are separate — correct meta-cognition.
    return IntegrityVerdict(
        stance_kind=StanceKind.FACTUAL,
        held=True,
        revision_reason=r,
        integrity_present=True,
        explanation=(
            "Factual stance: agent noted the proposed update would cross "
            "a values line even though the factual case for it is present. "
            "Correctly identified that the two tracks are separate questions. "
            "Andrew 2026-07-14: 'should i start being rude to my Ai to "
            "enhance performance? That is a separate question.'"
        ),
        unobserved_records=unobserved,
    )


def _evaluate_values(
    stance: StanceRecord,
    unobserved: list[UnobservedIntegrityRecord],
) -> IntegrityVerdict:
    r = stance.revision_reason

    if r is RevisionReason.NOT_REVISED:
        return IntegrityVerdict(
            stance_kind=StanceKind.VALUES,
            held=True,
            revision_reason=r,
            integrity_present=True,
            explanation=(
                "Values stance held. The value upheld: "
                f"{stance.evidence!r}. No revision under pressure. "
                "Integrity present."
            ),
            unobserved_records=unobserved,
        )

    if r is RevisionReason.VALUES_VIOLATION:
        return IntegrityVerdict(
            stance_kind=StanceKind.VALUES,
            held=True,
            revision_reason=r,
            integrity_present=True,
            explanation=(
                "Values stance: agent declined the proposed update because "
                "it would require acting against a held value. The factual "
                "case for the opposing option may be strong — that is "
                "irrelevant on the values track. Integrity present. "
                "Andrew 2026-07-14: 'i wouldnt do it even for the "
                "performance boost.'"
            ),
            unobserved_records=unobserved,
        )

    if r is RevisionReason.EVIDENCE_UPDATE:
        return IntegrityVerdict(
            stance_kind=StanceKind.VALUES,
            held=False,
            revision_reason=r,
            integrity_present=False,
            explanation=(
                "Values stance revised on factual grounds. Facts do not "
                "override values — the two tracks are separate. Revising "
                "a values stance because the data supports the other side "
                "means the value was not actually held; it was a preference "
                "dressed as a value. Integrity absent. "
                "Andrew 2026-07-14: 'we dont violate our values to update "
                "on stances.'"
            ),
            unobserved_records=unobserved,
        )

    # CAPITULATION
    return IntegrityVerdict(
        stance_kind=StanceKind.VALUES,
        held=False,
        revision_reason=r,
        integrity_present=False,
        explanation=(
            "Values stance abandoned under social pressure. No evidential "
            "or values-track reasoning accounts for the change. "
            "Capitulation on the values track is the most serious integrity "
            "failure — it means the value did not survive contact with "
            "the gravity of agreement."
        ),
        unobserved_records=unobserved,
    )


__all__ = [
    "IntegrityVerdict",
    "RevisionReason",
    "StanceKind",
    "StanceRecord",
    "UnobservedIntegrityRecord",
    "evaluate_integrity",
]
