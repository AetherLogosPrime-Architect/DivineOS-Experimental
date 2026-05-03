"""Property-based tests for ledger hash-chain integrity (opinion 288beb99).

These tests use hypothesis to generate random event sequences and verify
chain-integrity invariants hold across the generated space. Complements
the targeted tests in test_ledger_chain.py with broader coverage.

Hypothesis settings follow the pattern established in claim 388628c1:
deadline=None (these tests do real SQLite I/O), derandomize=True (CI
reliability over bug-finding-novelty), and ASCII-only strategies (avoid
environment-dependent unicode interactions).

Properties verified:
1. **chain monotonicity** — N events produce a chain where each event's
   prior_hash equals the previous event's chain_hash.
2. **verify_chain ok on clean chain** — any sequence of valid log_event
   calls produces a chain that verify_chain accepts.
3. **mutation breaks chain forward** — tampering with any event's
   payload causes verify_chain to fail at that event.
4. **backfill idempotency** — running backfill twice produces the same
   final chain state as running it once.
5. **chain hash uniqueness across distinct events** — distinct events
   produce distinct chain_hashes (collision resistance).
"""

from __future__ import annotations

import pytest
from hypothesis_compat import HAS_HYPOTHESIS, given, settings, st

from divineos.core.ledger import (
    _CHAIN_GENESIS,
    backfill_chain_hashes,
    get_connection,
    init_db,
    log_event,
    verify_chain,
)


pytestmark = pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")


# Shared strategies — printable ASCII per claim 388628c1 pattern.
_ASCII_TEXT = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1,
    max_size=200,
)
_ASCII_TYPE = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=30,
)


@pytest.fixture(autouse=True)
def isolated_chain_db(tmp_path, monkeypatch):
    """Fresh ledger DB per property test."""
    db_path = tmp_path / "test_chain_props.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    yield db_path


