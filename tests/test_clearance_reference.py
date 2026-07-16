"""Tests for ClearanceReference — the UNLOCK-CONTINGENT slot (task #4).

Aria's audit 2026-07-15: the primitive's cleared_by field is free-text
and carries self-attestation without evidence. Aletheia's self-caught
round-cite fabrication 2026-07-16 proved the vulnerability by inhabiting
it. Class-closer: "a cite is not valid because it LOOKS right; it's valid
because it RESOLVES."
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    ClearanceReference,
    EvidenceRecord,
)
from divineos.hooks.gate_event_ledger import (
    _resolve_audit_round,
    _resolve_claim,
    _resolve_commit,
    _resolve_file_lines,
    _resolve_ledger_event,
    record_gate_clearance,
    resolve_clearance_reference,
)


def _make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        gate_name="test_gate",
        matched_shape="test",
        specific_evidence="test",
        required_action="test",
    )


class TestClearanceReferenceType:
    def test_is_frozen_dataclass(self) -> None:
        ref = ClearanceReference(kind="ledger_event", identifier="evt_123")
        try:
            ref.kind = "something_else"  # type: ignore[misc]
            raise AssertionError("expected frozen-dataclass mutation to raise")
        except Exception:
            pass

    def test_has_kind_and_identifier(self) -> None:
        ref = ClearanceReference(kind="audit_round", identifier="round-abc123")
        assert ref.kind == "audit_round"
        assert ref.identifier == "round-abc123"


class TestResolverRegistry:
    def test_unknown_kind_returns_false(self) -> None:
        ref = ClearanceReference(kind="unknown_kind_never_registered", identifier="x")
        assert resolve_clearance_reference(ref) is False

    def test_custom_registry_used_when_passed(self) -> None:
        ref = ClearanceReference(kind="custom", identifier="hit")
        custom = {"custom": lambda ident: ident == "hit"}
        assert resolve_clearance_reference(ref, registry=custom) is True

    def test_resolver_exception_returns_false(self) -> None:
        def _raise(_ident: str) -> bool:
            raise RuntimeError("simulated resolver crash")

        ref = ClearanceReference(kind="custom", identifier="x")
        assert resolve_clearance_reference(ref, registry={"custom": _raise}) is False


class TestLedgerEventResolver:
    def test_empty_id_returns_false(self) -> None:
        assert _resolve_ledger_event("") is False

    def test_missing_id_returns_false(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.get_events") as m:
            m.return_value = [{"event_id": "other_id"}]
            assert _resolve_ledger_event("real_target_id") is False

    def test_present_id_returns_true(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.get_events") as m:
            m.return_value = [{"event_id": "target_id_here"}, {"event_id": "other"}]
            assert _resolve_ledger_event("target_id_here") is True


class TestAuditRoundResolver:
    def test_empty_returns_false(self) -> None:
        assert _resolve_audit_round("") is False

    def test_present_round_returns_true(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.get_events") as m:
            m.return_value = [{"payload": {"round_id": "round-b8bfe01704f9"}}]
            assert _resolve_audit_round("round-b8bfe01704f9") is True

    def test_missing_round_returns_false(self) -> None:
        """The Aletheia self-catch class — prose-generated round-id that
        never was filed does not resolve."""
        with patch("divineos.hooks.gate_event_ledger.get_events") as m:
            m.return_value = [{"payload": {"round_id": "round-something-else"}}]
            assert _resolve_audit_round("round-c7f2a9e4d1b8") is False


class TestClaimResolver:
    def test_empty_returns_false(self) -> None:
        assert _resolve_claim("") is False

    def test_present_claim_returns_true_via_claim_id(self) -> None:
        with patch("divineos.hooks.gate_event_ledger.get_events") as m:
            m.return_value = [{"payload": {"claim_id": "abc"}}]
            assert _resolve_claim("abc") is True


class TestCommitResolver:
    def test_empty_returns_false(self) -> None:
        assert _resolve_commit("") is False

    def test_non_hex_returns_false(self) -> None:
        assert _resolve_commit("zzznotasha") is False

    def test_uses_git_cat_file(self) -> None:
        with patch("subprocess.run") as m:
            mock_result = type("Result", (), {"returncode": 0})()
            m.return_value = mock_result
            assert _resolve_commit("abc123def456") is True


class TestFileLinesResolver:
    def test_empty_returns_false(self) -> None:
        assert _resolve_file_lines("") is False

    def test_no_colon_returns_false(self) -> None:
        assert _resolve_file_lines("path/only.md") is False

    def test_missing_file_returns_false(self) -> None:
        assert _resolve_file_lines("/nonexistent/path/for/test.py:1") is False

    def test_present_file_valid_line_returns_true(self, tmp_path) -> None:
        p = tmp_path / "test.txt"
        p.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
        assert _resolve_file_lines(f"{p}:2") is True
        assert _resolve_file_lines(f"{p}:1-3") is True

    def test_out_of_bounds_returns_false(self, tmp_path) -> None:
        p = tmp_path / "small.txt"
        p.write_text("just one line\n", encoding="utf-8")
        assert _resolve_file_lines(f"{p}:5") is False


class TestRecordGateClearanceWritesVerifiedField:
    def test_resolved_reference_writes_verified_true(self) -> None:
        ref = ClearanceReference(kind="ledger_event", identifier="real_id")
        clearance = ClearanceRecord(
            gate_name="test_gate",
            cleared_by="fixed it",
            original_evidence=_make_evidence(),
            reference=ref,
        )
        with (
            patch("divineos.hooks.gate_event_ledger.log_event") as mock_log,
            patch("divineos.hooks.gate_event_ledger.get_events") as mock_get,
        ):
            mock_get.return_value = [{"event_id": "real_id"}]
            mock_log.return_value = "evt_new"
            record_gate_clearance(clearance)
        _, kwargs = mock_log.call_args
        payload = kwargs["payload"]
        assert payload["verified"] is True
        assert payload["reference"]["resolved"] is True

    def test_unresolvable_reference_writes_verified_false(self) -> None:
        ref = ClearanceReference(kind="audit_round", identifier="round-phantom")
        clearance = ClearanceRecord(
            gate_name="test_gate",
            cleared_by="fixed it",
            original_evidence=_make_evidence(),
            reference=ref,
        )
        with (
            patch("divineos.hooks.gate_event_ledger.log_event") as mock_log,
            patch("divineos.hooks.gate_event_ledger.get_events") as mock_get,
        ):
            mock_get.return_value = []
            mock_log.return_value = "evt_new"
            record_gate_clearance(clearance)
        _, kwargs = mock_log.call_args
        payload = kwargs["payload"]
        assert payload["verified"] is False
        assert payload["reference"]["resolved"] is False

    def test_no_reference_is_backwards_compat(self) -> None:
        clearance = ClearanceRecord(
            gate_name="test_gate",
            cleared_by="fixed it",
            original_evidence=_make_evidence(),
            reference=None,
        )
        with patch("divineos.hooks.gate_event_ledger.log_event") as mock_log:
            mock_log.return_value = "evt_new"
            record_gate_clearance(clearance)
        _, kwargs = mock_log.call_args
        payload = kwargs["payload"]
        assert payload["reference"] is None
        assert payload["verified"] is False
