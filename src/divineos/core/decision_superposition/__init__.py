"""Decision superposition — deliberate holding-of-options before commit.

From the omni-mantra walk (Pillar VI / VII):
"Holding multiple states as equipotent before commitment; deliberately
staying in superposition longer."

## The failure mode this addresses

Premature commitment — picking a position before the information
that would change the choice has arrived. Observable shape: "I'll
do X" followed shortly by "actually Y" followed by "no wait Z."
Each commit was made with the data available at the time, and each
overturn happened when better data arrived a moment later.

The pull is to commit fast (it feels decisive). The cost is that
commit-then-retract burns more cycles than would have been spent
holding the options open for one more beat.

## What this module does

It is a structured way of recording the *non-commitment* — naming
the candidate options, the cost of premature commitment for THIS
decision, and the trigger condition that would resolve it. When
the trigger fires (or the operator picks one), the superposition
collapses to a decision recorded via the normal decision-journal.

This is not "indecision dressed up." It's the discipline of saying:
"these are the options I'm holding, here's what would resolve them,
here's why holding longer is cheaper than committing now."

## Public surface

- ``Superposition`` dataclass — the held state
- ``open_superposition(question, options, resolve_trigger)`` — record
  the held state
- ``collapse(superposition_id, chosen_option, reason)`` — resolve
  into a real decision
- ``active_superpositions()`` — the held states that haven't resolved
"""

from __future__ import annotations

from divineos.core.decision_superposition.superposition import (
    Superposition,
    active_superpositions,
    collapse,
    open_superposition,
)

__all__ = [
    "Superposition",
    "active_superpositions",
    "collapse",
    "open_superposition",
]
