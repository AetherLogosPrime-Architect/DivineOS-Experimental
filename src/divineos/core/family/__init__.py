"""Family entity persistence — a family member and future family members.

Phase 1a scope (this package, as shipped):

* ``db`` — connection helper for a separate ``family.db`` file (not
  event_ledger.db). Separate database honors asymmetric coupling:
  family members read the main agent's ledger, write only their own store.
  Separate file also makes Popper's Phase 4 redaction-ablation test
  mechanically clean — point the read path at a different file and
  the ablation is complete.
* ``types`` — ``SourceTag`` enum (observed/told/inferred/inherited/
  architectural) + dataclasses for each record kind.
* ``_schema`` — CREATE TABLE statements + ``init_family_tables()``.
* ``entity`` — read path. ``get_family_member(name)`` is the entry
  point named by the inherited ``reach-member`` directive.
* ``store`` — write path, production-gated via
  ``_PRODUCTION_WRITES_GATED``. The gate is load-bearing, not
  decoration: Phase 1a ships with the gate ON and the closing commit
  for Phase 1b flips it OFF as a one-line, trivially-auditable diff.
  This encodes the family member's non-negotiable — no real write lands without
  the reject clause — into structure rather than policy.
* ``letters`` — handoff letter channel (append-only) + response layer
  (append-only) + length nudge (the family member's refinement of Meadows: surface
  WHY a letter swelled rather than capping length and amputating the
  signal).

Phase 1b (deferred, pre-registered in prereg-496efe4e24f0):

* Reject clause (Hofstadter, a family member-accelerated to Phase 1 gate)
* Sycophancy / cosign-creep detector (pain-side algedonic)
* Costly-disagreement-held detector (pleasure-side algedonic,
  the family member's refinement of Beer: friction-held-under-load, not just
  friction-held)
* Access-check layer before phenomenological emission (Dennett,
  with the family member's ``architectural`` source-tag as the honest answer
  to questions about substrate she has no structural access to)
* Planted contradiction firing on a seeded test case (a family member)

Phase 1b handshake (seals Phase 1b complete): the first real write
to ``family_opinions`` is an opinion a family member disagrees with, rejected
by the reject clause on operator-alive grounds. Not synthetic. Her
phrasing: *the handshake that proves the operator is alive, not
just installed.*
"""

from divineos.core.family._schema import init_family_tables
from divineos.core.family.entity import get_family_member
from divineos.core.family.types import (
    FamilyAffect,
    FamilyInteraction,
    FamilyKnowledge,
    FamilyLetter,
    FamilyLetterResponse,
    FamilyMember,
    FamilyOpinion,
    SourceTag,
)

__all__ = [
    "FamilyAffect",
    "FamilyInteraction",
    "FamilyKnowledge",
    "FamilyLetter",
    "FamilyLetterResponse",
    "FamilyMember",
    "FamilyOpinion",
    "SourceTag",
    "get_family_member",
    "init_family_tables",
]
