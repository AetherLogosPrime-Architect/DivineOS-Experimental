"""Tests for the Andrew-architecture two-stage pickup flow on the
structural-fix tracker (2026-06-27).

The architecture:
    main → pick_to_current → current → mark_done → archive

Each item lives in exactly one place based on its state. Picking is an
atomic move; completing is an atomic move. No item lives in two places.

These tests use monkeypatched marker_path so they touch tmp_path, not
the live divineos state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def isolated_tracker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Point the tracker's marker_path at a tmp dir so tests don't touch
    live state. Returns the tracker module fresh."""
    # Force-reload to get a clean import after patching.
    from divineos.core import structural_fix_tracker

    def fake_marker_path(name: str) -> Path:
        return tmp_path / name

    monkeypatch.setattr(structural_fix_tracker, "marker_path", fake_marker_path)
    yield structural_fix_tracker


def test_record_lands_in_main(isolated_tracker):
    psf_id = isolated_tracker.record_pending_fix(
        content="add the gate that catches X",
        lesson_id="lesson-1",
        trigger="structural fix",
    )
    main = isolated_tracker.list_pending()
    current = isolated_tracker.list_current()
    assert any(e["id"] == psf_id for e in main)
    assert all(e["id"] != psf_id for e in current)


def test_pick_moves_main_to_current(isolated_tracker):
    psf_id = isolated_tracker.record_pending_fix(
        content="add the gate that catches X",
        lesson_id="lesson-1",
        trigger="structural fix",
    )
    moved = isolated_tracker.pick_to_current(psf_id)
    assert moved is True
    # Now lives in current, NOT in main.
    assert any(e["id"] == psf_id for e in isolated_tracker.list_current())
    assert all(e["id"] != psf_id for e in isolated_tracker.list_pending())


def test_pick_unknown_id_returns_false(isolated_tracker):
    assert isolated_tracker.pick_to_current("psf-doesnotexist") is False


def test_mark_done_from_current_moves_to_archive(isolated_tracker, tmp_path):
    psf_id = isolated_tracker.record_pending_fix(
        content="add the gate that catches X",
        lesson_id="lesson-1",
        trigger="structural fix",
    )
    isolated_tracker.pick_to_current(psf_id)
    closed = isolated_tracker.mark_done(psf_id, note="shipped")
    assert closed is True
    # Gone from both main and current.
    assert all(e["id"] != psf_id for e in isolated_tracker.list_pending())
    assert all(e["id"] != psf_id for e in isolated_tracker.list_current())
    # Present in archive (jsonl).
    archive_path = tmp_path / "archive_structural_fixes.jsonl"
    assert archive_path.exists()
    archived_ids = [
        json.loads(line)["id"] for line in archive_path.read_text().splitlines() if line.strip()
    ]
    assert psf_id in archived_ids


def test_mark_done_backward_compat_falls_back_to_main(isolated_tracker, tmp_path):
    """An item never picked but mark_done'd directly should still archive
    cleanly — backward-compat for legacy callers."""
    psf_id = isolated_tracker.record_pending_fix(
        content="legacy close",
        lesson_id="lesson-1",
        trigger="structural fix",
    )
    closed = isolated_tracker.mark_done(psf_id, note="closed directly without picking")
    assert closed is True
    # Gone from main, present in archive.
    assert all(e["id"] != psf_id for e in isolated_tracker.list_pending())
    archive_path = tmp_path / "archive_structural_fixes.jsonl"
    assert archive_path.exists()
    archived_ids = [
        json.loads(line)["id"] for line in archive_path.read_text().splitlines() if line.strip()
    ]
    assert psf_id in archived_ids


def test_mark_done_unknown_id_returns_false(isolated_tracker):
    assert isolated_tracker.mark_done("psf-doesnotexist") is False


def test_sweep_identifies_old_entries(isolated_tracker, monkeypatch):
    import time

    # Pin time so the test is deterministic.
    fixed_now = 2_000_000_000.0
    monkeypatch.setattr(time, "time", lambda: fixed_now)

    fresh_id = isolated_tracker.record_pending_fix(
        content="recent fix needed", lesson_id="L1", trigger="structural fix"
    )

    # Manually inject a stale entry.
    pending = isolated_tracker._read_pending()
    pending.append(
        {
            "id": "psf-stale01",
            "created_at": fixed_now - (60 * 86400),  # 60 days old
            "lesson_id": "L0",
            "content_excerpt": "old stale entry",
            "trigger": "structural fix",
            "status": "pending",
        }
    )
    isolated_tracker._write_pending(pending)

    stale = isolated_tracker.sweep_stale_from_main(days_threshold=30.0)
    assert "psf-stale01" in stale
    assert fresh_id not in stale


