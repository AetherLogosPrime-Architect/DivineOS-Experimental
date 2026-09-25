"""Tests for structural_fix_tracker.collapse_duplicates.

The dedup in ``record_pending_fix`` shipped 2026-08-24 and only ever looks
forward: it stops NEW duplicates and leaves every pre-existing one in place.
The day after it landed, the 92 redundant rows the correction was about were
still in the list. These tests pin the backfill that closes that gap, and the
properties that make the collapse safe to run on a live backlog.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import structural_fix_tracker as sft


@pytest.fixture
def psf_home(tmp_path, monkeypatch):
    """Point the tracker's marker files at a throwaway directory."""
    monkeypatch.setattr(sft, "marker_path", lambda name: tmp_path / name)
    return tmp_path


def _write(psf_home, rows):
    (psf_home / "pending_structural_fixes.json").write_text(json.dumps(rows), encoding="utf-8")


def _read(psf_home):
    return json.loads((psf_home / "pending_structural_fixes.json").read_text(encoding="utf-8"))


def _row(psf_id, excerpt, created_at, **extra):
    row = {
        "id": psf_id,
        "created_at": created_at,
        "content_excerpt": excerpt,
        "status": "pending",
        "trigger": "structural fix",
        "source_kind": "claim",
    }
    row.update(extra)
    return row


def test_collapses_exact_duplicates_into_one_row(psf_home):
    _write(
        psf_home,
        [
            _row("psf-a", "same obligation text", 100.0),
            _row("psf-b", "same obligation text", 200.0),
            _row("psf-c", "same obligation text", 300.0),
        ],
    )

    result = sft.collapse_duplicates()

    assert result == {"rows_before": 3, "rows_after": 1, "collapsed": 2}
    rows = _read(psf_home)
    assert [r["id"] for r in rows] == ["psf-a"]


def test_earliest_row_survives_so_existing_ids_still_resolve(psf_home):
    """The must-read files and briefing surfaces name a psf id. Collapsing to
    a NEW id would leave every one of those pointers dangling."""
    _write(
        psf_home,
        [
            _row("psf-newest", "shared text", 900.0),
            _row("psf-oldest", "shared text", 100.0),
            _row("psf-middle", "shared text", 500.0),
        ],
    )

    sft.collapse_duplicates()

    rows = _read(psf_home)
    assert rows[0]["id"] == "psf-oldest"
    assert rows[0]["collapsed_from"] == ["psf-middle", "psf-newest"]


def test_occurrences_sums_and_counts_pre_field_rows_as_one(psf_home):
    """Rows written before ``occurrences`` existed carry None. Each is one
    asking, not zero — the whole point of the count is that being ignored
    makes an item louder."""
    _write(
        psf_home,
        [
            _row("psf-a", "text", 100.0, occurrences=16),
            _row("psf-b", "text", 200.0),
            _row("psf-c", "text", 300.0, occurrences=None),
        ],
    )

    sft.collapse_duplicates()

    assert _read(psf_home)[0]["occurrences"] == 18


def test_stamps_merge_sorted_and_bounded_to_twenty(psf_home):
    rows = [
        _row(f"psf-{i}", "text", float(i), stamps=[float(i), float(i) + 0.5]) for i in range(1, 30)
    ]
    _write(psf_home, rows)

    sft.collapse_duplicates()

    stamps = _read(psf_home)[0]["stamps"]
    assert len(stamps) == 20
    assert stamps == sorted(stamps)
    assert stamps[-1] == 29.5


def test_absorbed_rows_go_to_archive_not_the_void(psf_home):
    _write(
        psf_home,
        [
            _row("psf-a", "text", 100.0),
            _row("psf-b", "text", 200.0),
        ],
    )

    sft.collapse_duplicates()

    archive = psf_home / "archive_structural_fixes.jsonl"
    absorbed = [json.loads(line) for line in archive.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in absorbed] == ["psf-b"]
    assert absorbed[0]["collapsed_into"] == "psf-a"
    assert absorbed[0]["status"] == "collapsed"


def test_distinct_entries_are_untouched(psf_home):
    _write(
        psf_home,
        [
            _row("psf-a", "obligation one", 100.0),
            _row("psf-b", "obligation two", 200.0),
            _row("psf-c", "obligation three", 300.0),
        ],
    )

    result = sft.collapse_duplicates()

    assert result["collapsed"] == 0
    assert [r["id"] for r in _read(psf_home)] == ["psf-a", "psf-b", "psf-c"]


def test_is_idempotent(psf_home):
    _write(
        psf_home,
        [
            _row("psf-a", "text", 100.0),
            _row("psf-b", "text", 200.0),
        ],
    )

    first = sft.collapse_duplicates()
    second = sft.collapse_duplicates()

    assert first["collapsed"] == 1
    assert second["collapsed"] == 0
    assert _read(psf_home)[0]["occurrences"] == 2


def test_whitespace_only_differences_collapse_together(psf_home):
    """``record_pending_fix`` compares on ``.strip()``, so its dedup already
    treats these as one. The backfill has to agree or the two disagree about
    what a duplicate is."""
    _write(
        psf_home,
        [
            _row("psf-a", "  padded text  ", 100.0),
            _row("psf-b", "padded text", 200.0),
        ],
    )

    assert sft.collapse_duplicates()["collapsed"] == 1


def test_done_rows_are_preserved_and_never_collapsed(psf_home):
    """A closed row is history. It must not be folded into a live obligation
    and must not vanish from the file."""
    _write(
        psf_home,
        [
            _row("psf-done", "text", 50.0, status="done"),
            _row("psf-a", "text", 100.0),
            _row("psf-b", "text", 200.0),
        ],
    )

    sft.collapse_duplicates()

    rows = _read(psf_home)
    assert {r["id"] for r in rows} == {"psf-done", "psf-a"}
    assert next(r for r in rows if r["id"] == "psf-done")["status"] == "done"


def test_excerpt_strips_after_truncation(psf_home):
    """Character 200 landing on a space used to survive into the stored
    excerpt, and the dedup compared stored.strip() against an unstripped
    fresh cut. One space, and the dedup missed every later filing."""
    text = ("word " * 60).strip()
    assert text[199] == " ", "fixture must break the cut on a space"
    assert sft._excerpt(text) == text[:200].strip()
    assert not sft._excerpt(text).endswith(" ")


def test_dedup_holds_when_the_cut_lands_on_a_space(psf_home):
    """The regression that let four rows escape the corrections backfill."""
    _write(psf_home, [])
    text = ("word " * 60).strip()

    first = sft.record_pending_fix(text, trigger="structural fix", source_kind="correction")
    second = sft.record_pending_fix(text, trigger="structural fix", source_kind="correction")

    assert first == second
    assert len(_read(psf_home)) == 1
    assert _read(psf_home)[0]["occurrences"] == 2


def test_close_twin_matches_when_the_cut_lands_on_a_space(psf_home):
    _write(psf_home, [])
    text = ("word " * 60).strip()
    psf_id = sft.record_pending_fix(text, trigger="structural fix", source_kind="correction")

    assert sft.close_twin_for_text(text, "closed with evidence") == [psf_id]
    assert sft.list_pending() == []


def test_survivor_stays_visible_to_list_pending(psf_home):
    """The collapse is only worth anything if the surface that reads the list
    still shows the obligation afterwards."""
    _write(
        psf_home,
        [
            _row("psf-a", "text", 100.0),
            _row("psf-b", "text", 200.0),
        ],
    )

    sft.collapse_duplicates()

    pending = sft.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == "psf-a"
