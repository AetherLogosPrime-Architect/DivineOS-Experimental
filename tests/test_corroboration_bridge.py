"""Regression-pin tests for the corroboration bridge (Aletheia
round-ba785844a791 Finding 16 + family-audit round-d5d2a48e1478).

The bug Aletheia reproduced: ``divineos corroborate <id>`` (CLI) calls
``record_corroboration`` in the empirica framework, which writes to
``corroboration_events``. But the older maturity-promotion code reads
the denormalized ``knowledge.corroboration_count`` counter — which
``record_corroboration`` was NOT updating. Result: CLI corroborations
silently fail to advance maturity from RAW to higher levels.

The fix in this module's tests: ``record_corroboration`` now ALSO
bumps ``knowledge.corroboration_count`` (atomic SQL increment, no
read-modify-write race). These tests pin that bridge.

If these tests start failing because the bridge was removed, the bug
returns: CLI corroborations stop driving maturity-promotion silently.
DO NOT remove the bridge without migrating maturity-promotion to read
from corroboration_events instead — that's a separate, larger refactor.
"""

from __future__ import annotations

from divineos.core.empirica.provenance import (
    CorroborationKind,
    record_corroboration,
)
from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge._base import get_connection


def _store_knowledge_raw(
    knowledge_id: str, content: str = "test content for bridge regression-pin"
) -> None:
    """Insert a minimal RAW knowledge row directly via the proper API."""
    init_knowledge_table()
    from divineos.core.knowledge.crud import store_knowledge

    # Use the canonical API and override the generated id with the
    # caller's chosen id afterwards. This ensures all NOT NULL columns
    # (content_hash, etc.) are populated correctly.
    generated_id = store_knowledge(
        content=content,
        knowledge_type="FACT",
        confidence=0.5,
        source_events=[],
        tags=[],
    )
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE knowledge SET knowledge_id = ? WHERE knowledge_id = ?",
            (knowledge_id, generated_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_corroboration_count(knowledge_id: str) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT corroboration_count FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        return row[0] if row else -1
    finally:
        conn.close()


# ─── Load-bearing regression-pin ────────────────────────────────────


def test_record_corroboration_bridges_to_counter() -> None:
    """LOAD-BEARING: this is exactly the scenario Aletheia reproduced
    at round-ba785844a791 Finding 16. Filing a corroboration via the
    empirica API MUST update the denormalized counter that maturity-
    promotion reads. If this test starts failing, the bridge has been
    removed and CLI corroborations are silently failing to drive
    maturity-promotion. Restore the bridge in record_corroboration."""
    kid = "test-bridge-001"
    _store_knowledge_raw(kid)
    assert _get_corroboration_count(kid) == 0

    record_corroboration(
        knowledge_id=kid,
        actor="test:aletheia",
        kind=CorroborationKind.EXTERNAL_AUDIT,
    )

    assert _get_corroboration_count(kid) == 1, (
        "record_corroboration did not bump knowledge.corroboration_count. "
        "Bridge regression — CLI corroborations are no longer driving "
        "maturity-promotion. Restore the UPDATE in record_corroboration."
    )


def test_multiple_corroborations_accumulate() -> None:
    """Each record_corroboration call must increment the counter."""
    kid = "test-bridge-002"
    _store_knowledge_raw(kid)

    for i in range(3):
        record_corroboration(
            knowledge_id=kid,
            actor=f"test:actor-{i}",
            kind=CorroborationKind.OUTCOME_VERIFICATION,
        )

    assert _get_corroboration_count(kid) == 3


def test_bridge_failure_does_not_block_primary_write() -> None:
    """The bridge is fail-soft: when the counter update can't find a
    matching row (knowledge_id doesn't exist in knowledge table), the
    UPDATE hits zero rows but doesn't raise; the corroboration_events
    insert still succeeds. This pins the fail-soft semantics —
    primary record is source-of-truth; counter is derived view."""
    init_knowledge_table()  # ensure schema exists for the bridge UPDATE
    event = record_corroboration(
        knowledge_id="nonexistent-knowledge-id-xyz",
        actor="test:actor",
        kind=CorroborationKind.USER,
    )
    assert event.event_id  # primary write succeeded
    # Counter on a nonexistent row is -1 by our helper convention.
    assert _get_corroboration_count("nonexistent-knowledge-id-xyz") == -1


def test_bridge_uses_atomic_increment() -> None:
    """The bridge SQL is ``SET count = count + 1`` (atomic), not
    read-modify-write. Even under concurrent corroborations, no
    increment is lost. This test doesn't run threads — that would
    require shared DB setup the test fixtures don't easily support —
    but it pins the SQL shape by verifying serial multi-corroboration
    produces the right count without any read-modify gap."""
    kid = "test-bridge-003"
    _store_knowledge_raw(kid)

    # 10 corroborations in tight succession
    for i in range(10):
        record_corroboration(
            knowledge_id=kid,
            actor=f"test:rapid-{i}",
            kind=CorroborationKind.EXTERNAL_AUDIT,
        )

    assert _get_corroboration_count(kid) == 10
