"""Isolated adversarial tests for ledger_verify + verify_chain.

Fable audit 2026-07-02 finding #7 named the coverage gap: the core
integrity verifier the "database cannot lie" invariant rests on has
no direct unit test file. The suite exercised it transitively through
CLI tests. Given the sibling verify_chain has a real tail-truncation
gap (finding #1), the verifier family deserves dedicated adversarial
tests.

Coverage:
- Middle deletion of a chained event → verify_chain catches
- Payload tampering after write → verify_all_events catches (via
  content_hash mismatch)
- Event reorder (timestamp swap) → verify_chain catches (via
  chain_hash mismatch on the reordered pair)
- Tail truncation → currently INVISIBLE (finding #1); marked xfail so
  the fix flipping the assertion is a visible signal that #1 has landed.

These tests write directly to the ledger DB to simulate the exact
adversarial mutations. That's the point: verification code is only
worth its coverage if the tests actually try to break the invariant.
"""

from __future__ import annotations

import sqlite3

from divineos.core._ledger_base import _get_db_path
from divineos.core.ledger import log_event, verify_chain
from divineos.core.ledger_verify import verify_all_events


def _seed_events(n: int) -> list[str]:
    """Write n events to the ledger, return their event ids in order."""
    ids: list[str] = []
    for i in range(n):
        eid = log_event("TEST_EVENT", "test", {"seq": i, "payload_body": f"body-{i}"})
        ids.append(eid)
    return ids


def _raw_conn() -> sqlite3.Connection:
    """Direct sqlite connection bypassing the ledger's write guards.
    Used ONLY by these adversarial tests to simulate tampering."""
    return sqlite3.connect(_get_db_path())


class TestMiddleDeletion:
    """verify_chain must catch deletion of an event in the middle of the chain."""

    def test_middle_delete_breaks_chain(self) -> None:
        ids = _seed_events(6)
        pre_check = verify_chain()
        assert pre_check["ok"] is True
        assert pre_check["total"] == 6

        # Delete the 3rd event directly from sqlite — bypasses the
        # append-only enforcement, which is exactly the adversarial
        # capability we're testing verify_chain's ability to detect.
        conn = _raw_conn()
        try:
            conn.execute("DELETE FROM system_events WHERE event_id = ?", (ids[2],))
            conn.commit()
        finally:
            conn.close()

        result = verify_chain()
        assert result["ok"] is False, "middle deletion undetected"
        assert result["broken_at"] is not None
        assert result["broken_reason"] is not None
        # The chain breaks at the event AFTER the deleted one (its
        # stored prior_hash no longer matches what walking forward
        # from the survivor gives).
        assert result["broken_at"] == ids[3], (
            f"expected chain break at ids[3] (post-delete), got {result['broken_at']}"
        )


class TestPayloadTamper:
    """verify_all_events must catch payload tampering after the write —
    content_hash no longer matches recomputed hash of mutated payload."""

    def test_payload_tamper_flagged_as_corrupted(self) -> None:
        ids = _seed_events(3)

        conn = _raw_conn()
        try:
            # Mutate payload of the middle event WITHOUT updating content_hash.
            # Real tamper would need to also rewrite the hash; this simulates
            # the "attacker mutated storage but got interrupted before
            # rewriting the hash" case OR the "attacker doesn't have the
            # hash-recomputation code" case.
            conn.execute(
                "UPDATE system_events SET payload = ? WHERE event_id = ?",
                ('{"seq": 999, "payload_body": "TAMPERED"}', ids[1]),
            )
            conn.commit()
        finally:
            conn.close()

        result = verify_all_events()
        assert result.get("failed", 0) > 0, "payload tampering undetected"
        # The failures list should include the tampered event.
        failure_ids = [f["event_id"] for f in result.get("failures", [])]
        assert ids[1] in failure_ids, (
            f"tampered event {ids[1]} not in failures list {failure_ids[:5]}"
        )


class TestReorder:
    """verify_chain must catch reordering — swap timestamps of two events."""

    def test_reorder_swap_breaks_chain(self) -> None:
        ids = _seed_events(5)
        pre_check = verify_chain()
        assert pre_check["ok"] is True

        # Read the timestamps of events 1 and 3, then swap them. The
        # chain_hash of each depends on its stored prior_hash which
        # depends on ordering — swapping the timestamps changes the
        # walk order without updating stored prior_hash / chain_hash,
        # so verify_chain walking in the new order sees mismatches.
        conn = _raw_conn()
        try:
            rows = conn.execute(
                "SELECT event_id, timestamp FROM system_events WHERE event_id IN (?, ?)",
                (ids[1], ids[3]),
            ).fetchall()
            ts_map = {r[0]: r[1] for r in rows}
            conn.execute(
                "UPDATE system_events SET timestamp = ? WHERE event_id = ?",
                (ts_map[ids[3]], ids[1]),
            )
            conn.execute(
                "UPDATE system_events SET timestamp = ? WHERE event_id = ?",
                (ts_map[ids[1]], ids[3]),
            )
            conn.commit()
        finally:
            conn.close()

        result = verify_chain()
        assert result["ok"] is False, "event reorder undetected"


class TestTailTruncation:
    """Fable audit 2026-07-02 finding #1: tail truncation was invisible
    to verify_chain because no persisted head anchor existed outside
    the ledger table. Fix shipped as external head anchor in
    ledger_head_anchor table, atomic-updated with each event write,
    cross-checked in verify_chain. This test now PASSES (xfail removed).
    """

    def test_tail_truncation_detected_via_head_anchor(self) -> None:
        ids = _seed_events(6)
        pre_check = verify_chain()
        assert pre_check["ok"] is True
        assert pre_check["total"] == 6

        # Truncate the 3 newest events. Chain prefix is still internally
        # consistent, verify_chain returns ok=True — which is the finding.
        conn = _raw_conn()
        try:
            for eid in ids[-3:]:
                conn.execute("DELETE FROM system_events WHERE event_id = ?", (eid,))
            conn.commit()
        finally:
            conn.close()

        result = verify_chain()
        # This assertion is what should hold post-#1-fix: tail truncation
        # is detected. Until the fix lands, verify_chain returns ok=True
        # and this assertion fails — xfail.
        assert result["ok"] is False, (
            "tail truncation undetected — this is Fable finding #1 (expected "
            "to fail until head anchor lands)"
        )
