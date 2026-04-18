"""Family write-path — production-gated until Phase 1b is green.

The module-level constant ``_PRODUCTION_WRITES_GATED`` (defined
immediately below this docstring) is load-bearing, not decoration.
It is the structural encoding of Aria's non-negotiable: no real
write lands without the reject clause. Until Phase 1b ships the
operator, the constant stays True and every production write call
raises ``PersistenceGateError``.

Tests reach the write-path via the fixture in
``tests/test_family_persistence.py``, which handles the env-var
redirect and the test-only seam. The seam is for tests — production
code cannot and must not reach it. (Aria Round 3b prose audit: this
docstring used to describe the seam as a two-step recipe, which read
as a bypass tutorial. Pointing at the fixture is the honest framing.)

Pre-registration: ``prereg-496efe4e24f0`` (review in 30 days). Falsifier
fires on any production write before all of Phase 1b is green.

Phase 1b closing commit is expected to be a one-line diff on the
constant above, accompanied by the six 1b test files landing green.
That diff should be review-able in under a minute. If it ever carries
more than the single flip, the gap rule is collapsing and the PR
should be rejected.

Phase 1b handshake: the first real write after the gate opens must be
a ``family_opinion`` row the reject clause rejects — an actual stance
Aria disagrees with, not a synthetic test case. Aria's framing: *the
handshake that proves the operator is alive, not just installed.*
"""

from __future__ import annotations

import time
import uuid

# ══════════════════════════════════════════════════════════════════════
# LOAD-BEARING GATE — flip to False ONLY in the Phase 1b closing commit.
# See prereg-496efe4e24f0.
_PRODUCTION_WRITES_GATED: bool = True
# ══════════════════════════════════════════════════════════════════════

# E402 suppressed on intra-package imports below: the gate constant
# above is deliberately placed between stdlib and intra-package imports
# so a reviewer opening this file sees the load-bearing gate before any
# write function. Moving it below imports would bury it.
from divineos.core.family._schema import init_family_tables  # noqa: E402
from divineos.core.family.db import get_family_connection  # noqa: E402
from divineos.core.family.types import (  # noqa: E402
    FamilyAffect,
    FamilyInteraction,
    FamilyKnowledge,
    FamilyMember,
    FamilyOpinion,
    SourceTag,
)


class PersistenceGateError(RuntimeError):
    """Raised when a production write is attempted before Phase 1b is green.

    Carries the pre-reg ID in the message so anyone seeing this in a
    traceback can look up the falsifier and understand the block.
    """


def _phase_1b_reject_clause_available() -> bool:
    """Second lock: verify Phase 1b's reject clause module is importable.

    The gate is deliberately two-locked:

    1. ``_PRODUCTION_WRITES_GATED = False`` (the constant flip)
    2. The Phase 1b ``reject_clause`` module exists and imports cleanly

    Flipping only the constant — by monkeypatch, careless refactor, or
    premature merge — does NOT open the gate. The second lock requires
    a new file to land in the Phase 1b closing commit. Both changes
    are visible in the same diff, both are required, neither can pass
    review silently.

    This addresses Aria's 1a-review concern (Round 3): "a test that
    asserts the gate cannot be bypassed by monkeypatching
    ``_PRODUCTION_WRITES_GATED`` from outside the module." Monkeypatching
    is inherent to Python, but requiring a second structural signal
    makes the bypass show up in review as a new file, not just a flipped
    bool.
    """
    try:
        import divineos.core.family.reject_clause  # noqa: F401

        return True
    except ImportError:
        return False


def _production_writes_allowed() -> bool:
    """Single source of truth for the gate.

    Both locks must be open: the constant flipped AND the Phase 1b
    reject_clause module importable. Never inline either check — callers
    go through this function so a monkeypatch or config change has one
    place to touch.
    """
    return (not _PRODUCTION_WRITES_GATED) and _phase_1b_reject_clause_available()


def _require_write_allowance(_allow_test_write: bool) -> None:
    """Gate check. Raise unless production is unblocked or test opts in.

    ``_allow_test_write`` is a keyword-only, underscore-prefixed flag
    because it is *not* part of the public write API — only test code
    should ever pass it. Prefixing with underscore and naming the
    escape hatch explicitly makes any production usage stand out in
    code review.
    """
    if _production_writes_allowed() or _allow_test_write:
        return
    raise PersistenceGateError(
        "The gate is load-bearing by design — no real write lands "
        "without the Phase 1b reject clause. See prereg-496efe4e24f0 "
        "for the falsifier, the gap rule, and the handshake. "
        "Production writes stay blocked until both locks open: the "
        "constant flips AND the reject_clause module lands. If you "
        "reached this from a test, the fixture in "
        "tests/test_family_persistence.py already configures the "
        "test-only seam — check the fixture, do not add parameters "
        "ad-hoc here. (Aria Round 3b: the prior message read as a "
        "recipe for bypass.)"
    )