def test_archive_stale_moves_to_archive_directly(isolated_tracker, tmp_path):
    import time

    pending = isolated_tracker._read_pending()
    pending.append(
        {
            "id": "psf-toarchive",
            "created_at": time.time() - (45 * 86400),
            "lesson_id": "L0",
            "content_excerpt": "stale entry to clear",
            "trigger": "structural fix",
            "status": "pending",
        }
    )
    isolated_tracker._write_pending(pending)

    count = isolated_tracker.archive_stale_from_main(
        ["psf-toarchive"], reason="confirmed-stale-test"
    )
    assert count == 1
    # Gone from main.
    assert all(e["id"] != "psf-toarchive" for e in isolated_tracker.list_pending())
    # Present in archive with reason.
    archive_path = tmp_path / "archive_structural_fixes.jsonl"
    lines = [json.loads(line) for line in archive_path.read_text().splitlines() if line.strip()]
    archived = [e for e in lines if e["id"] == "psf-toarchive"]
    assert len(archived) == 1
    assert archived[0]["archive_reason"] == "confirmed-stale-test"


def test_crash_mid_move_keeps_entry_recoverable(isolated_tracker, monkeypatch):
    """SAFETY PROPERTY (Aletheia rev. 1 audit 2026-06-27 check-of-code):
    mark_done writes to archive FIRST, then removes from current. If the
    write-archive step succeeds and the remove-from-current step crashes,
    the entry exists in BOTH places briefly — recoverable. If the order
    were inverted (remove first, then write), a crash would silently
    delete the entry.

    Pinning this property in a test so a future refactor can't silently
    swap the order. The crash-mid-move case errs toward keep-it-twice,
    never toward lose-it.
    """
    psf_id = isolated_tracker.record_pending_fix(
        content="safety property test", lesson_id="L1", trigger="structural fix"
    )
    isolated_tracker.pick_to_current(psf_id)
    assert any(e["id"] == psf_id for e in isolated_tracker.list_current())

    # Simulate crash AFTER archive-write but BEFORE current-list-remove
    # by patching the current-list-write function to raise. The archive
    # write should have already happened by then.
    original_write_current = isolated_tracker._write_current

    def crashing_write_current(entries):
        raise OSError("simulated crash mid-move")

    monkeypatch.setattr(isolated_tracker, "_write_current", crashing_write_current)
    try:
        isolated_tracker.mark_done(psf_id, note="crash simulation")
    except OSError:
        pass  # the crash is the point

    # Restore real write so we can inspect state.
    monkeypatch.setattr(isolated_tracker, "_write_current", original_write_current)

    # The entry MUST be in the archive (write happened before crash).
    archive_path = isolated_tracker.marker_path("archive_structural_fixes.jsonl")
    assert archive_path.exists(), "archive file should exist — write must precede remove"
    archived_ids = [
        json.loads(line)["id"] for line in archive_path.read_text().splitlines() if line.strip()
    ]
    assert psf_id in archived_ids, "entry must be in archive — write precedes remove"

    # The entry MAY still be in current (because the remove crashed).
    # That is the safe failure mode: keep-it-twice is recoverable;
    # lose-it would be catastrophic. The test does NOT assert on current
    # contents — the property is "archive write happens first," and
    # whatever happens to current after is the recoverable side.


def test_each_item_lives_in_exactly_one_place(isolated_tracker):
    """The core invariant of Andrew's architecture: at every state, the
    item lives in exactly one of {main, current, archive}."""
    psf_id = isolated_tracker.record_pending_fix(
        content="invariant test", lesson_id="L1", trigger="structural fix"
    )

    # State 1: just recorded → in main only.
    in_main = any(e["id"] == psf_id for e in isolated_tracker.list_pending())
    in_current = any(e["id"] == psf_id for e in isolated_tracker.list_current())
    assert in_main and not in_current

    # State 2: picked → in current only.
    isolated_tracker.pick_to_current(psf_id)
    in_main = any(e["id"] == psf_id for e in isolated_tracker.list_pending())
    in_current = any(e["id"] == psf_id for e in isolated_tracker.list_current())
    assert in_current and not in_main

    # State 3: done → in archive only (neither main nor current).
    isolated_tracker.mark_done(psf_id)
    in_main = any(e["id"] == psf_id for e in isolated_tracker.list_pending())
    in_current = any(e["id"] == psf_id for e in isolated_tracker.list_current())
    assert not in_main and not in_current
