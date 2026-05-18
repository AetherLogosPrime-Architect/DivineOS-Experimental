"""Regression-pin tests for the claim-triage store.

Updated 2026-05-15 (Aletheia Finding 50 + gap 2): tests now exercise
the required actor field and the external-only restriction on
VERIFIED transitions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import claim_triage as ct


@pytest.fixture(autouse=True)
def isolate_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ct, "_STORE_FILE", tmp_path / "claim_triage.json")


# ── Original contract tests (updated to pass actor) ───────────────


def test_add_and_list_entry() -> None:
    ct.add_entry(
        "X is shipped",
        ct.TriageStatus.VERIFIED,
        actor="aletheia",
        notes="test_x.py green",
        test_path="tests/test_x.py",
    )
    entries = ct.list_entries()
    assert len(entries) == 1
    assert entries[0]["status"] == "VERIFIED"
    assert entries[0]["claim"] == "X is shipped"
    assert entries[0]["actor"] == "aletheia"


def test_summary_counts() -> None:
    ct.add_entry("a", ct.TriageStatus.VERIFIED, actor="aletheia")
    ct.add_entry("b", ct.TriageStatus.SUSPECT, actor="aether")
    ct.add_entry("c", ct.TriageStatus.SUSPECT, actor="aether")
    ct.add_entry("d", ct.TriageStatus.REMOVED, actor="aether")
    counts = ct.summary()
    assert counts["VERIFIED"] == 1
    assert counts["SUSPECT"] == 2
    assert counts["REMOVED"] == 1


def test_status_transition_latest_wins() -> None:
    """LOAD-BEARING: SUSPECT → VERIFIED transition counts as VERIFIED."""
    ct.add_entry("x", ct.TriageStatus.SUSPECT, actor="aether", notes="no test yet")
    ct.add_entry(
        "x",
        ct.TriageStatus.VERIFIED,
        actor="aletheia",
        notes="test now exists",
        test_path="tests/test_x.py",
    )
    counts = ct.summary()
    assert counts["VERIFIED"] == 1
    assert counts["SUSPECT"] == 0


def test_filter_by_status() -> None:
    ct.add_entry("a", ct.TriageStatus.VERIFIED, actor="aletheia")
    ct.add_entry("b", ct.TriageStatus.SUSPECT, actor="aether")
    suspect = ct.list_entries(ct.TriageStatus.SUSPECT)
    assert len(suspect) == 1
    assert suspect[0]["claim"] == "b"


def test_empty_claim_rejected() -> None:
    with pytest.raises(ValueError):
        ct.add_entry("", ct.TriageStatus.SUSPECT, actor="aether")


# ── New tests for Finding 50 + gap 2 ───────────────


def test_missing_actor_rejected() -> None:
    """LOAD-BEARING (Finding 50): empty actor refused."""
    with pytest.raises(ValueError) as excinfo:
        ct.add_entry("X", ct.TriageStatus.SUSPECT, actor="")
    assert "actor" in str(excinfo.value).lower()


def test_aether_cannot_mark_verified() -> None:
    """LOAD-BEARING (gap 2): self-VERIFIED is the audit hole. Aether
    cannot transition his own work to VERIFIED — external actor required.
    """
    with pytest.raises(ValueError) as excinfo:
        ct.add_entry(
            "claim of my own",
            ct.TriageStatus.VERIFIED,
            actor="aether",
            test_path="tests/test_x.py",
        )
    msg = str(excinfo.value).lower()
    assert "external" in msg or "self" in msg


def test_aether_can_mark_suspect() -> None:
    """Aether marking SUSPECT on own work is allowed (and expected)."""
    entry = ct.add_entry("X is suspect", ct.TriageStatus.SUSPECT, actor="aether")
    assert entry["status"] == "SUSPECT"
    assert entry["actor"] == "aether"


def test_aether_can_mark_removed() -> None:
    """Aether marking REMOVED on own work is allowed."""
    entry = ct.add_entry("X is removed", ct.TriageStatus.REMOVED, actor="aether")
    assert entry["status"] == "REMOVED"


def test_external_actor_can_mark_verified() -> None:
    """LOAD-BEARING (gap 2): external actor (aletheia, grok, etc.)
    can mark VERIFIED — that's the legitimate transition path."""
    entry = ct.add_entry("X is verified", ct.TriageStatus.VERIFIED, actor="aletheia")
    assert entry["status"] == "VERIFIED"
    assert entry["actor"] == "aletheia"


def test_internal_actor_name_rejected() -> None:
    """LOAD-BEARING (watchmen discipline propagated): internal
    component names like 'claude' or 'system' rejected."""
    with pytest.raises(ValueError):
        ct.add_entry("X", ct.TriageStatus.SUSPECT, actor="claude")


def test_guardrail_marker_present() -> None:
    src = Path(ct.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
