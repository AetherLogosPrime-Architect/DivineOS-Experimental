"""Tests for F14/F52 auto-verify integrity check.

Aletheia named the gap: the ledger has tamper-evidence but nothing ever
checks it. This test suite pins the wire — sleep runs verify_all_events
on every cycle, writes a marker, and the HUD slot surfaces LOUDLY when
the chain is broken or the verifier itself crashed.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def isolated_marker(tmp_path, monkeypatch):
    """Route the integrity marker to a scratch marker path."""
    marker_dir = tmp_path / "markers"
    marker_dir.mkdir()

    def _fake_marker_path(name):
        return marker_dir / name

    monkeypatch.setattr(
        "divineos.core.operating_loop_audit.marker_path",
        _fake_marker_path,
    )
    return marker_dir


class TestIntegrityPhase:
    """Sleep phase records verify result on the DreamReport + marker file."""

    def test_phase_records_result_on_report(self, isolated_marker, monkeypatch):
        from divineos.core.sleep import DreamReport, _phase_integrity_check

        def _fake_verify_all_events(*_a, **_kw):
            return {"passed": 40, "failed": 0, "skipped": 5, "failures": []}

        monkeypatch.setattr(
            "divineos.core.ledger_verify.verify_all_events",
            _fake_verify_all_events,
        )

        report = DreamReport()
        _phase_integrity_check(report)
        assert report.integrity_events_verified == 40
        assert report.integrity_events_failed == 0
        assert report.integrity_failures == []

    def test_phase_records_failures_on_report(self, isolated_marker, monkeypatch):
        from divineos.core.sleep import DreamReport, _phase_integrity_check

        def _fake_verify_all_events(*_a, **_kw):
            return {
                "passed": 20,
                "failed": 2,
                "skipped": 0,
                "failures": [
                    {"event_id": "abc123", "reason": "hash mismatch", "type": "hash_mismatch"},
                    {"event_id": "def456", "reason": "payload invalid", "type": "payload_invalid"},
                ],
            }

        monkeypatch.setattr(
            "divineos.core.ledger_verify.verify_all_events",
            _fake_verify_all_events,
        )

        report = DreamReport()
        _phase_integrity_check(report)
        assert report.integrity_events_verified == 22
        assert report.integrity_events_failed == 2
        assert len(report.integrity_failures) == 2

    def test_phase_writes_marker_file(self, isolated_marker, monkeypatch):
        from divineos.core.sleep import DreamReport, _phase_integrity_check

        def _fake_verify_all_events(*_a, **_kw):
            return {
                "passed": 10,
                "failed": 1,
                "skipped": 0,
                "failures": [{"event_id": "x", "reason": "y"}],
            }

        monkeypatch.setattr(
            "divineos.core.ledger_verify.verify_all_events",
            _fake_verify_all_events,
        )

        report = DreamReport()
        _phase_integrity_check(report)
        marker = isolated_marker / "ledger_integrity_last_run.json"
        assert marker.exists()
        data = json.loads(marker.read_text(encoding="utf-8"))
        assert data["failed"] == 1
        assert data["verified"] == 11
        assert "ts" in data

    def test_phase_failsoft_when_verifier_crashes(self, isolated_marker, monkeypatch):
        """A verifier crash records the crash in the marker but does NOT
        crash the sleep pipeline itself."""
        from divineos.core.sleep import DreamReport, _phase_integrity_check

        def _fake_verify_all_events(*_a, **_kw):
            raise RuntimeError("simulated DB failure")

        monkeypatch.setattr(
            "divineos.core.ledger_verify.verify_all_events",
            _fake_verify_all_events,
        )

        report = DreamReport()
        # Must not raise
        _phase_integrity_check(report)
        marker = isolated_marker / "ledger_integrity_last_run.json"
        assert marker.exists()
        data = json.loads(marker.read_text(encoding="utf-8"))
        assert data["verifier_crashed"] is True
        assert "simulated DB failure" in data["error"]


class TestGetLastIntegrityResult:
    """Public accessor for the HUD slot."""

    def test_none_when_marker_absent(self, isolated_marker):
        from divineos.core.sleep import get_last_integrity_result

        assert get_last_integrity_result() is None

    def test_returns_dict_when_marker_present(self, isolated_marker):
        from divineos.core.sleep import get_last_integrity_result

        marker = isolated_marker / "ledger_integrity_last_run.json"
        marker.write_text(
            json.dumps({"ts": 123.0, "verified": 10, "failed": 0, "failures": [], "skipped": 2}),
            encoding="utf-8",
        )
        result = get_last_integrity_result()
        assert result is not None
        assert result["verified"] == 10

    def test_none_when_marker_corrupted(self, isolated_marker):
        from divineos.core.sleep import get_last_integrity_result

        marker = isolated_marker / "ledger_integrity_last_run.json"
        marker.write_text("not valid json {{", encoding="utf-8")
        assert get_last_integrity_result() is None


class TestChainIntegrityHudSlot:
    """HUD slot hidden on healthy, loud on broken/crashed."""

    def test_slot_hidden_when_never_run(self, isolated_marker):
        from divineos.core.hud import _build_chain_integrity_slot

        assert _build_chain_integrity_slot() == ""

    def test_slot_hidden_when_healthy(self, isolated_marker):
        from divineos.core.hud import _build_chain_integrity_slot

        marker = isolated_marker / "ledger_integrity_last_run.json"
        marker.write_text(
            json.dumps({"ts": 123.0, "verified": 100, "failed": 0, "failures": [], "skipped": 5}),
            encoding="utf-8",
        )
        assert _build_chain_integrity_slot() == ""

    def test_slot_fires_when_failures_present(self, isolated_marker):
        from divineos.core.hud import _build_chain_integrity_slot

        marker = isolated_marker / "ledger_integrity_last_run.json"
        marker.write_text(
            json.dumps(
                {
                    "ts": 123.0,
                    "verified": 50,
                    "failed": 3,
                    "failures": [
                        {"event_id": "aaabbbccc111", "reason": "hash mismatch"},
                        {"event_id": "dddeeefff222", "reason": "payload invalid"},
                    ],
                    "skipped": 5,
                }
            ),
            encoding="utf-8",
        )
        out = _build_chain_integrity_slot()
        assert "CHAIN BROKEN" in out
        assert "3 failed" in out
        assert "aaabbbccc111" in out

    def test_slot_fires_when_verifier_crashed(self, isolated_marker):
        from divineos.core.hud import _build_chain_integrity_slot

        marker = isolated_marker / "ledger_integrity_last_run.json"
        marker.write_text(
            json.dumps({"ts": 123.0, "verifier_crashed": True, "error": "RuntimeError: DB gone"}),
            encoding="utf-8",
        )
        out = _build_chain_integrity_slot()
        assert "VERIFIER CRASHED" in out
        assert "RuntimeError" in out


class TestPhaseRegistered:
    """The integrity phase must be in the sleep pipeline's registered list."""

    def test_integrity_phase_in_phases_list(self):
        from divineos.core.sleep import _PHASES

        phase_names = [name for name, _ in _PHASES]
        assert "integrity_check" in phase_names

    def test_slot_registered_in_hud(self):
        from divineos.core.hud import SLOT_BUILDERS, SLOT_ORDER

        assert "chain_integrity" in SLOT_BUILDERS
        assert "chain_integrity" in SLOT_ORDER
