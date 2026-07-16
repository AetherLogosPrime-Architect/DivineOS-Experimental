"""Tests for state_markers module.

Peer-designed with Aria 2026-07-16; contract in
docs/primitives/forced_work_gate_design.md addendum.

Test surface covers:
- emit + find happy path (single kind, single fingerprint)
- kind isolation (marker of kind A not found by lookup for kind B)
- fingerprint predicate (custom filter)
- consume happy path (fingerprint matches)
- consume with fingerprint mismatch (LOUD event fires — Aria's add)
- consume of already-consumed marker (returns already_consumed)
- consume of not-found marker (returns not_found)
- consume of expired marker (returns expired)
- concurrent consume race (BEGIN IMMEDIATE serializes; only one wins)
- fail-loud on lookup crash (StateMarkerLookupError raised, not None)
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from divineos.core import state_markers
from divineos.core.state_markers import (
    ConsumeVerdict,
    StateMarkerLookupError,
    consume_marker,
    emit_marker,
    find_active_marker,
)


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    """Isolate each test's ledger writes to a temp DB."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    from divineos.core.ledger import init_db

    init_db()
    yield


class TestEmitAndFindHappyPath:
    def test_emit_returns_hex_id(self):
        mid = emit_marker("test_kind", "fp:abc", payload={"k": "v"})
        assert isinstance(mid, str)
        assert len(mid) == 32  # uuid4 hex

    def test_emit_then_find_returns_marker(self):
        mid = emit_marker(
            "claim_scope_active",
            "turn:42",
            payload={"directive_text": "verify before continuing"},
        )
        found = find_active_marker("claim_scope_active")
        assert found is not None
        assert found.marker_id == mid
        assert found.kind == "claim_scope_active"
        assert found.fingerprint == "turn:42"
        assert found.payload["directive_text"] == "verify before continuing"

    def test_find_returns_none_when_no_markers(self):
        assert find_active_marker("no_such_kind") is None

    def test_emit_requires_kind_and_fingerprint(self):
        with pytest.raises(ValueError):
            emit_marker("", "fp")
        with pytest.raises(ValueError):
            emit_marker("kind", "")

    def test_emit_rejects_zero_or_negative_expiry(self):
        with pytest.raises(ValueError):
            emit_marker("kind", "fp", expires_in_seconds=0)
        with pytest.raises(ValueError):
            emit_marker("kind", "fp", expires_in_seconds=-1)


class TestKindIsolation:
    def test_kind_A_marker_not_found_by_kind_B_lookup(self):
        emit_marker("kind_a", "fp:1")
        assert find_active_marker("kind_b") is None
        assert find_active_marker("kind_a") is not None


class TestFingerprintPredicate:
    def test_predicate_filters_matching_only(self):
        emit_marker("op_bypass", "edit:file_a.py")
        emit_marker("op_bypass", "edit:file_b.py")
        result = find_active_marker(
            "op_bypass",
            fingerprint_predicate=lambda fp: fp.endswith("file_a.py"),
        )
        assert result is not None
        assert result.fingerprint == "edit:file_a.py"


class TestConsumeHappyPath:
    def test_consume_returns_consumed_when_fingerprint_matches(self):
        mid = emit_marker("op_bypass", "edit:x.py")
        verdict = consume_marker(mid, "edit:x.py")
        assert verdict.outcome == "consumed"
        assert verdict.fingerprint_mismatch is False
        assert verdict.marker is not None

    def test_consumed_marker_no_longer_findable(self):
        mid = emit_marker("op_bypass", "edit:y.py")
        consume_marker(mid, "edit:y.py")
        assert find_active_marker("op_bypass") is None


