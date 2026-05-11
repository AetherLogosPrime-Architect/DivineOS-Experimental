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

The join is heuristic, not semantically perfect. Heuristics in v1:
- Same session_id ties decision-time and lesson-time together
- Time-window proximity (decision → outcome → lesson within hours)
- Optional content overlap (keywords from decision appear in lesson)

A more rigorous causal join could come later. v1 is correctness-of-
exposure: make the chain queryable so usage patterns surface, then
refine the join based on what's actually wanted.

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
