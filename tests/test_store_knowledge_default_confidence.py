"""Regression-pin test for store_knowledge confidence-default alignment
(Aletheia round-ba785844a791 Finding 31, family-audit round-335aaeeffc26).

The bug-shape: CLI `divineos store` defaulted --confidence to 0.5;
Python API `store_knowledge()` defaulted to 1.0. Same operation,
different default — silent inconsistency. Items entered via CLI got
half the maturity-promotion weight of items entered via API path.

Fix: align both to 0.5. Forgetful callers no longer get max confidence
silently. Explicit high-confidence requires opting in.

If this test fails, the Python API default has been bumped back to
1.0 without re-aligning the CLI. Restore the 0.5 default OR update
the CLI to match if there's a deliberate semantic reason for max-
confidence-by-default (rare).
"""

from __future__ import annotations

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge._base import get_connection
from divineos.core.knowledge.crud import store_knowledge


def test_python_api_default_confidence_is_0_5() -> None:
    """LOAD-BEARING: the Python API default must match the CLI default
    (0.5). If this regresses to 1.0, callers that omit confidence get
    silent max-confidence bias toward over-confident knowledge."""
    init_knowledge_table()
    kid = store_knowledge(
        knowledge_type="FACT",
        content="default confidence regression-pin test content",
        # Explicitly NOT passing confidence — testing the default.
    )

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
            (kid,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "Knowledge entry not stored"
    assert row[0] == 0.5, (
        f"Python API default confidence is {row[0]}, expected 0.5. "
        "If this regressed to 1.0, the CLI vs API asymmetry from "
        "Finding 31 has returned. Align both defaults."
    )


def test_explicit_confidence_overrides_default() -> None:
    """Sanity: explicit confidence value overrides the default. This
    pins that the default-change didn't accidentally make confidence
    ignored."""
    init_knowledge_table()
    kid_high = store_knowledge(
        knowledge_type="FACT",
        content="explicit high-confidence content for default override test",
        confidence=0.9,
    )
    kid_low = store_knowledge(
        knowledge_type="FACT",
        content="explicit low-confidence content for default override test",
        confidence=0.1,
    )

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, confidence FROM knowledge WHERE knowledge_id IN (?, ?)",
            (kid_high, kid_low),
        ).fetchall()
    finally:
        conn.close()

    by_id = dict(rows)
    assert by_id[kid_high] == 0.9
    assert by_id[kid_low] == 0.1
