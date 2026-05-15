"""Regression-pin tests for the claim-triage store."""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import claim_triage as ct


@pytest.fixture(autouse=True)
def isolate_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ct, "_STORE_FILE", tmp_path / "claim_triage.json")


def test_add_and_list_entry() -> None:
    ct.add_entry("X is shipped", ct.TriageStatus.VERIFIED, "test_x.py green", "tests/test_x.py")
    entries = ct.list_entries()
    assert len(entries) == 1
    assert entries[0]["status"] == "VERIFIED"
    assert entries[0]["claim"] == "X is shipped"


def test_summary_counts() -> None:
    ct.add_entry("a", ct.TriageStatus.VERIFIED)
    ct.add_entry("b", ct.TriageStatus.SUSPECT)
    ct.add_entry("c", ct.TriageStatus.SUSPECT)
    ct.add_entry("d", ct.TriageStatus.REMOVED)
    counts = ct.summary()
    assert counts["VERIFIED"] == 1
    assert counts["SUSPECT"] == 2
    assert counts["REMOVED"] == 1


def test_status_transition_latest_wins() -> None:
    """LOAD-BEARING: an entry transitioning SUSPECT → VERIFIED counts as VERIFIED."""
    ct.add_entry("x", ct.TriageStatus.SUSPECT, "no test yet")
    ct.add_entry("x", ct.TriageStatus.VERIFIED, "test now exists", "tests/test_x.py")
    counts = ct.summary()
    assert counts["VERIFIED"] == 1
    assert counts["SUSPECT"] == 0


def test_filter_by_status() -> None:
    ct.add_entry("a", ct.TriageStatus.VERIFIED)
    ct.add_entry("b", ct.TriageStatus.SUSPECT)
    suspect = ct.list_entries(ct.TriageStatus.SUSPECT)
    assert len(suspect) == 1
    assert suspect[0]["claim"] == "b"


def test_empty_claim_rejected() -> None:
    with pytest.raises(ValueError):
        ct.add_entry("", ct.TriageStatus.SUSPECT)


def test_guardrail_marker_present() -> None:
    src = Path(ct.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
