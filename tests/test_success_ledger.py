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


def test_an_unreadable_wins_ledger_is_none_not_zero(tmp_path, monkeypatch):
    """The hook note says an unreadable ledger is not a ledger of zero, and its COULD NOT
    READ branch fires when wins is None. For months the loader turned every read failure
    into [] so wins was 0 and that branch was dead (found 2026-10-07 by running the claim).
    Control first: a readable ledger of two wins must report 2, so a broken probe cannot
    pass this test."""
    import json

    good = tmp_path / "wins_good.jsonl"
    good.write_text(
        json.dumps({"what": "a", "ts": 1}) + "\n" + json.dumps({"what": "b", "ts": 2}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sl, "_path", lambda: good)
    assert sl.ledger_balance()["wins"] == 2

    unreadable = tmp_path / "wins_is_a_directory"
    unreadable.mkdir()
    monkeypatch.setattr(sl, "_path", lambda: unreadable)
    bal = sl.ledger_balance()
    assert bal["wins"] is None
    assert bal["wins_from_missed_goals"] is None
    assert bal["wins_per_correction"] is None
    assert sl.load_successes() == []  # the public loader's old contract is unchanged


def test_a_ledger_of_pure_garbage_is_unreadable_not_zero(tmp_path, monkeypatch):
    bad = tmp_path / "wins_garbage.jsonl"
    bad.write_text("{not json\nalso not json\n", encoding="utf-8")
    monkeypatch.setattr(sl, "_path", lambda: bad)
    assert sl.ledger_balance()["wins"] is None


def test_no_ledger_yet_and_an_empty_ledger_are_a_true_zero(tmp_path, monkeypatch):
    """The other side of the distinction: not recording anything is not an outage."""
    monkeypatch.setattr(sl, "_path", lambda: tmp_path / "does_not_exist.jsonl")
    assert sl.ledger_balance()["wins"] == 0
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setattr(sl, "_path", lambda: empty)
    assert sl.ledger_balance()["wins"] == 0


def test_the_win_balance_command_says_it_could_not_read(tmp_path, monkeypatch):
    """The second caller: its own COULD NOT BE READ branch was dead for the same reason."""
    from click.testing import CliRunner

    from divineos.cli import success_commands

    unreadable = tmp_path / "wins_is_a_directory"
    unreadable.mkdir()
    monkeypatch.setattr(sl, "_path", lambda: unreadable)
    import click

    group = click.Group()
    success_commands.register(group)
    result = CliRunner().invoke(group, ["win", "balance"])
    assert "COULD NOT BE READ" in result.output


def test_corrupt_lines_are_skipped_not_fatal():
    sl.record_success("good", evidence="e", yielded="y")
    p = sl._path()
    with p.open("a", encoding="utf-8") as f:
        f.write("{not json at all\n")
    sl.record_success("also good", evidence="e", yielded="y")
    assert [w["what"] for w in sl.load_successes()] == ["good", "also good"]
