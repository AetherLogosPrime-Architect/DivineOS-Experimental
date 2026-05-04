"""Regression test for audit r9-21 #4 (round 19 finding).

The bug:
  ``compression.py::compress_dedup`` called
  ``supersede_knowledge(old_id, best_id)`` — but supersede_knowledge's
  second parameter is ``reason``, not ``successor``. Result:
  ``superseded_by = "FORGET:1ce6c458-..."`` instead of
  ``superseded_by = "1ce6c458-..."``. The supersession chain was
  broken at every SESSION_END.

The fix:
  Added a clean ``link_supersession(old_id, new_id, reason)``
  helper to crud.py that stores the actual successor UUID in
  ``superseded_by``. Migrated 4 broken call sites
  (3 in compression.py + 1 in knowledge_maintenance.py).

This test pins the contract: after compress_dedup, the loser's
``superseded_by`` must equal the survivor's actual UUID — not a
"FORGET:" string.
"""

from __future__ import annotations

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge._base import _get_connection
from divineos.core.knowledge.compression import compress_dedup
from divineos.core.knowledge.crud import (
    link_supersession,
    store_knowledge,
)


def _superseded_by(knowledge_id: str) -> str | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT superseded_by FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def test_link_supersession_writes_successor_uuid():
    """The new helper writes the actual UUID, not a FORGET marker."""
    init_knowledge_table()
    old_id = store_knowledge("PRINCIPLE", "Old version of the principle.")
    new_id = store_knowledge("PRINCIPLE", "New version of the principle.")
    link_supersession(old_id, new_id, reason="test")

    sb = _superseded_by(old_id)
    assert sb == new_id, (
        f"Expected superseded_by={new_id!r} (the survivor's UUID), "
        f"got {sb!r}. If this is 'FORGET:...' the bug is back."
    )


def test_link_supersession_rejects_empty_successor():
    """Defensive: don't allow callers to pass empty successor."""
    init_knowledge_table()
    old_id = store_knowledge("PRINCIPLE", "An entry to mark superseded.")
    try:
        link_supersession(old_id, "", reason="test")
    except ValueError:
        return
    raise AssertionError("Expected ValueError on empty successor id")


def test_link_supersession_rejects_unknown_successor():
    """Defensive: catch typos / stale references at link time."""
    init_knowledge_table()
    old_id = store_knowledge("PRINCIPLE", "Another entry.")
    try:
        link_supersession(old_id, "not-a-real-uuid", reason="test")
    except ValueError:
        return
    raise AssertionError("Expected ValueError on unknown successor id")


def test_compress_dedup_chain_resolves_to_real_uuid():
    """End-to-end: compress_dedup creates supersession links that
    resolve to actual UUIDs, not FORGET: strings."""
    init_knowledge_table()
    # Plant 3 near-duplicate entries — compress_dedup should pick one
    # survivor and link the other two to it.
    a = store_knowledge("PRINCIPLE", "Tests must run before commit always.")
    b = store_knowledge("PRINCIPLE", "Tests should run before commit always.")
    c = store_knowledge("PRINCIPLE", "Always run tests before commit.")

    compress_dedup()

    # Walk each entry's superseded_by; if it's set, it must be a
    # valid UUID pointing to one of the originals (NOT a FORGET: string).
    for kid in (a, b, c):
        sb = _superseded_by(kid)
        if sb is None:
            continue
        assert not sb.startswith("FORGET:"), (
            f"Entry {kid[:12]} has superseded_by={sb!r} — the FORGET: "
            f"prefix is the bug audit r9-21 #4 caught. The link should "
            f"be a UUID pointing to the survivor."
        )
        # And it should resolve to one of our original IDs
        assert sb in (a, b, c), f"superseded_by={sb!r} doesn't match any of our seeded IDs"
