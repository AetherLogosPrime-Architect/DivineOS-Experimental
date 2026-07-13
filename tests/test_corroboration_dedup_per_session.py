"""Regression test for audit r9-21 #3: same-source corroboration dedup.

The bug:
  ``increment_corroboration(kid, source_context="extraction:STATED")``
  fired N times in a single session bumped knowledge.corroboration_count
  N times. One session re-encountering the same knowledge through the
  same code path was laundered into "N independent witnesses,"
  promoting HYPOTHESIS to CONFIRMED on volume of self-talk.

The fix:
  ``knowledge_corroborations`` table with PRIMARY KEY
  (knowledge_id, source_context, session_id). INSERT OR IGNORE
  on each call; only bump corroboration_count when the insert
  actually wrote a row. Cross-session repetition still counts.
  Cross-source repetition in the same session still counts.
"""

from __future__ import annotations

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge._base import _get_connection
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.knowledge_maintenance import increment_corroboration


def _count(kid: str) -> int:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT corroboration_count FROM knowledge WHERE knowledge_id = ?",
            (kid,),
        ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def test_same_source_same_session_dedups():
    """10 calls with identical (source, session) → count goes up by 1, not 10."""
    init_knowledge_table()
    kid = store_knowledge("PRINCIPLE", "Tests must run before commit.")
    start = _count(kid)
    for _ in range(10):
        increment_corroboration(kid, source_context="extraction:STATED", session_id="sess-A")
    assert _count(kid) == start + 1, (
        f"Expected count to increase by exactly 1 from same-source same-session "
        f"repetition; got delta={_count(kid) - start}. The dedup PK is missing."
    )


def test_different_source_same_session_counts():
    """Different source_context in same session → still corroborates."""
    init_knowledge_table()
    kid = store_knowledge("PRINCIPLE", "Run preflight before commit.")
    start = _count(kid)
    increment_corroboration(kid, source_context="extraction:STATED", session_id="sess-B")
    increment_corroboration(kid, source_context="session:end_sweep", session_id="sess-B")
    assert _count(kid) == start + 2


def test_same_source_different_session_counts():
    """Different session → still corroborates (the legit path)."""
    init_knowledge_table()
    kid = store_knowledge("PRINCIPLE", "Always read before edit.")
    start = _count(kid)
    increment_corroboration(kid, source_context="extraction:STATED", session_id="sess-C")
    increment_corroboration(kid, source_context="extraction:STATED", session_id="sess-D")
    assert _count(kid) == start + 2
