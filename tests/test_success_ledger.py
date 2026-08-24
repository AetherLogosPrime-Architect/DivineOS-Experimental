"""Tests for the success ledger.

Real file writes into a temp HUD dir, real read-back. The evidence-required
tests are the load-bearing ones: a ledger that accepts uncited wins is a
place to write encouraging things about myself.
"""

from __future__ import annotations

import pytest

from divineos.core import success_ledger as sl


@pytest.fixture(autouse=True)
def _tmp_hud(tmp_path, monkeypatch):
    monkeypatch.setattr(sl, "_ensure_hud_dir", lambda: tmp_path)
    yield


def test_evidence_is_required():
    with pytest.raises(sl.EvidenceRequiredError, match="evidence is required"):
        sl.record_success("did a thing", evidence="", yielded="something")
    with pytest.raises(sl.EvidenceRequiredError):
        sl.record_success("did a thing", evidence="   ", yielded="something")


def test_yielded_is_required():
    with pytest.raises(ValueError, match="yielded"):
        sl.record_success("did a thing", evidence="commit abc123", yielded="")


def test_what_is_required():
    with pytest.raises(ValueError, match="what"):
        sl.record_success("  ", evidence="commit abc123", yielded="something")


def test_a_win_round_trips():
    entry = sl.record_success(
        "capped hook timeouts",
        evidence="commit 23423024, 994s -> 559s per exchange",
        yielded="bounded a genuinely stuck hook from stalling a full minute",
    )
    assert entry["id"].startswith("win-")
    loaded = sl.load_successes()
    assert len(loaded) == 1
    assert loaded[0]["evidence"].startswith("commit 23423024")


def test_goal_met_false_still_records_a_win():
    """The moon case — the whole reason this module exists."""
    sl.record_success(
        "found the guardrail gate failing open",
        evidence="commit c1f371f6, both paths verified, SystemExit(1) on git failure",
        yielded="a gate protecting the foundational truths now refuses instead of waving through",
        goal="find the cause of the freeze",
        goal_met=False,
    )
    wins = sl.load_successes()
    assert len(wins) == 1
    assert wins[0]["goal_met"] is False
    assert sl.wins_from_missed_goals() == wins


def test_wins_from_missed_goals_excludes_met_and_none():
    sl.record_success("a", evidence="e", yielded="y", goal_met=True)
    sl.record_success("b", evidence="e", yielded="y", goal_met=False)
    sl.record_success("c", evidence="e", yielded="y")  # goal_met None
    missed = sl.wins_from_missed_goals()
    assert [w["what"] for w in missed] == ["b"]


def test_recent_successes_is_newest_first():
    for n in ("first", "second", "third"):
        sl.record_success(n, evidence="e", yielded="y")
    assert [w["what"] for w in sl.recent_successes(2)] == ["third", "second"]


def test_append_only_never_rewrites():
    sl.record_success("one", evidence="e", yielded="y")
    first = sl.load_successes()[0]
    sl.record_success("two", evidence="e", yielded="y")
    after = sl.load_successes()
    assert len(after) == 2
    assert after[0] == first  # the earlier entry is untouched


def test_balance_reports_zero_wins_honestly():
    b = sl.ledger_balance()
    assert b["wins"] == 0
    assert b["wins_from_missed_goals"] == 0


def test_balance_distinguishes_unreadable_corrections_from_zero(monkeypatch):
    """None and 0 are different facts — collapsing them is the session's whole lesson."""
    import divineos.core.corrections as corrections

    def boom():
        raise OSError("store unreadable")

    monkeypatch.setattr(corrections, "load_corrections", boom)
    sl.record_success("a", evidence="e", yielded="y")
    b = sl.ledger_balance()
    assert b["wins"] == 1
    assert b["corrections"] is None  # NOT 0
    assert b["wins_per_correction"] is None


def test_corrupt_lines_are_skipped_not_fatal():
    sl.record_success("good", evidence="e", yielded="y")
    p = sl._path()
    with p.open("a", encoding="utf-8") as f:
        f.write("{not json at all\n")
    sl.record_success("also good", evidence="e", yielded="y")
    assert [w["what"] for w in sl.load_successes()] == ["good", "also good"]
