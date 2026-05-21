"""Tests for emergency_bypass — the LOGGED/REPORTED/ADDRESSED/FIXED loop.

Aletheia hidden-issues audit 2026-05-20 (Finding B): this substrate-shaping
module shipped with one caller and zero tests. The fail-mode it exists to
prevent — bare flag-flipping passed off as "emergency" — rests on the
>=20-char reason guard, which had no test pinning it.
"""

from __future__ import annotations

import pytest

from divineos.core.emergency_bypass import EmergencyBypassReport, record_emergency_use


class TestReasonGuard:
    """The core discipline: the bypass refuses to fire without a real
    operator-named reason. This is the line between emergency and escape."""

    def test_empty_reason_rejected(self):
        with pytest.raises(ValueError, match="reason must be"):
            record_emergency_use("some-gate", "DIVINEOS_SKIP_X", "")

    def test_whitespace_reason_rejected(self):
        with pytest.raises(ValueError):
            record_emergency_use("some-gate", "DIVINEOS_SKIP_X", "       ")

    def test_short_reason_rejected(self):
        # 19 chars — one under the threshold.
        with pytest.raises(ValueError):
            record_emergency_use("some-gate", "DIVINEOS_SKIP_X", "x" * 19)

    def test_exactly_20_chars_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        report = record_emergency_use("some-gate", "DIVINEOS_SKIP_X", "x" * 20)
        assert isinstance(report, EmergencyBypassReport)


class TestReportShape:
    def test_valid_use_returns_report(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        reason = "prep-relay gate malfunctioned mid-push, hotfix required now"
        report = record_emergency_use("prep-relay-narrow-range", "DIVINEOS_SKIP_RELAY", reason)
        assert report.gate_name == "prep-relay-narrow-range"
        assert report.env_var == "DIVINEOS_SKIP_RELAY"
        assert report.reason == reason  # already stripped, no surrounding ws
        assert isinstance(report.telemetry_logged, bool)
        # claim_id / psf_id are fail-soft — strings (possibly empty in a bare
        # test env where the claim/psf subsystems aren't initialized).
        assert isinstance(report.claim_id, str)
        assert isinstance(report.psf_id, str)

    def test_reason_is_stripped(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        report = record_emergency_use(
            "g", "ENV", "   a genuinely long enough reason string   "
        )
        assert report.reason == "a genuinely long enough reason string"

    def test_telemetry_logged_when_home_writable(self, tmp_path, monkeypatch):
        # With DIVINEOS_HOME pointed at a writable tmp dir, the LOGGED step
        # (bypass_telemetry.record_bypass) should succeed.
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        report = record_emergency_use("g", "ENV_LOGGED", "another sufficiently long reason here")
        assert report.telemetry_logged is True
        # And the event should be queryable through the telemetry surface.
        from divineos.core.bypass_telemetry import bypass_rate

        stats = bypass_rate()
        assert stats["total_events"] >= 1
