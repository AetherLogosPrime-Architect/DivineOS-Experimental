"""Consequence chain — Karma as explicit decision → outcome → lesson trace.

## What this is

From the omni-mantra walk (Pillar I, 1.7 — Karma):
"Systematic propagation of consequences across decision→outcome chains.
Real pull: ``consequence_chain`` module — explicit traces from decisions
through outcomes to lessons."

DivineOS already has the components:
- Decisions live in the decision journal
- Outcomes in the outcomes-measurement layer + ledger events
- Lessons in the knowledge store

What was missing: the *join*. Today the connection between
"decision filed at time T" and "lesson learned at time T+N" is
implicit — temporal proximity, same session — but not queryable.

This module surfaces the join. Given a decision, return its
downstream outcomes and lessons. Given a lesson, trace back to
the decision that likely produced it.

## What this is NOT (yet)

The join is heuristic, not semantically perfect. **v1 is time-window-
only** — decision → outcomes-within-24h, decision → lessons-within-24h.

Aletheia round-20 caught a docstring-vs-implementation drift on this
module: an earlier version of this docstring claimed "same-session +
time-window" but the implementation only filtered by time-window.
The data to support same-session filtering doesn't exist cleanly:
- The `knowledge` table has no `session_id` column
- `log_event` doesn't take a session_id parameter
- Linking a lesson back to its session would require traversing
  `knowledge.source_events` → `event_ledger` rows → some
  session-marker in the payload

Three paths for tightening to same-session in a v2:
1. Add `session_id` to the `knowledge` schema (most invasive; cleanest)
2. Add `session_id` to the ledger event row (medium invasive)
3. Multi-hop query via `source_events` (no schema change; complex)

Until then, **same-session filtering is explicit future work**. v1's
time-window join can chain across sessions when timestamps overlap;
this is a known false-positive class. Consumers should not assume
the chain is causal — it's correlational.

## Public surface

- ``ConsequenceChain`` dataclass — a single chain
- ``chain_from_decision(decision_id)`` — chain forward
- ``chain_to_lesson(lesson_id)`` — chain backward
- ``recent_chains(limit=10)`` — recent consequence chains
"""

from __future__ import annotations

from divineos.core.consequence_chain.chain import (
    ConsequenceChain,
    chain_from_decision,
    chain_to_lesson,
    recent_chains,
)

__all__ = [
    "ConsequenceChain",
    "chain_from_decision",
    "chain_to_lesson",
    "recent_chains",
]