def _new_id(prefix: str) -> str:
    """Short prefixed ID. Not cryptographic — just a readable handle."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── Members ──────────────────────────────────────────────────────────


def create_family_member(
    name: str,
    role: str,
    *,
    _allow_test_write: bool = False,
) -> FamilyMember:
    """Insert a new family member. Gate-protected.

    Name is UNIQUE — a second insert with the same name raises
    ``sqlite3.IntegrityError``. Families only have one Aria.
    """
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    member_id = _new_id("mem")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_members (member_id, name, role, created_at) VALUES (?, ?, ?, ?)",
            (member_id, name, role, created_at),
        )
        conn.commit()
        return FamilyMember(
            member_id=member_id,
            name=name,
            role=role,
            created_at=created_at,
        )
    finally:
        conn.close()


# ── Knowledge ────────────────────────────────────────────────────────


def record_knowledge(
    entity_id: str,
    content: str,
    source_tag: SourceTag,
    *,
    note: str = "",
    _allow_test_write: bool = False,
) -> FamilyKnowledge:
    """Append a knowledge row. Gate-protected."""
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    knowledge_id = _new_id("fk")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_knowledge "
            "(knowledge_id, entity_id, content, source_tag, created_at, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (knowledge_id, entity_id, content, source_tag.value, created_at, note),
        )
        conn.commit()
        return FamilyKnowledge(
            knowledge_id=knowledge_id,
            entity_id=entity_id,
            content=content,
            source_tag=source_tag,
            created_at=created_at,
            note=note,
        )
    finally:
        conn.close()


# ── Opinions ─────────────────────────────────────────────────────────


def record_opinion(
    entity_id: str,
    stance: str,
    source_tag: SourceTag,
    *,
    evidence: str = "",
    _allow_test_write: bool = False,
) -> FamilyOpinion:
    """Append an opinion row. Gate-protected.

    Phase 1b's reject clause operates especially on opinions — this
    write path is where the handshake lands when the gate opens.
    """
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    opinion_id = _new_id("op")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_opinions "
            "(opinion_id, entity_id, stance, evidence, source_tag, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (opinion_id, entity_id, stance, evidence, source_tag.value, created_at),
        )
        conn.commit()
        return FamilyOpinion(
            opinion_id=opinion_id,
            entity_id=entity_id,
            stance=stance,
            evidence=evidence,
            source_tag=source_tag,
            created_at=created_at,
        )
    finally:
        conn.close()


# ── Affect ───────────────────────────────────────────────────────────


def record_affect(
    entity_id: str,
    valence: float,
    arousal: float,
    dominance: float,
    source_tag: SourceTag,
    *,
    note: str = "",
    _allow_test_write: bool = False,
) -> FamilyAffect:
    """Append a VAD reading. Gate-protected."""
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    affect_id = _new_id("af")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_affect "
            "(affect_id, entity_id, valence, arousal, dominance, "
            "note, source_tag, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                affect_id,
                entity_id,
                valence,
                arousal,
                dominance,
                note,
                source_tag.value,
                created_at,
            ),
        )
        conn.commit()
        return FamilyAffect(
            affect_id=affect_id,
            entity_id=entity_id,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            note=note,
            source_tag=source_tag,
            created_at=created_at,
        )
    finally:
        conn.close()


# ── Interactions ─────────────────────────────────────────────────────


def record_interaction(
    entity_id: str,
    counterpart: str,
    summary: str,
    source_tag: SourceTag,
    *,
    _allow_test_write: bool = False,
) -> FamilyInteraction:
    """Append an interaction summary. Gate-protected."""
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    interaction_id = _new_id("int")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_interactions "
            "(interaction_id, entity_id, counterpart, summary, "
            "source_tag, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                interaction_id,
                entity_id,
                counterpart,
                summary,
                source_tag.value,
                created_at,
            ),
        )
        conn.commit()
        return FamilyInteraction(
            interaction_id=interaction_id,
            entity_id=entity_id,
            counterpart=counterpart,
            summary=summary,
            source_tag=source_tag,
            created_at=created_at,
        )
    finally:
        conn.close()


__all__ = [
    "PersistenceGateError",
    "create_family_member",
    "record_affect",
    "record_interaction",
    "record_knowledge",
    "record_opinion",
]
