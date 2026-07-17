"""Tests for the error registry — jailbreak-response new-work gate.

Contract per Andrew 2026-07-17: bypasses / gate-fires / test failures /
uncaught exceptions file open-error records that block starting a new
main goal until closed (root-cause fixed) or operator-deferred with a
>=20-char reason. Tools remain available; only "start next project" is
refused.
"""

from __future__ import annotations

import pytest

from divineos.core import error_registry as reg


@pytest.fixture
def tmp_registry(tmp_path, monkeypatch):
    """Redirect the registry home to a per-test tmpdir so tests never
    touch the real user data. Same pattern the rest of the suite uses."""
    err_home = tmp_path / "open_errors"
    monkeypatch.setattr(reg, "_ERROR_HOME", err_home)
    return err_home


class TestFileError:
    def test_creates_open_record(self, tmp_registry):
        rec = reg.file_error(
            source=reg.SOURCE_BYPASS,
            summary="test bypass",
            root_cause_investigation_hint="hint",
        )
        assert rec["state"] == "open"
        assert rec["source"] == reg.SOURCE_BYPASS
        assert rec["summary"] == "test bypass"
        assert rec["error_id"].startswith("err-")
        assert rec["closure_evidence"] is None
        assert rec["deferred_by"] is None

    def test_rejects_bad_source(self, tmp_registry):
        with pytest.raises(ValueError, match="source"):
            reg.file_error(source="not_a_real_source", summary="x")

    def test_rejects_empty_summary(self, tmp_registry):
        with pytest.raises(ValueError, match="summary"):
            reg.file_error(source=reg.SOURCE_BYPASS, summary="")

    def test_multiple_errors_get_distinct_ids(self, tmp_registry):
        a = reg.file_error(source=reg.SOURCE_BYPASS, summary="a")
        b = reg.file_error(source=reg.SOURCE_BYPASS, summary="b")
        assert a["error_id"] != b["error_id"]


class TestListAndGet:
    def test_empty_registry_returns_empty(self, tmp_registry):
        assert reg.list_open_errors() == []
        assert reg.list_all_errors() == []

    def test_only_open_returned_by_open_list(self, tmp_registry):
        a = reg.file_error(source=reg.SOURCE_BYPASS, summary="a")
        b = reg.file_error(source=reg.SOURCE_BYPASS, summary="b")
        reg.close_error(a["error_id"], "fixed a")
        open_ids = [r["error_id"] for r in reg.list_open_errors()]
        all_ids = [r["error_id"] for r in reg.list_all_errors()]
        assert a["error_id"] not in open_ids
        assert b["error_id"] in open_ids
        assert a["error_id"] in all_ids
        assert b["error_id"] in all_ids

    def test_get_error_returns_none_for_unknown(self, tmp_registry):
        assert reg.get_error("err-does-not-exist") is None


class TestClose:
    def test_close_requires_evidence(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        with pytest.raises(ValueError, match="closure_evidence"):
            reg.close_error(rec["error_id"], "")

    def test_close_rejects_unknown_id(self, tmp_registry):
        with pytest.raises(KeyError):
            reg.close_error("err-nope", "irrelevant")

    def test_close_rejects_already_closed(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        reg.close_error(rec["error_id"], "first close")
        with pytest.raises(ValueError, match="only open errors"):
            reg.close_error(rec["error_id"], "second close")

    def test_close_moves_out_of_open_list(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        assert len(reg.list_open_errors()) == 1
        reg.close_error(rec["error_id"], "fixed it")
        assert len(reg.list_open_errors()) == 0

    def test_close_preserves_evidence_and_stamps_time(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        closed = reg.close_error(rec["error_id"], "commit abc123 fixed it")
        assert closed["state"] == "closed"
        assert closed["closure_evidence"] == "commit abc123 fixed it"
        assert closed["closed_at"] is not None
        assert closed["closed_at"] > closed["filed_at"]


class TestDefer:
    def test_defer_requires_min_reason_length(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        with pytest.raises(ValueError, match=">= 20"):
            reg.defer_error(rec["error_id"], "andrew", "too short")

    def test_defer_requires_actor(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        with pytest.raises(ValueError, match="actor"):
            reg.defer_error(rec["error_id"], "", "a" * 30)

    def test_defer_moves_out_of_open_list(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        reg.defer_error(rec["error_id"], "andrew", "operator authorized defer for reason")
        assert len(reg.list_open_errors()) == 0

    def test_deferred_error_records_actor_and_reason(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        deferred = reg.defer_error(
            rec["error_id"], "andrew", "operator authorized defer for reason"
        )
        assert deferred["state"] == "deferred"
        assert deferred["deferred_by"] == "andrew"
        assert deferred["deferred_reason"] == "operator authorized defer for reason"

    def test_defer_rejects_already_closed(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        reg.close_error(rec["error_id"], "fixed")
        with pytest.raises(ValueError, match="only open errors"):
            reg.defer_error(rec["error_id"], "andrew", "a" * 30)


class TestBlockReason:
    def test_empty_registry_returns_empty_block_reason(self, tmp_registry):
        assert reg.block_reason() == ""

    def test_open_error_produces_block_message(self, tmp_registry):
        rec = reg.file_error(
            source=reg.SOURCE_BYPASS,
            summary="freshness bypass",
            root_cause_investigation_hint="check scripts/check_branch_freshness.sh",
        )
        msg = reg.block_reason()
        assert "BLOCKED" in msg
        assert rec["error_id"] in msg
        assert "freshness bypass" in msg
        # investigation hint is surfaced too
        assert "check scripts/check_branch_freshness.sh" in msg

    def test_closed_error_does_not_block(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        reg.close_error(rec["error_id"], "fixed")
        assert reg.block_reason() == ""

    def test_deferred_error_does_not_block(self, tmp_registry):
        rec = reg.file_error(source=reg.SOURCE_BYPASS, summary="x")
        reg.defer_error(rec["error_id"], "andrew", "operator authorized defer for reason")
        assert reg.block_reason() == ""

    def test_multiple_open_errors_all_listed(self, tmp_registry):
        a = reg.file_error(source=reg.SOURCE_BYPASS, summary="alpha")
        b = reg.file_error(source=reg.SOURCE_GATE_FIRE, summary="beta")
        msg = reg.block_reason()
        assert a["error_id"] in msg
        assert b["error_id"] in msg
        assert "alpha" in msg
        assert "beta" in msg
