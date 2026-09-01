"""Tests for the context-token heartbeat.

The property under test is one sentence: A BLIND SENSOR MUST NEVER REPORT A
LOW NUMBER. Before 2026-08-24 it reported ``0.0``, which the caller reads as
"3% of the window used, plenty of room, do not fire" -- so the reading that
knew least said the most reassuring thing available, and the pre-compaction
ritual stayed dark at whatever the real level was.

Every test here exercises the BLOCK case, not just the happy path. That is
deliberate: the happy path was never broken.
"""

from __future__ import annotations

import json
import time

import pytest

from divineos.core import context_heartbeat as ch


class FakeSnap:
    """Stand-in for ContextSnapshot. Only the fields the reader touches."""

    def __init__(self, pinned, total_tokens, session_id="sess-a", note="n"):
        self.pinned = pinned
        self.total_tokens = total_tokens
        self.session_id = session_id
        self.note = note


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point the heartbeat at a throwaway home so tests never touch the real log."""
    d = tmp_path / ".divineos"
    d.mkdir()
    monkeypatch.setattr(ch, "divineos_home", lambda: d)
    return d


def _patch_snapshot(monkeypatch, value):
    """Replace get_context_snapshot; ``value`` may be a snap or an exception."""
    import divineos.core.context_tokens as ct

    def fake(*_a, **_k):
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(ct, "get_context_snapshot", fake)


# --------------------------------------------------------------- the block case


@pytest.mark.parametrize(
    ("label", "snap"),
    [
        ("unpinned — may belong to another session", FakeSnap(False, 961_000)),
        ("pinned but zero tokens", FakeSnap(True, 0)),
        ("pinned but tokens is None", FakeSnap(True, None)),
        ("pinned but tokens is not an int", FakeSnap(True, "lots")),
        ("pinned but tokens negative", FakeSnap(True, -5)),
    ],
)
def test_blind_never_reports_a_number(home, monkeypatch, label, snap):
    """The whole point. Blind yields None, never 0 -- see module docstring."""
    _patch_snapshot(monkeypatch, snap)
    b = ch.beat()
    assert b.seen is False, label
    assert b.total_tokens is None, label
    assert b.pct is None, label
    # The specific historical bug: a blind read that looks like a low one.
    assert b.total_tokens != 0
    assert b.pct != 0.0


def test_snapshot_raising_is_blind_not_zero(home, monkeypatch):
    _patch_snapshot(monkeypatch, OSError("transcript gone"))
    b = ch.beat()
    assert b.seen is False
    assert b.total_tokens is None
    assert "OSError" in b.note


def test_blind_is_not_fresh(home, monkeypatch):
    """A blind beat must never satisfy the freshness check a caller spends."""
    _patch_snapshot(monkeypatch, FakeSnap(False, 900_000))
    assert ch.beat().is_fresh is False


# --------------------------------------------------------------- the happy path


def test_pinned_reading_is_recorded(home, monkeypatch):
    _patch_snapshot(monkeypatch, FakeSnap(True, 500_000, "sess-a"))
    b = ch.beat()
    assert b.seen is True
    assert b.total_tokens == 500_000
    assert b.pct == pytest.approx(0.5)
    assert b.session_id == "sess-a"
    assert b.is_fresh is True


def test_threshold_arithmetic_is_the_number_andrew_named(home, monkeypatch):
    """0.92 of the window is 920,000 -- the figure the ritual fires on."""
    from divineos.core.auto_cycle import TRIGGER_THRESHOLD

    assert ch.CONTEXT_WINDOW_TOKENS * TRIGGER_THRESHOLD == 920_000
    _patch_snapshot(monkeypatch, FakeSnap(True, 920_000))
    assert ch.beat().pct >= TRIGGER_THRESHOLD


def test_just_below_threshold_does_not_reach(home, monkeypatch):
    from divineos.core.auto_cycle import TRIGGER_THRESHOLD

    _patch_snapshot(monkeypatch, FakeSnap(True, 919_999))
    assert ch.beat().pct < TRIGGER_THRESHOLD


# ------------------------------------------------------------------ persistence


def test_read_latest_round_trips(home, monkeypatch):
    _patch_snapshot(monkeypatch, FakeSnap(True, 123_456, "sess-b"))
    ch.beat()
    got = ch.read_latest()
    assert got is not None
    assert got.total_tokens == 123_456
    assert got.session_id == "sess-b"
    assert got.seen is True


def test_read_latest_is_none_before_any_beat(home):
    assert ch.read_latest() is None


def test_read_latest_survives_a_corrupt_state_file(home, monkeypatch):
    """An unreadable state file must read as 'no heartbeat', not crash."""
    (home / ch.HEARTBEAT_STATE).write_text("{not json", encoding="utf-8")
    assert ch.read_latest() is None


def test_log_is_append_only(home, monkeypatch):
    _patch_snapshot(monkeypatch, FakeSnap(True, 100, "sess-a"))
    ch.beat()
    _patch_snapshot(monkeypatch, FakeSnap(True, 200, "sess-a"))
    ch.beat()
    rows = [
        json.loads(line)
        for line in (home / ch.HEARTBEAT_LOG).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["total_tokens"] for r in rows] == [100, 200]


# ----------------------------------------------------------------- blind counting


def test_blind_stats_counts_what_had_no_answer_before(home, monkeypatch):
    """Until 2026-08-24 no log anywhere recorded a sensor fault. Now it does."""
    for snap in (
        FakeSnap(True, 10),
        FakeSnap(False, 0),
        FakeSnap(True, 20),
        FakeSnap(False, 0),
    ):
        _patch_snapshot(monkeypatch, snap)
        ch.beat()
    st = ch.blind_stats()
    assert st["beats"] == 4
    assert st["blind"] == 2
    assert st["blind_pct"] == pytest.approx(0.5)
    assert sum(st["reasons"].values()) == 2


def test_blind_stats_on_empty_log_is_zero_not_a_crash(home):
    st = ch.blind_stats()
    assert st["beats"] == 0
    assert st["blind"] == 0


def test_blind_stats_skips_unparseable_rows(home, monkeypatch):
    _patch_snapshot(monkeypatch, FakeSnap(True, 10))
    ch.beat()
    with open(home / ch.HEARTBEAT_LOG, "a", encoding="utf-8") as fh:
        fh.write("{torn row" + chr(10))
    assert ch.blind_stats()["beats"] == 1


# --------------------------------------------------------------------- freshness


def test_a_stale_beat_is_not_fresh(home):
    old = ch.Beat(True, time.time() - ch.FRESH_WITHIN_SECONDS - 1, 500_000, "s", "ok")
    assert old.seen is True
    assert old.is_fresh is False


def test_beat_never_raises_when_the_home_is_unwritable(tmp_path, monkeypatch):
    """A heartbeat that cannot write is a hole in the log, never a dead turn."""
    monkeypatch.setattr(ch, "divineos_home", lambda: tmp_path / "nope" / "deeper")
    _patch_snapshot(monkeypatch, FakeSnap(True, 42))
    monkeypatch.setattr(
        ch.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("read-only"))
    )
    b = ch.beat()
    assert b.seen is True  # the reading still happened
    assert b.total_tokens == 42
