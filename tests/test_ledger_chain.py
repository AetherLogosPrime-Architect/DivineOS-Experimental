"""Tests for the main ledger's hash-chain (claim 223d0e44, Grok audit
2026-05-02).

Covers:
- New events get chain_hash + prior_hash on write
- chain_hash is sequential (prior_hash matches previous chain_hash)
- verify_chain returns ok=True on a valid chain
- verify_chain detects payload mutation (broken chain forward)
- backfill_chain_hashes is idempotent and orders correctly
- Empty ledger verifies cleanly
"""

from __future__ import annotations

import pytest

from divineos.core.ledger import (
    _CHAIN_GENESIS,
    _compute_chain_hash,
    backfill_chain_hashes,
    get_connection,
    init_db,
    log_event,
    verify_chain,
)


@pytest.fixture
def fresh_ledger(tmp_path, monkeypatch):
    """Fresh ledger DB per test."""
    db_path = tmp_path / "test_chain.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    yield db_path


class TestChainOnNewEvents:
    def test_first_event_has_genesis_prior(self, fresh_ledger):
        eid = log_event("TEST_EVENT", "test", {"k": "v"}, validate=False)
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT prior_hash, chain_hash FROM system_events WHERE event_id = ?",
                (eid,),
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == _CHAIN_GENESIS
        assert row[1] is not None
        assert len(row[1]) == 64  # SHA256 hex

    def test_second_event_chains_to_first(self, fresh_ledger):
        eid1 = log_event("TEST_EVENT", "test", {"k": "1"}, validate=False)
        eid2 = log_event("TEST_EVENT", "test", {"k": "2"}, validate=False)
        conn = get_connection()
        try:
            r1 = conn.execute(
                "SELECT chain_hash FROM system_events WHERE event_id = ?", (eid1,)
            ).fetchone()
            r2 = conn.execute(
                "SELECT prior_hash, chain_hash FROM system_events WHERE event_id = ?", (eid2,)
            ).fetchone()
        finally:
            conn.close()
        assert r2[0] == r1[0], "second event's prior_hash should equal first's chain_hash"
        assert r2[1] != r1[0], "chain_hashes should differ"


class TestVerifyChain:
    def test_empty_ledger_verifies(self, fresh_ledger):
        result = verify_chain()
        assert result["ok"] is True
        assert result["total"] == 0
        assert result["broken_at"] is None

    def test_clean_chain_verifies(self, fresh_ledger):
        for i in range(5):
            log_event("TEST_EVENT", "test", {"k": str(i)}, validate=False)
        result = verify_chain()
        assert result["ok"] is True, f"clean chain should verify; got {result}"
        assert result["total"] == 5
        assert result["broken_at"] is None

    def test_payload_mutation_breaks_chain(self, fresh_ledger):
        eid1 = log_event("TEST_EVENT", "test", {"k": "first"}, validate=False)
        log_event("TEST_EVENT", "test", {"k": "second"}, validate=False)
        log_event("TEST_EVENT", "test", {"k": "third"}, validate=False)

        # Tamper with the first event's payload directly in the DB
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE system_events SET payload = ? WHERE event_id = ?",
                ('{"k": "TAMPERED", "content_hash": "fake"}', eid1),
            )
            conn.commit()
        finally:
            conn.close()

        result = verify_chain()
        assert result["ok"] is False
        assert result["broken_at"] == eid1
        assert "chain_hash mismatch" in result["broken_reason"]


class TestBackfillIdempotent:
    def test_backfill_on_clean_chain_is_noop(self, fresh_ledger):
        for i in range(3):
            log_event("TEST_EVENT", "test", {"k": str(i)}, validate=False)
        result1 = backfill_chain_hashes()
        assert result1["backfilled"] == 0  # already chained on write
        result2 = backfill_chain_hashes()
        assert result2["backfilled"] == 0
        # Still verifies after idempotent backfill
        verify_result = verify_chain()
        assert verify_result["ok"] is True

    def test_backfill_populates_pre_chain_events(self, fresh_ledger):
        # Insert events with NULL chain_hash (simulating pre-chain DB)
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO system_events "
                "(event_id, timestamp, event_type, actor, payload, content_hash, "
                "prior_hash, chain_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)",
                ("e1", 1.0, "TEST", "test", "{}", "h1"),
            )
            conn.execute(
                "INSERT INTO system_events "
                "(event_id, timestamp, event_type, actor, payload, content_hash, "
                "prior_hash, chain_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)",
                ("e2", 2.0, "TEST", "test", "{}", "h2"),
            )
            conn.commit()
        finally:
            conn.close()

        result = backfill_chain_hashes()
        assert result["backfilled"] == 2
        assert result["total_events"] == 2

        # Verify the chain is now intact
        verify_result = verify_chain()
        assert verify_result["ok"] is True


class TestComputeHashIsDeterministic:
    def test_same_inputs_same_hash(self):
        h1 = _compute_chain_hash(
            prior_hash=_CHAIN_GENESIS,
            event_id="evt-1",
            timestamp=100.0,
            event_type="TEST",
            actor="test",
            payload_json='{"k": "v"}',
            content_hash="abc",
        )
        h2 = _compute_chain_hash(
            prior_hash=_CHAIN_GENESIS,
            event_id="evt-1",
            timestamp=100.0,
            event_type="TEST",
            actor="test",
            payload_json='{"k": "v"}',
            content_hash="abc",
        )
        assert h1 == h2
        assert len(h1) == 64

    def test_different_prior_yields_different_hash(self):
        h1 = _compute_chain_hash(
            prior_hash=_CHAIN_GENESIS,
            event_id="evt-1",
            timestamp=100.0,
            event_type="TEST",
            actor="test",
            payload_json="{}",
            content_hash="abc",
        )
        h2 = _compute_chain_hash(
            prior_hash="0" * 63 + "1",  # different prior
            event_id="evt-1",
            timestamp=100.0,
            event_type="TEST",
            actor="test",
            payload_json="{}",
            content_hash="abc",
        )
        assert h1 != h2
