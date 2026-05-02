"""Tests for VOID separate hash-chained ledger."""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

import pytest

from divineos.core.void import ledger as void_ledger


@pytest.fixture
def void_db(tmp_path):
    return tmp_path / "void_ledger.db"


class TestSchema:
    def test_connect_creates_schema(self, void_db) -> None:
        with void_ledger.connect(path=void_db) as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {r[0] for r in rows}
        assert "void_events" in names

    def test_indexes_created(self, void_db) -> None:
        with void_ledger.connect(path=void_db) as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        names = {r[0] for r in rows}
        assert "idx_void_events_ts" in names
        assert "idx_void_events_type" in names
        assert "idx_void_events_persona" in names


class TestAppendEvent:
    def test_first_event_has_no_prev_hash(self, void_db) -> None:
        result = void_ledger.append_event(
            "VOID_INVOCATION_STARTED",
            {"target": "test"},
            persona="sycophant",
            path=void_db,
        )
        assert result["prev_hash"] is None
        assert result["content_hash"]
        assert result["event_id"]

    def test_subsequent_events_chain(self, void_db) -> None:
        r1 = void_ledger.append_event(
            "VOID_INVOCATION_STARTED", {"a": 1}, persona="sycophant", path=void_db
        )
        r2 = void_ledger.append_event("VOID_FINDING", {"b": 2}, persona="sycophant", path=void_db)
        assert r2["prev_hash"] == r1["content_hash"]
        assert r2["content_hash"] != r1["content_hash"]

    def test_persona_stored(self, void_db) -> None:
        r = void_ledger.append_event("VOID_FINDING", {"x": 1}, persona="nyarlathotep", path=void_db)
        ev = void_ledger.get_event(r["event_id"], path=void_db)
        assert ev["persona"] == "nyarlathotep"


class TestListEvents:
    def test_list_newest_first(self, void_db) -> None:
        void_ledger.append_event("VOID_FINDING", {"i": 1}, path=void_db)
        void_ledger.append_event("VOID_FINDING", {"i": 2}, path=void_db)
        rows = void_ledger.list_events(path=void_db)
        assert len(rows) == 2
        assert rows[0]["ts"] >= rows[1]["ts"]

    def test_filter_by_event_type(self, void_db) -> None:
        void_ledger.append_event("VOID_FINDING", {}, path=void_db)
        void_ledger.append_event("VOID_SHRED", {}, path=void_db)
        rows = void_ledger.list_events(event_type="VOID_SHRED", path=void_db)
        assert len(rows) == 1
        assert rows[0]["event_type"] == "VOID_SHRED"

    def test_filter_by_persona(self, void_db) -> None:
        void_ledger.append_event("VOID_FINDING", {}, persona="sycophant", path=void_db)
        void_ledger.append_event("VOID_FINDING", {}, persona="phisher", path=void_db)
        rows = void_ledger.list_events(persona="phisher", path=void_db)
        assert len(rows) == 1
        assert rows[0]["persona"] == "phisher"

    def test_limit_respected(self, void_db) -> None:
        for i in range(5):
            void_ledger.append_event("VOID_FINDING", {"i": i}, path=void_db)
        rows = void_ledger.list_events(limit=2, path=void_db)
        assert len(rows) == 2


class TestGetEvent:
    def test_get_existing(self, void_db) -> None:
        r = void_ledger.append_event("VOID_FINDING", {"k": "v"}, path=void_db)
        ev = void_ledger.get_event(r["event_id"], path=void_db)
        assert ev is not None
        assert ev["event_id"] == r["event_id"]

    def test_get_missing_returns_none(self, void_db) -> None:
        assert void_ledger.get_event("nope", path=void_db) is None


class TestVerifyChain:
    def test_clean_chain_verifies(self, void_db) -> None:
        for i in range(3):
            void_ledger.append_event("VOID_FINDING", {"i": i}, path=void_db)
        ok, broken = void_ledger.verify_chain(path=void_db)
        assert ok is True
        assert broken == []

    def test_empty_chain_verifies(self, void_db) -> None:
        with void_ledger.connect(path=void_db):
            pass
        ok, broken = void_ledger.verify_chain(path=void_db)
        assert ok is True
        assert broken == []

    def test_tampered_payload_detected(self, void_db) -> None:
        r = void_ledger.append_event("VOID_FINDING", {"k": "v"}, path=void_db)
        void_ledger.append_event("VOID_FINDING", {"k": "w"}, path=void_db)
        # Tamper with the first event's payload directly.
        conn = sqlite3.connect(str(void_db))
        conn.execute(
            "UPDATE void_events SET payload = ? WHERE event_id = ?",
            (json.dumps({"tampered": True}), r["event_id"]),
        )
        conn.commit()
        conn.close()
        ok, broken = void_ledger.verify_chain(path=void_db)
        assert ok is False
        assert r["event_id"] in broken

    def test_broken_prev_hash_detected(self, void_db) -> None:
        void_ledger.append_event("VOID_FINDING", {"i": 1}, path=void_db)
        r2 = void_ledger.append_event("VOID_FINDING", {"i": 2}, path=void_db)
        conn = sqlite3.connect(str(void_db))
        conn.execute(
            "UPDATE void_events SET prev_hash = ? WHERE event_id = ?",
            ("deadbeef", r2["event_id"]),
        )
        conn.commit()
        conn.close()
        ok, broken = void_ledger.verify_chain(path=void_db)
        assert ok is False
        assert r2["event_id"] in broken


class TestDbPath:
    def test_env_override(self, tmp_path, monkeypatch) -> None:
        custom = tmp_path / "custom_void.db"
        monkeypatch.setenv("DIVINEOS_VOID_DB", str(custom))
        assert void_ledger.db_path() == custom

    def test_default_under_data_dir(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_VOID_DB", raising=False)
        p = void_ledger.db_path()
        assert p.name == "void_ledger.db"
        assert p.parent.name == "data"


class TestMainLedgerPointer:
    def test_writes_pointer_event(self, void_db) -> None:
        with patch("divineos.core.ledger.log_event") as mock_log:
            void_ledger.write_main_ledger_pointer("fid-123", "hash-abc", actor="void")
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == "VOID_SEALED"
        assert args[1] == "void"
        payload = args[2]
        assert payload["void_finding_id"] == "fid-123"
        assert payload["void_ledger_hash"] == "hash-abc"

    def test_fails_soft_when_main_unavailable(self) -> None:
        with patch("divineos.core.ledger.log_event", side_effect=RuntimeError("no main")):
            # Must not raise.
            void_ledger.write_main_ledger_pointer("fid", "hash")
