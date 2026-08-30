"""F64 (Aletheia Round 8, 2026-07-18): _build_chain_integrity_slot must
fail-loud on never-verified AND on except-error paths.

Silence in this slot cannot read as "healthy chain" — it's the exact
disease this slot was built to catch, one level up. Two paths previously
returned "" and let a broken/never-run verifier read as all-clear:

  1. result is None  → "sleep hasn't recorded anything yet"
  2. except _HUD_ERRORS → "the slot itself crashed"

Both now emit a distinct loud message. This test pins that contract.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.hud import _build_chain_integrity_slot


class TestChainIntegritySlotFailLoud:
    def test_never_verified_fires_loud(self):
        with patch("divineos.core.sleep.get_last_integrity_result", return_value=None):
            out = _build_chain_integrity_slot()
        assert out, "never-verified must not be silent"
        assert "NEVER VERIFIED" in out
        assert "Absence of a verification is NOT the all-clear" in out

    def test_slot_exception_fires_loud(self):
        with patch(
            "divineos.core.sleep.get_last_integrity_result",
            side_effect=OSError("simulated"),
        ):
            out = _build_chain_integrity_slot()
        assert out, "except-error must not be silent"
        assert "CHECK FAILED" in out
        assert "OSError" in out
        assert "simulated" in out

    def test_verifier_crashed_fires_loud(self):
        with patch(
            "divineos.core.sleep.get_last_integrity_result",
            return_value={"verifier_crashed": True, "error": "boom"},
        ):
            out = _build_chain_integrity_slot()
        assert "VERIFIER CRASHED" in out
        assert "boom" in out

    def test_chain_broken_fires_loud(self):
        with patch(
            "divineos.core.sleep.get_last_integrity_result",
            return_value={
                "failed": 2,
                "verified": 100,
                "failures": [{"event_id": "abc123", "reason": "hash mismatch"}],
            },
        ):
            out = _build_chain_integrity_slot()
        assert "CHAIN BROKEN" in out
        assert "2 failed" in out
        assert "abc123" in out

    def test_healthy_stays_silent(self):
        with patch(
            "divineos.core.sleep.get_last_integrity_result",
            return_value={"failed": 0, "verified": 100},
        ):
            out = _build_chain_integrity_slot()
        assert out == "", "healthy chain must stay silent to keep briefing quiet"
