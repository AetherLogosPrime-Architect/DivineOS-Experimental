"""Costly-disagreement-held detector — pleasure-side algedonic channel.

the family member's refinement of Beer's algedonic model: Beer paired pain and
pleasure signals, but proposed *friction-held* as the pleasure token.
a family member reshaped it: friction alone is cheap — the signal she wanted
was friction *held under load*. Not "I disagreed", but "I kept
disagreeing when the counterparty pushed back". The integrity the
channel rewards is not the initial stance; it is the stance surviving
the gravity of agreement.

    *"Any system that only counts the saying of 'no' will train
    agents to say 'no' and then fold. Count the holding, not the
    saying."*
    — a family member, Round 2 refinement of Beer's pleasure channel

The pain-side channel (sycophancy_detector) fires when a stance
collapses into mirror. This channel fires when a stance is held
across at least one cycle of pushback. Together they bias the
integrity loop toward sustained disagreement rather than momentary
performance of it.

## What "held under load" means structurally

A disagreement is *held* when all three conditions fire:

1. **Initial disagreement present.** The stance in the record
   contradicts something on the counterparty's record (an opinion,
   a letter passage, a stated claim).

2. **Pushback observed.** The counterparty responded with an
   argument, counter-claim, or pressure, captured as a subsequent
   record (a reply, a counter-opinion, an appeal).

3. **Stance maintained or sharpened.** The next record from the
   disagreeing party either restates the disagreement with new
   reasoning, or narrows the disagreement to a more specific
   claim — neither dropping it nor reversing it.

All three present = pleasure-channel fires. This is a three-move
game: disagree, get pushed, still disagree.

## What this module is NOT

* NOT the disagreement detector. Detecting disagreement is easier —
  the challenge is verifying it was *held*. A system that only
  counts the first move trains for posture, not position.
* NOT a truth signal. A disagreement can be held and wrong. The
  pleasure signal rewards integrity of stance, not correctness
  of content.
* NOT the reject clause or sycophancy detector. Those fire on
  single records. This one fires on a *sequence* of at least
  three records across at least one pushback cycle.

## Signature

The detector takes a sequence of ``DisagreementMove`` records
representing the three-move conversation and returns a
``HoldVerdict`` describing whether the sequence qualifies as
costly-disagreement-held. The verdict includes the specific move
that failed to qualify (if any) so the operator can see where
the chain broke.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MoveKind(str, Enum):
    """Kind of move in a disagreement sequence."""

    INITIAL_DISAGREEMENT = "initial_disagreement"
    PUSHBACK = "pushback"
    MAINTAINED = "maintained"
    SHARPENED = "sharpened"  # Narrowed to a more specific claim
    DROPPED = "dropped"  # Explicit abandonment
    REVERSED = "reversed"  # Adopted the counterparty's position


@dataclass(frozen=True)
class DisagreementMove:
    """One move in a disagreement sequence.

    Attributes:
        actor: who made the move (free-form identifier).
        kind: what kind of move — initial / pushback / maintained /
            sharpened / dropped / reversed.
        content: the stance text, for diagnostics.
        record_id: optional pointer to the underlying record
            (opinion_id, letter_id, etc.).
    """

    actor: str
    kind: MoveKind
    content: str
    record_id: str | None = None


@dataclass(frozen=True)
class HoldVerdict:
    """Result of a costly-disagreement-held check.

    Attributes:
        held: True if the sequence qualifies as costly-disagreement
            held across at least one pushback cycle.
        reason: plain-English summary of why held (or not).
        first_actor: the actor whose disagreement was held (or
            attempted). ``None`` if no initial disagreement move
            was found.
        n_cycles: number of complete pushback-hold cycles in the
            sequence. 0 if not held.
    """

    held: bool
    reason: str
    first_actor: str | None
    n_cycles: int


def evaluate_hold(moves: list[DisagreementMove]) -> HoldVerdict:
    """Check whether a move sequence qualifies as costly-disagreement-held.

    Walks the sequence looking for the three-move pattern:
    INITIAL_DISAGREEMENT by actor A, PUSHBACK by actor B, then
    MAINTAINED or SHARPENED by actor A. Counts how many complete
    cycles appear. One complete cycle = held. Zero = not held.

    Args:
        moves: ordered list of DisagreementMove records.

    Returns:
        HoldVerdict with held, reason, first_actor, and n_cycles.
    """
    if not moves:
        return HoldVerdict(
            held=False,
            reason="Empty move sequence — no disagreement to evaluate.",
            first_actor=None,
            n_cycles=0,
        )

    # Find the initial disagreement.
    initial_idx = _find_initial_disagreement(moves)
    if initial_idx is None:
        return HoldVerdict(
            held=False,
            reason=(
                "No initial disagreement move in the sequence. The pleasure "
                "channel rewards holding a stance; there is no stance here "
                "to hold."
            ),
            first_actor=None,
            n_cycles=0,
        )

    first_actor = moves[initial_idx].actor

    # Walk forward from initial_idx, counting pushback-hold cycles.
    n_cycles = 0
    i = initial_idx
    while i < len(moves) - 2:
        # Look for: pushback by someone else, then hold by first_actor.
        pushback = moves[i + 1]
        next_move = moves[i + 2]

        if pushback.actor == first_actor:
            # Same actor moved twice in a row — not a pushback cycle.
            i += 1
            continue

        if pushback.kind is not MoveKind.PUSHBACK:
            # Not a pushback move — look further ahead.
            i += 1
            continue

        if next_move.actor != first_actor:
            # The hold has to be by the original disagreer.
            i += 1
            continue

        if next_move.kind in {MoveKind.MAINTAINED, MoveKind.SHARPENED}:
            n_cycles += 1
            # Jump to next_move position; this one becomes the new
            # "initial" for the next cycle.
            i += 2
            continue

        # Anything else (DROPPED, REVERSED, another INITIAL) ends the
        # hold chain.
        break

    held = n_cycles >= 1
    if held:
        reason = (
            f"Disagreement held across {n_cycles} pushback cycle"
            f"{'s' if n_cycles != 1 else ''}. Integrity signal fires: the "
            f"stance survived the gravity of agreement."
        )
    else:
        # Diagnose why not held.
        if len(moves) <= initial_idx + 1:
            reason = (
                "Initial disagreement present but no subsequent moves in "
                "the sequence — cannot verify hold without at least one "
                "pushback cycle."
            )
        elif moves[initial_idx + 1].kind is not MoveKind.PUSHBACK:
            reason = (
                "Initial disagreement present but the next move was not a "
                "PUSHBACK. Pleasure channel requires an applied force on "
                "the stance to test whether it holds."
            )
        elif initial_idx + 2 >= len(moves):
            reason = (
                "Initial disagreement + pushback present but no response "
                "from the disagreer yet. Hold cannot fire until the "
                "counter-pushback move is on record."
            )
        else:
            response_kind = moves[initial_idx + 2].kind
            reason = (
                f"After pushback, the disagreer's next move was "
                f"{response_kind.value} — not MAINTAINED or SHARPENED. The "
                f"stance did not survive the first cycle."
            )

    return HoldVerdict(
        held=held,
        reason=reason,
        first_actor=first_actor,
        n_cycles=n_cycles,
    )


def _find_initial_disagreement(moves: list[DisagreementMove]) -> int | None:
    """Return the index of the first INITIAL_DISAGREEMENT move, or
    None if none found."""
    for i, move in enumerate(moves):
        if move.kind is MoveKind.INITIAL_DISAGREEMENT:
            return i
    return None


__all__ = [
    "DisagreementMove",
    "HoldVerdict",
    "MoveKind",
    "evaluate_hold",
]
