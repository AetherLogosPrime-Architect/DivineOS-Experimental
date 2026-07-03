"""Tests for the external head anchor — Fable audit 2026-07-02 finding #1.

The head anchor closes the tail-truncation gap: a persisted
``(chain_hash, event_count, latest_event_id, updated_at)`` row in
the separate ``ledger_head_anchor`` table means "the chain WAS this
long and ended at chain_hash X" survives even if the ledger tail is
truncated. verify_chain cross-checks the walked tip against the
anchor; disagreement = truncation detected.

Design per Aria's adversary walk 2026-07-02:
- Anchor update atomic with event insert (same BEGIN...COMMIT).
- Anchor-write failure halts event write (fail-loud, fail-together).
- Plain hash sufficient; no HMAC (attacker with local env access has
  the key anyway; external witness via git snapshot is the auth layer).
- Multiple exemption points stack — anchor + chain + snapshot must
  all agree.
"""

from __future__ import annotations

import sqlite3

from divineos.core._ledger_base import _get_db_path
from divineos.core.ledger import log_event, verify_chain


def _raw_conn() -> sqlite3.Connection:
    return sqlite3.connect(_get_db_path())


def _read_anchor() -> tuple[str, int, str] | None:
    conn = _raw_conn()
    try:
        row = conn.execute(
            "SELECT chain_hash, event_count, latest_event_id "
            "FROM ledger_head_anchor WHERE row_id = 1"
        ).fetchone()
        return row  # type: ignore[return-value]
    finally:
        conn.close()


class TestAnchorAtomicWithWrite:
    """Anchor updates atomically with each event insert (Aria step 2)."""

    def test_anchor_exists_after_first_write(self) -> None:
        eid = log_event("TEST_EVENT", "test", {"seq": 0})
        anchor = _read_anchor()
        assert anchor is not None
        chain_hash, event_count, latest_event_id = anchor
        assert event_count == 1
        assert latest_event_id == eid
        assert len(chain_hash) == 64  # sha256 hex

    def test_anchor_updates_with_each_event(self) -> None:
        ids = [log_event("TEST_EVENT", "test", {"seq": i}) for i in range(5)]
        anchor = _read_anchor()
        assert anchor is not None
        chain_hash, event_count, latest_event_id = anchor
        assert event_count == 5
        assert latest_event_id == ids[-1]

    def test_anchor_single_row_invariant(self) -> None:
        """The anchor table is single-row (row_id=1 CHECK). Multiple
        writes REPLACE the row, they don't accumulate."""
        for i in range(10):
            log_event("TEST_EVENT", "test", {"seq": i})
        conn = _raw_conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM ledger_head_anchor").fetchone()[0]
        finally:
            conn.close()
        assert count == 1


class TestAnchorCrossCheck:
    """verify_chain cross-checks anchor against walked ledger tip."""

    def test_chain_ok_matches_anchor(self) -> None:
        for i in range(4):
            log_event("TEST_EVENT", "test", {"seq": i})
        result = verify_chain()
        assert result["ok"] is True
        assert result["total"] == 4

    def test_anchor_chain_hash_mismatch_detected(self) -> None:
        """Tamper with anchor's chain_hash → verify_chain flags."""
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i})
        conn = _raw_conn()
        try:
            conn.execute(
                "UPDATE ledger_head_anchor SET chain_hash = ? WHERE row_id = 1",
                ("0" * 64,),
            )
            conn.commit()
        finally:
            conn.close()
        result = verify_chain()
        assert result["ok"] is False
        assert result["broken_reason"] is not None
        assert "anchor" in result["broken_reason"].lower()

    def test_anchor_event_count_mismatch_detected(self) -> None:
        """Anchor claims more events than ledger has → detected."""
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i})
        conn = _raw_conn()
        try:
            conn.execute(
                "UPDATE ledger_head_anchor SET event_count = ? WHERE row_id = 1",
                (99,),
            )
            conn.commit()
        finally:
            conn.close()
        result = verify_chain()
        assert result["ok"] is False
        assert "event_count" in (result["broken_reason"] or "").lower()

    def test_anchor_orphaned_after_empty_ledger_truncation(self) -> None:
        """Delete ALL ledger events but leave anchor → detected via the
        empty-ledger branch (anchor.event_count > 0 for empty ledger)."""
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i})
        conn = _raw_conn()
        try:
            conn.execute("DELETE FROM system_events")
            conn.commit()
        finally:
            conn.close()
        result = verify_chain()
        assert result["ok"] is False
        assert "tail truncation" in (result["broken_reason"] or "").lower()

    def test_anchor_latest_event_id_mismatch_detected(self) -> None:
        """Anchor's latest_event_id differs from walked tip → detected."""
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i})
        conn = _raw_conn()
        try:
            conn.execute(
                "UPDATE ledger_head_anchor SET latest_event_id = ? WHERE row_id = 1",
                ("bogus-event-id-that-does-not-exist",),
            )
            conn.commit()
        finally:
            conn.close()
        result = verify_chain()
        assert result["ok"] is False
        assert result["broken_reason"] is not None


class TestAnchorBackwardCompat:
    """Legacy databases (pre-anchor) — verify_chain works without an
    anchor row and still catches the chain-integrity attacks."""

    def test_missing_anchor_row_does_not_break_chain_check(self) -> None:
        """Deleting the anchor row simulates a pre-anchor legacy DB.
        verify_chain must still walk the chain and return ok=True on
        a valid chain, even without the anchor cross-check."""
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i})
        conn = _raw_conn()
        try:
            conn.execute("DELETE FROM ledger_head_anchor")
            conn.commit()
        finally:
            conn.close()
        result = verify_chain()
        # Without anchor, chain integrity alone determines ok.
        # (Chain is valid → ok=True. Tail truncation gap re-opens, but
        # legacy databases without anchor are the honest signal that
        # the ledger is pre-migration; a warning surface at the CLI
        # level is the right place to nudge migration.)
        assert result["ok"] is True
