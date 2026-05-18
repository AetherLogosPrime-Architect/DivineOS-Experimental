"""Regression-pin tests for the triage briefing surface.

Channel-shape (Andrew 2026-05-14): SUSPECT count must be loud in
every briefing — that's what makes the cheap-close of 'it's fine now'
expensive. These tests verify the slot is registered in SLOT_ORDER
and the build function produces output when SUSPECT entries exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import claim_triage as ct
from divineos.core import hud


@pytest.fixture(autouse=True)
def isolate_triage_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ct, "_STORE_FILE", tmp_path / "claim_triage.json")


def test_triage_in_slot_order() -> None:
    """LOAD-BEARING: 'triage' must be in SLOT_ORDER and mapped to a builder."""
    assert "triage" in hud.SLOT_ORDER
    # Find the slot-builder map. It's the dict at module level mapping
    # slot names to _build_* functions.
    import inspect

    for name, obj in inspect.getmembers(hud):
        if isinstance(obj, dict) and "claims" in obj and callable(obj.get("claims")):
            assert "triage" in obj, "triage slot not registered in builder map"
            assert callable(obj["triage"])
            return
    raise AssertionError("could not find slot-builder dict in hud module")


def test_slot_empty_when_no_entries() -> None:
    """Slot returns empty string when there's no triage activity."""
    result = hud._build_triage_slot()
    assert result == ""


def test_slot_shows_suspect_count() -> None:
    """LOAD-BEARING: when SUSPECT entries exist, the slot makes them visible."""
    ct.add_entry("x is shipped", ct.TriageStatus.SUSPECT, "not verified")
    ct.add_entry("y is shipped", ct.TriageStatus.VERIFIED, "test green", "tests/test_y.py")
    result = hud._build_triage_slot()
    assert "SUSPECT" in result
    assert "x is shipped" in result
    assert "1 verified" in result.lower() or "1 verified" in result


def test_slot_shows_all_verified_message() -> None:
    """When everything is VERIFIED, slot still appears with congratulatory note."""
    ct.add_entry("a", ct.TriageStatus.VERIFIED, "test green", "tests/test_a.py")
    result = hud._build_triage_slot()
    assert "VERIFIED" in result
    assert "All known claims" in result or "0 SUSPECT" in result


def test_status_transition_reflected() -> None:
    """SUSPECT → VERIFIED transition reduces SUSPECT count in the surface."""
    ct.add_entry("x", ct.TriageStatus.SUSPECT, "needs walking")
    out1 = hud._build_triage_slot()
    assert "SUSPECT" in out1 and "x" in out1
    ct.add_entry("x", ct.TriageStatus.VERIFIED, "now verified", "tests/test_x.py")
    out2 = hud._build_triage_slot()
    # The 'x' should now be VERIFIED — no longer listed under SUSPECT
    assert "0 SUSPECT" in out2 or "All known claims" in out2
