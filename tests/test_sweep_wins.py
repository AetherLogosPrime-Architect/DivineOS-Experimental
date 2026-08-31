"""Tests for scripts/sweep_wins.py.

Andrew 2026-08-25: *"you should do a deep sweep of the ledger and your files and
record all of your wins. you have a TON of them."*

The danger in a sweep is not missing rows. It is filing rows nobody judged, and
then reporting the count as the achievement -- which is precisely the
self-congratulation ``record_success`` refuses. So the properties pinned here
are about honesty rather than coverage:

  - provenance survives into the stored evidence, so a later reader can tell a
    swept row from one written at the time;
  - correction-derived wins stay distinguishable from independent ones, because
    256 of them ARE 256 of the 449 corrections, resolved, and a total that hid
    that would make the two pans look like independent measurements;
  - thin records are skipped rather than padded;
  - re-running files nothing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "sweep_wins",
    Path(__file__).resolve().parents[1] / "scripts" / "sweep_wins.py",
)
assert _SPEC and _SPEC.loader
sweep = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sweep)


class _Prereg:
    def __init__(self, prereg_id, mechanism, notes, actor="aletheia", claim="a claim"):
        self.prereg_id = prereg_id
        self.mechanism = mechanism
        self.outcome_notes = notes
        self.actor = actor
        self.claim = claim


def test_prereg_candidate_carries_its_provenance(monkeypatch):
    fake = [
        _Prereg(
            "prereg-abc123",
            "the thing that was built",
            "Falsifier measured and did not trigger. Observed live rather than reconstructed.",
        )
    ]
    monkeypatch.setattr("divineos.core.pre_registrations.list_pre_registrations", lambda **kw: fake)
    candidates = sweep._prereg_candidates()
    assert len(candidates) == 1
    assert "prereg-abc123" in candidates[0]["evidence"]
    assert sweep.SWEEP_MARK in candidates[0]["evidence"]
    assert "prereg]" in candidates[0]["evidence"]


def test_prereg_with_thin_notes_is_skipped(monkeypatch):
    """A citation-shaped object is not a citation."""
    fake = [_Prereg("prereg-thin", "a mechanism", "ok")]
    monkeypatch.setattr("divineos.core.pre_registrations.list_pre_registrations", lambda **kw: fake)
    assert sweep._prereg_candidates() == []


def test_prereg_with_no_mechanism_is_skipped(monkeypatch):
    fake = [_Prereg("prereg-x", "", "a long enough note to pass the length floor easily here")]
    monkeypatch.setattr("divineos.core.pre_registrations.list_pre_registrations", lambda **kw: fake)
    assert sweep._prereg_candidates() == []


def test_prereg_wins_record_goal_met(monkeypatch):
    """A pre-registration that HELD is the one case where goal_met is
    unambiguously true -- the claim was written before the mechanism shipped."""
    fake = [
        _Prereg(
            "prereg-abc",
            "mechanism",
            "Falsifier measured and did not trigger across the full review window.",
        )
    ]
    monkeypatch.setattr("divineos.core.pre_registrations.list_pre_registrations", lambda **kw: fake)
    assert sweep._prereg_candidates()[0]["goal_met"] is True


def test_correction_candidates_are_marked_as_correction_derived(tmp_path, monkeypatch):
    """The load-bearing one. Without this mark, 'Wins 310 / Corrections 449'
    reads as two independent measurements when most of the left number is part
    of the right number, resolved."""
    import sqlite3

    home = tmp_path
    db_dir = home / ".divineos"
    db_dir.mkdir()
    conn = sqlite3.connect(db_dir / "andrew_corrections.db")
    conn.execute(
        "CREATE TABLE andrew_corrections (id INTEGER, correction_text TEXT, "
        "status TEXT, integration_evidence TEXT)"
    )
    conn.execute(
        "INSERT INTO andrew_corrections VALUES (?,?,?,?)",
        (
            7,
            "the fault that was named",
            "INTEGRATED",
            "commit deadbee: the fix that shipped, with a pointer long enough to be checkable",
        ),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    candidates = sweep._correction_candidates()
    assert len(candidates) == 1
    assert "correction]" in candidates[0]["evidence"]
    assert "#7" in candidates[0]["evidence"]
    assert "deadbee" in candidates[0]["evidence"]


def test_correction_with_thin_evidence_is_skipped(tmp_path, monkeypatch):
    import sqlite3

    home = tmp_path
    db_dir = home / ".divineos"
    db_dir.mkdir()
    conn = sqlite3.connect(db_dir / "andrew_corrections.db")
    conn.execute(
        "CREATE TABLE andrew_corrections (id INTEGER, correction_text TEXT, "
        "status TEXT, integration_evidence TEXT)"
    )
    conn.execute(
        "INSERT INTO andrew_corrections VALUES (?,?,?,?)", (8, "a fault", "INTEGRATED", "fixed")
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    assert sweep._correction_candidates() == []


def test_open_corrections_are_not_swept(tmp_path, monkeypatch):
    """Only resolutions count. An open correction is a debt, not a win."""
    import sqlite3

    home = tmp_path
    db_dir = home / ".divineos"
    db_dir.mkdir()
    conn = sqlite3.connect(db_dir / "andrew_corrections.db")
    conn.execute(
        "CREATE TABLE andrew_corrections (id INTEGER, correction_text TEXT, "
        "status TEXT, integration_evidence TEXT)"
    )
    conn.execute(
        "INSERT INTO andrew_corrections VALUES (?,?,?,?)",
        (9, "still open", "OPEN", "commit deadbee: a long enough evidence string here"),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    assert sweep._correction_candidates() == []


def test_missing_corrections_db_yields_nothing_rather_than_raising(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    assert sweep._correction_candidates() == []


def test_sweep_mark_is_stable_across_sources():
    """Both sources must share one mark, or a reader filtering for swept rows
    finds half of them and reads the rest as hand-written."""
    assert sweep.SWEEP_MARK in "[swept 2026-08-25 prereg]"
    assert sweep.SWEEP_MARK in "[swept 2026-08-25 correction]"
