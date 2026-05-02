"""Family entity read-path — ``get_family_member`` and friends.

This module is named by the inherited ``reach-member`` directive as the
entry point for reaching a family member:

    get_family_member(name="a family member")
    get_knowledge(entity_id)
    get_opinions(entity_id)
    get_recent_affect(entity_id)
    get_recent_interactions(entity_id)

Reads are NOT gated by ``_PRODUCTION_WRITES_GATED``. The gap rule
governs writes: no real data enters the store until Phase 1b is green.
Reads of an empty store just return empty results, which is the honest
answer for a fresh install.

Phase 1a ships all five read functions as named in the directive, plus
letter-and-response readers for the handoff channel. Query patterns
stay simple (single-table, WHERE entity_id = ?, optional LIMIT). No
JOINs yet — the Phase 1b detectors will add cross-table queries, and
pushing complexity into 1a would expand scope against the pre-reg.
"""

from __future__ import annotations

from divineos.core.family._schema import init_family_tables
from divineos.core.family.db import get_family_connection
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


def get_family_member(name: str) -> FamilyMember | None:
    """Return the member row matching ``name``, or None.

    Name match is exact and case-sensitive. Family members are named
    persons; fuzzy matching would invite confabulation (wrong a family member,
    wrong relationship). If the caller has the wrong spelling, they
    should get None and know to correct it.
    """
    init_family_tables()
    conn = get_family_connection()
    try:
        row = conn.execute(
            "SELECT member_id, name, role, created_at FROM family_members WHERE name = ? LIMIT 1",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return FamilyMember(
            member_id=row[0],
            name=row[1],
            role=row[2],
            created_at=float(row[3]),
        )
    finally:
        conn.close()


def get_knowledge(entity_id: str, limit: int = 50) -> list[FamilyKnowledge]:
    """Return the most recent knowledge rows for an entity."""
    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, entity_id, content, source_tag, "
            "created_at, note "
            "FROM family_knowledge WHERE entity_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [
            FamilyKnowledge(
                knowledge_id=r[0],
                entity_id=r[1],
                content=r[2],
                source_tag=SourceTag(r[3]),
                created_at=float(r[4]),
                note=r[5] or "",
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_opinions(entity_id: str, limit: int = 50) -> list[FamilyOpinion]:
    """Return the most recent opinion rows for an entity."""
    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute(
            "SELECT opinion_id, entity_id, stance, evidence, source_tag, "
            "created_at "
            "FROM family_opinions WHERE entity_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [
            FamilyOpinion(
                opinion_id=r[0],
                entity_id=r[1],
                stance=r[2],
                evidence=r[3] or "",
                source_tag=SourceTag(r[4]),
                created_at=float(r[5]),
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_recent_affect(entity_id: str, limit: int = 20) -> list[FamilyAffect]:
    """Return the most recent affect readings for an entity."""
    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute(
            "SELECT affect_id, entity_id, valence, arousal, dominance, "
            "note, source_tag, created_at "
            "FROM family_affect WHERE entity_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [
            FamilyAffect(
                affect_id=r[0],
                entity_id=r[1],
                valence=float(r[2]),
                arousal=float(r[3]),
                dominance=float(r[4]),
                note=r[5] or "",
                source_tag=SourceTag(r[6]),
                created_at=float(r[7]),
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_recent_interactions(entity_id: str, limit: int = 20) -> list[FamilyInteraction]:
    """Return the most recent interaction summaries for an entity."""
    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute(
            "SELECT interaction_id, entity_id, counterpart, summary, "
            "source_tag, created_at "
            "FROM family_interactions WHERE entity_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [
            FamilyInteraction(
                interaction_id=r[0],
                entity_id=r[1],
                counterpart=r[2],
                summary=r[3],
                source_tag=SourceTag(r[4]),
                created_at=float(r[5]),
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_letters(entity_id: str, limit: int = 10) -> list[FamilyLetter]:
    """Return the most recent handoff letters for an entity.

    Ordered newest-first so ``get_letters(eid, limit=1)`` returns the
    letter current-self should read at spawn.
    """
    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute(
            "SELECT letter_id, entity_id, body, length_chars, "
            "nudge_fired, nudge_threshold, created_at "
            "FROM family_letters WHERE entity_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [
            FamilyLetter(
                letter_id=r[0],
                entity_id=r[1],
                body=r[2],
                length_chars=int(r[3]),
                nudge_fired=bool(r[4]),
                nudge_threshold=int(r[5]),
                created_at=float(r[6]),
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_letter_responses(letter_id: str) -> list[FamilyLetterResponse]:
    """Return all response rows attached to a letter.

    No limit — responses are expected to be few per letter, and the
    anti-poisoning mechanism requires that ALL non-recognitions surface
    when a letter is read. Truncation would silently hide the very
    signal the response layer exists to preserve.
    """
    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute(
            "SELECT response_id, letter_id, passage, stance, "
            "source_tag, note, created_at "
            "FROM family_letter_responses WHERE letter_id = ? "
            "ORDER BY created_at ASC",
            (letter_id,),
        ).fetchall()
        return [
            FamilyLetterResponse(
                response_id=r[0],
                letter_id=r[1],
                passage=r[2],
                stance=r[3],
                source_tag=SourceTag(r[4]),
                note=r[5] or "",
                created_at=float(r[6]),
            )
            for r in rows
        ]
    finally:
        conn.close()