class TestConsumeMismatch:
    def test_mismatch_still_consumes_but_flags_mismatch(self):
        mid = emit_marker(
            "op_bypass",
            "edit:authorized.py",
            payload={"quote_hash": "abc123", "reason": "hotfix"},
        )
        verdict = consume_marker(mid, "edit:different_file.py")
        assert verdict.outcome == "consumed"
        assert verdict.fingerprint_mismatch is True

    def test_mismatch_emits_loud_fingerprint_mismatch_event(self):
        mid = emit_marker("op_bypass", "edit:authorized.py", payload={"reason": "test"})
        consume_marker(mid, "edit:different_file.py")

        # The LOUD event should be in the ledger.
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT event_type, payload FROM system_events "
                "WHERE event_type = 'STATE_MARKER_FINGERPRINT_MISMATCH'"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        payload = json.loads(rows[0][1])
        assert payload["authorized_fingerprint"] == "edit:authorized.py"
        assert payload["consumed_by_fingerprint"] == "edit:different_file.py"
        assert payload["kind"] == "op_bypass"

    def test_matching_fingerprint_does_NOT_emit_mismatch_event(self):
        mid = emit_marker("op_bypass", "edit:x.py")
        consume_marker(mid, "edit:x.py")

        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT event_type FROM system_events "
                "WHERE event_type = 'STATE_MARKER_FINGERPRINT_MISMATCH'"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 0, "no mismatch event should fire on matching fingerprint"


class TestConsumeEdgeCases:
    def test_consume_not_found_returns_not_found(self):
        verdict = consume_marker("nonexistent_marker_id", "edit:x.py")
        assert verdict.outcome == "not_found"
        assert verdict.marker is None

    def test_consume_already_consumed_returns_already_consumed(self):
        mid = emit_marker("op_bypass", "edit:x.py")
        first = consume_marker(mid, "edit:x.py")
        assert first.outcome == "consumed"
        second = consume_marker(mid, "edit:x.py")
        assert second.outcome == "already_consumed"

    def test_consume_expired_returns_expired(self):
        # Emit with 0.1s expiry; wait 0.2s; consume.
        mid = emit_marker("op_bypass", "edit:x.py", expires_in_seconds=0.1)
        time.sleep(0.2)
        verdict = consume_marker(mid, "edit:x.py")
        assert verdict.outcome == "expired"

    def test_consume_requires_marker_id_and_fingerprint(self):
        with pytest.raises(ValueError):
            consume_marker("", "fp")
        with pytest.raises(ValueError):
            consume_marker("mid", "")


class TestExpiredMarkerNotFindable:
    def test_expired_marker_not_returned_by_find(self):
        emit_marker("op_bypass", "edit:x.py", expires_in_seconds=0.1)
        time.sleep(0.2)
        assert find_active_marker("op_bypass") is None


class TestConcurrentConsumeRace:
    def test_only_one_of_two_concurrent_consumers_wins(self):
        """Reuse of Aria's Fix A pattern (find_and_consume_atomically):
        BEGIN IMMEDIATE serializes; whichever consumer wins the lock
        commits first; the other re-scans and sees already-consumed.
        """
        mid = emit_marker("op_bypass", "edit:x.py")
        results: list[ConsumeVerdict] = []
        lock = threading.Lock()

        def try_consume():
            v = consume_marker(mid, "edit:x.py")
            with lock:
                results.append(v)

        t1 = threading.Thread(target=try_consume)
        t2 = threading.Thread(target=try_consume)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = sorted(v.outcome for v in results)
        assert outcomes == ["already_consumed", "consumed"], (
            f"expected exactly one consumed + one already_consumed, got: {outcomes}"
        )


class TestFailLoudOnLookupCrash:
    def test_find_raises_StateMarkerLookupError_on_ledger_crash(self, monkeypatch):
        """Aletheia root pattern #2: a crashed lookup must not return
        the same shape as a clean empty lookup. Must RAISE, not return None.
        """

        class ExplodingConn:
            def execute(self, *args, **kwargs):
                raise sqlite3_like_error("simulated ledger crash")

            def close(self):
                pass

        def bad_connection(*args, **kwargs):
            return ExplodingConn()

        monkeypatch.setattr(state_markers, "get_connection", bad_connection)
        with pytest.raises(StateMarkerLookupError):
            find_active_marker("op_bypass")


def sqlite3_like_error(msg: str) -> Exception:
    """A generic Exception to simulate a ledger-lookup crash. Kept as
    a helper so the fail-loud test's intent is explicit."""
    return RuntimeError(msg)
