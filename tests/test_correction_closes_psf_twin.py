"""Integrating a correction must close the structural-fix row it spawned.

``correction`` mirrors structural-fix-shaped text into the pending-obligations
list. Until 2026-08-25 the mirror had no return path: 187 of 334 rows came in
that way and 50 of them were already INTEGRATED on the corrections side while
still reading as pending on the briefing.

These tests exist for a second reason. ``_close_structural_fix_twin`` swallows
every exception on purpose — mirror upkeep must never block an integration —
and a bare except around code that has never executed is indistinguishable from
code that does nothing. The first draft called a ``get_correction_text`` that
does not exist; it would have raised NameError into that handler and reported
success forever. So the wiring is pinned by a test that asserts the row
actually closes, not that the call did not crash.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import andrew_correction_tracker as act
from divineos.core import structural_fix_tracker as sft

TEXT = (
    "Andrew 2026-08-25: the mirror files but never closes, so build the "
    "structural fix that propagates closure back to the obligations list."
)


@pytest.fixture
def stores(tmp_path, monkeypatch):
    """Redirect both stores — the corrections DB and the psf marker files."""
    monkeypatch.setattr(act, "_db_path", lambda: tmp_path / "andrew_corrections.db")
    monkeypatch.setattr(act, "_write_attestation_marker", lambda: None)
    monkeypatch.setattr(sft, "marker_path", lambda name: tmp_path / name)
    return tmp_path


def _pending_ids(stores):
    return [e["id"] for e in sft.list_pending()]


def _archive(stores):
    path = stores / "archive_structural_fixes.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_integrating_a_correction_closes_its_psf_twin(stores):
    correction_id = act.file_correction(TEXT)
    psf_id = sft.record_pending_fix(TEXT, trigger="structural fix", source_kind="correction")
    assert psf_id in _pending_ids(stores)

    assert act.integrate(correction_id, "shipped in commit abc1234, tests/test_x.py")

    assert psf_id not in _pending_ids(stores)
    archived = _archive(stores)
    assert [r["id"] for r in archived] == [psf_id]
    assert archived[0]["status"] == "done"
    assert f"#{correction_id}" in archived[0]["done_note"]


def test_evidence_travels_into_the_close_note(stores):
    """A row closed with no trace of WHY is the same silence the mirror had."""
    correction_id = act.file_correction(TEXT)
    sft.record_pending_fix(TEXT, trigger="structural fix", source_kind="correction")

    act.integrate(correction_id, "shipped in commit deadbee, tests/test_y.py")

    assert "deadbee" in _archive(stores)[0]["done_note"]


def test_refused_integration_leaves_the_twin_open(stores):
    """Evidence without a structural artifact is refused. The obligation has
    to survive that refusal or the mirror closes on prose."""
    correction_id = act.file_correction(TEXT)
    psf_id = sft.record_pending_fix(TEXT, trigger="structural fix", source_kind="correction")

    assert not act.integrate(correction_id, "I have learned this and will do better now")

    assert psf_id in _pending_ids(stores)


def test_only_the_matching_row_closes(stores):
    other = sft.record_pending_fix(
        "An unrelated obligation with a structural fix in it",
        trigger="structural fix",
        source_kind="correction",
    )
    correction_id = act.file_correction(TEXT)
    mine = sft.record_pending_fix(TEXT, trigger="structural fix", source_kind="correction")

    act.integrate(correction_id, "shipped in commit abc1234, tests/test_x.py")

    remaining = _pending_ids(stores)
    assert other in remaining
    assert mine not in remaining


def test_claim_sourced_rows_are_not_closed_by_a_correction(stores):
    """``claim`` files into the same list. A correction integrating its own
    text must not close an obligation a different surface is tracking."""
    correction_id = act.file_correction(TEXT)
    claim_row = sft.record_pending_fix(TEXT, trigger="structural fix", source_kind="claim")

    act.integrate(correction_id, "shipped in commit abc1234, tests/test_x.py")

    assert claim_row in _pending_ids(stores)


def test_integration_succeeds_when_there_is_no_twin(stores):
    correction_id = act.file_correction("A plain correction with no fix shape in it")

    assert act.integrate(correction_id, "shipped in commit abc1234, tests/test_x.py")


def test_mirror_failure_never_blocks_the_integration(stores, monkeypatch):
    """The swallow is deliberate. Pin it: a broken mirror must not cost an
    integration that has real evidence behind it."""
    correction_id = act.file_correction(TEXT)
    sft.record_pending_fix(TEXT, trigger="structural fix", source_kind="correction")

    def boom(*_args, **_kwargs):
        raise RuntimeError("mirror is down")

    monkeypatch.setattr(sft, "close_twin_for_text", boom)

    assert act.integrate(correction_id, "shipped in commit abc1234, tests/test_x.py")