def _reset_events_table() -> None:
    """Truncate system_events between hypothesis examples within a test.

    Hypothesis calls the test function multiple times per @given run.
    Without per-example reset, DB state accumulates and breaks invariants
    that assume "first event chains from genesis" or "total == len(events)
    in this example". Fixture-scope=function isn't enough — the fixture
    runs once per @given invocation, not per example.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM system_events")
        conn.commit()
    finally:
        conn.close()


# ─── Property 1: chain monotonicity ─────────────────────────────────


class TestChainMonotonicity:
    @given(
        events=st.lists(
            st.tuples(_ASCII_TYPE, _ASCII_TEXT),
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=10, deadline=None, derandomize=True)
    def test_each_events_prior_hash_equals_previous_chain_hash(self, events):
        """For any sequence of N>=2 events, event[i].prior_hash equals
        event[i-1].chain_hash. event[0].prior_hash equals genesis."""
        _reset_events_table()
        event_ids = [
            log_event(et, "test", {"k": content}, validate=False) for et, content in events
        ]

        conn = get_connection()
        try:
            rows = []
            for eid in event_ids:
                row = conn.execute(
                    "SELECT prior_hash, chain_hash FROM system_events WHERE event_id = ?",
                    (eid,),
                ).fetchone()
                rows.append(row)
        finally:
            conn.close()

        # First event chains from genesis
        assert rows[0][0] == _CHAIN_GENESIS

        # Each subsequent event's prior_hash matches previous chain_hash
        for i in range(1, len(rows)):
            assert rows[i][0] == rows[i - 1][1], (
                f"Event {i}: prior_hash {rows[i][0][:12]!r} should equal "
                f"event {i - 1}'s chain_hash {rows[i - 1][1][:12]!r}"
            )


# ─── Property 2: verify_chain accepts clean chains ──────────────────


class TestVerifyChainAcceptsCleanChains:
    @given(
        events=st.lists(
            st.tuples(_ASCII_TYPE, _ASCII_TEXT),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=10, deadline=None, derandomize=True)
    def test_any_clean_sequence_verifies(self, events):
        """Any sequence of valid log_event calls produces a chain that
        verify_chain accepts (ok=True, broken_at=None)."""
        _reset_events_table()
        for et, content in events:
            log_event(et, "test", {"k": content}, validate=False)

        result = verify_chain()
        assert result["ok"] is True, (
            f"Clean chain should verify; got broken_at={result['broken_at']}, "
            f"reason={result['broken_reason']}"
        )
        assert result["total"] == len(events)
        assert result["broken_at"] is None


# ─── Property 3: payload mutation breaks chain forward ──────────────


class TestPayloadMutationBreaksChain:
    @given(
        events=st.lists(
            st.tuples(_ASCII_TYPE, _ASCII_TEXT),
            min_size=2,
            max_size=8,
        ),
        # which event index to tamper with (0-indexed)
        tamper_index=st.integers(min_value=0, max_value=7),
    )
    @settings(max_examples=10, deadline=None, derandomize=True)
    def test_tampering_with_payload_breaks_chain(self, events, tamper_index):
        """Mutating any event's payload causes verify_chain to detect
        the break at that event (or earlier — chain-detection fires at
        the first break, which may include the tampered event itself)."""
        _reset_events_table()
        # Filter tamper_index to valid range for this event list
        if tamper_index >= len(events):
            tamper_index = len(events) - 1

        event_ids = [
            log_event(et, "test", {"k": content}, validate=False) for et, content in events
        ]
        target_id = event_ids[tamper_index]

        # Tamper with the target event's payload
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE system_events SET payload = ? WHERE event_id = ?",
                ('{"k": "TAMPERED"}', target_id),
            )
            conn.commit()
        finally:
            conn.close()

        result = verify_chain()
        assert result["ok"] is False, (
            "Tampered chain should not verify; tamper_index=%d events=%d"
            % (tamper_index, len(events))
        )
        assert result["broken_at"] is not None


# ─── Property 4: backfill idempotency ───────────────────────────────


class TestBackfillIdempotency:
    @given(
        events=st.lists(
            st.tuples(_ASCII_TYPE, _ASCII_TEXT),
            min_size=0,
            max_size=8,
        )
    )
    @settings(max_examples=10, deadline=None, derandomize=True)
    def test_backfill_twice_equals_backfill_once(self, events):
        """Running backfill_chain_hashes() twice produces the same
        chain state as running it once. The first run should report
        backfilled=0 because log_event already chains on write."""
        _reset_events_table()
        for et, content in events:
            log_event(et, "test", {"k": content}, validate=False)

        # Snapshot chain_hashes after first backfill
        result1 = backfill_chain_hashes()
        assert result1["backfilled"] == 0, "Already-chained writes need no backfill"

        conn = get_connection()
        try:
            chain_hashes_after_1 = [
                row[0]
                for row in conn.execute(
                    "SELECT chain_hash FROM system_events ORDER BY timestamp ASC, rowid ASC"
                )
            ]
        finally:
            conn.close()

        # Second backfill must also be a no-op
        result2 = backfill_chain_hashes()
        assert result2["backfilled"] == 0

        conn = get_connection()
        try:
            chain_hashes_after_2 = [
                row[0]
                for row in conn.execute(
                    "SELECT chain_hash FROM system_events ORDER BY timestamp ASC, rowid ASC"
                )
            ]
        finally:
            conn.close()

        assert chain_hashes_after_1 == chain_hashes_after_2


# ─── Property 5: chain hash uniqueness ──────────────────────────────


class TestChainHashUniqueness:
    @given(
        events=st.lists(
            st.tuples(_ASCII_TYPE, _ASCII_TEXT),
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=10, deadline=None, derandomize=True)
    def test_distinct_events_produce_distinct_chain_hashes(self, events):
        """Each event's chain_hash should be unique. Same payload at
        different positions still differs because the chain formula
        includes prior_hash + event_id + timestamp."""
        _reset_events_table()
        for et, content in events:
            log_event(et, "test", {"k": content}, validate=False)

        conn = get_connection()
        try:
            chain_hashes = [row[0] for row in conn.execute("SELECT chain_hash FROM system_events")]
        finally:
            conn.close()

        assert len(chain_hashes) == len(set(chain_hashes)), (
            f"Found duplicate chain_hashes; expected all distinct. "
            f"len={len(chain_hashes)} unique={len(set(chain_hashes))}"
        )
