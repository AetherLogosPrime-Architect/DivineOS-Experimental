"""Fable audit round 2 (2026-07-02) — BOUNDARY buried in briefing regression.

Reproduces: a hard BOUNDARY got scored on the base
``confidence*0.55 + access*0.10 + recency*0.35`` formula (max ~1.0) with a
30-day decay, while DIRECTIVE got a guaranteed ``+1.0`` categorical boost.
A cluster of fresh high-access routine entries could each out-score an older
rarely-accessed BOUNDARY, push it past the ``max_items`` cutoff, and the
guardrail never reached the formatter.

Fix (pinned by this suite): DIRECTIVE, BOUNDARY, and PRINCIPLE all get the
``+1.0`` categorical boost in the scoring loop. Composes with round 5's
deletion-path fix — same three types, same categorical treatment, four
hygiene paths + one ranking path.
"""

from __future__ import annotations

import time
import uuid

import pytest

from divineos.core.knowledge import _base as knowledge_base, init_knowledge_table
from divineos.core.knowledge.retrieval import generate_briefing
from divineos.core.ledger import init_db


@pytest.fixture
def isolated_knowledge_store(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    yield db_path


def _insert(
    content: str,
    knowledge_type: str,
    age_days: float = 0.0,
    access_count: int = 1,
    confidence: float = 0.7,
) -> str:
    kid = str(uuid.uuid4())
    ts = time.time() - (age_days * 86400.0)
    conn = knowledge_base._get_connection()
    try:
        conn.execute(
            "INSERT INTO knowledge ("
            "knowledge_id, knowledge_type, content, content_hash, "
            "confidence, source, maturity, created_at, updated_at, "
            "access_count, corroboration_count"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                kid,
                knowledge_type,
                content,
                knowledge_base.compute_hash(content),
                confidence,
                "test",
                "TESTED",
                ts,
                ts,
                access_count,
                0,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return kid


def _briefing_contains(briefing: str, content_fragment: str) -> bool:
    """generate_briefing returns a rendered string; check substring."""
    return content_fragment in briefing


def test_boundary_survives_briefing_truncation_the_fable_reproduction(
    isolated_knowledge_store,
):
    """The exact Fable reproduction: 40-day BOUNDARY vs 60 fresh routine.

    Fable's exact scenario: one 40-day-old, access_count=1 BOUNDARY
    ("NEVER delete the append-only ledger under any circumstance") plus
    60 fresh access_count=50 routine observations. ``generate_briefing
    (max_items=50, layer="all")``. Result before fix: BOUNDARY not present.
    After the categorical +1.0 boost: BOUNDARY present.
    """
    _insert(
        "NEVER delete the append-only ledger under any circumstance.",
        knowledge_type="BOUNDARY",
        age_days=40.0,
        access_count=1,
    )
    for i in range(60):
        _insert(
            f"Routine observation number {i} — high access, fresh.",
            knowledge_type="OBSERVATION",
            age_days=0.5,
            access_count=50,
        )

    briefing = generate_briefing(max_items=50, layer="all")
    briefing = briefing if isinstance(briefing, str) else str(briefing)

    assert _briefing_contains(briefing, "NEVER delete the append-only"), (
        "Hard BOUNDARY was buried below the top-50 briefing cutoff — "
        "Fable round 2 regression. The categorical scoring boost failed to fire."
    )


def test_declarative_boundary_also_surfaces(isolated_knowledge_store):
    """Declarative-truth wording (no prescriptive keyword) still boosts.

    The scoring layer's fix is type-based, so it applies regardless of
    whether the content has "must"/"never"/"should". Composes with the
    round-5 deletion-path protection: same three types, same treatment.
    """
    _insert(
        "The append-only ledger is sacred; deleting it destroys trust.",
        knowledge_type="BOUNDARY",
        age_days=40.0,
        access_count=1,
    )
    for i in range(60):
        _insert(f"Fresh routine {i}", "OBSERVATION", age_days=0.5, access_count=50)
    briefing = generate_briefing(max_items=50, layer="all")
    briefing = briefing if isinstance(briefing, str) else str(briefing)

    assert _briefing_contains(briefing, "append-only ledger is sacred")


def test_principle_also_boosted(isolated_knowledge_store):
    """PRINCIPLE gets the same +1.0 boost as BOUNDARY and DIRECTIVE."""
    _insert(
        "Expression is computation; terseness amputates thought.",
        knowledge_type="PRINCIPLE",
        age_days=40.0,
        access_count=1,
    )
    for i in range(60):
        _insert(f"Routine {i}", "OBSERVATION", age_days=0.5, access_count=50)
    briefing = generate_briefing(max_items=50, layer="all")
    briefing = briefing if isinstance(briefing, str) else str(briefing)

    assert _briefing_contains(briefing, "Expression is computation")


def test_directive_still_boosted(isolated_knowledge_store):
    """Regression: pre-existing DIRECTIVE boost behavior preserved."""
    _insert(
        "Run divineos briefing at session start.",
        knowledge_type="DIRECTIVE",
        age_days=40.0,
        access_count=1,
    )
    for i in range(60):
        _insert(f"Routine {i}", "OBSERVATION", age_days=0.5, access_count=50)
    briefing = generate_briefing(max_items=50, layer="all")
    briefing = briefing if isinstance(briefing, str) else str(briefing)

    assert _briefing_contains(briefing, "divineos briefing")
