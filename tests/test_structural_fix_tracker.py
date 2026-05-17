"""Regression-pin tests for structural_fix_tracker.

Andrew 2026-05-14: I had been filing `learn` entries that named
structural fixes I should build, treating the filing as if it were
the fix. structural_fix_tracker is the structural change that ALTERS
EXECUTION PATH — the learn CLI now writes parallel pending entries
when content matches structural-fix-shape, and the briefing surfaces
them as visible obligations.

These tests pin the detector regex set and the persistence shape so
a future refactor can't silently revert the behavior.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from divineos.core.structural_fix_tracker import (
    detect_structural_fix_shape,
    list_pending,
    mark_done,
    record_pending_fix,
)


# --- Detector regex set --------------------------------------------------


def test_detect_structural_fix_phrase() -> None:
    """Bare phrase 'structural fix' fires."""
    assert detect_structural_fix_shape("the structural fix is X") == "structural fix"


def test_detect_should_build() -> None:
    """'should build' / 'need to build' / 'will build' all fire."""
    assert detect_structural_fix_shape("I should build a detector for X") == "should build"
    assert detect_structural_fix_shape("need to build a gate here") == "should build"
    assert detect_structural_fix_shape("will build the test next") == "should build"


def test_detect_build_a_detector() -> None:
    """'build a detector/gate/check/test/monitor' fires (Andrew's
    paradigmatic structural-fix language)."""
    assert detect_structural_fix_shape("build a detector that catches X") == "build a detector"
    assert detect_structural_fix_shape("build the gate that blocks Y") == "build a detector"
    assert detect_structural_fix_shape("building a check for Z") == "build a detector"


def test_detect_to_prevent_recurrence() -> None:
    """The recurring-pattern framing fires."""
    assert (
        detect_structural_fix_shape("to prevent recurrence of this failure")
        == "to prevent recurrence"
    )


def test_detect_the_actual_fix() -> None:
    """'the actual fix is' / 'the real fix would be' fires."""
    assert detect_structural_fix_shape("the actual fix is wiring X") == "the actual fix"
    assert detect_structural_fix_shape("the real fix would be a gate") == "the actual fix"


def test_detect_wire_into() -> None:
    """Wiring promises fire — they were a common deferral shape."""
    assert detect_structural_fix_shape("wire X into Y") == "wire X into Y"
    assert detect_structural_fix_shape("wiring the detector into the hook") == "wire X into Y"


def test_detect_empty_content_returns_none() -> None:
    """Empty / None content does not fire."""
    assert detect_structural_fix_shape("") is None
    assert detect_structural_fix_shape(None) is None  # type: ignore[arg-type]


def test_detect_pure_record_returns_none() -> None:
    """Plain factual records (no structural-fix-shape) do not fire.
    LOAD-BEARING: false-positive on every learn entry would defeat
    the discipline."""
    plain = (
        "Andrew uses native Windows paths in transcript_path. The hook "
        "needs to handle both formats. Already verified."
    )
    assert detect_structural_fix_shape(plain) is None


# --- Persistence shape ---------------------------------------------------


def test_record_and_list_round_trip(tmp_path: Path) -> None:
    """Recording a pending entry surfaces it via list_pending."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        psf_id = record_pending_fix(
            "should build a fabrication detector",
            lesson_id="kid-test-1",
            trigger="should build",
        )
        assert psf_id.startswith("psf-")
        pending = list_pending()
        assert len(pending) == 1
        assert pending[0]["id"] == psf_id
        assert pending[0]["lesson_id"] == "kid-test-1"
        assert pending[0]["trigger"] == "should build"
        assert pending[0]["status"] == "pending"


def test_mark_done_removes_from_pending(tmp_path: Path) -> None:
    """Marking done excludes the entry from default list_pending."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        psf_id = record_pending_fix("the actual fix is X", trigger="the actual fix")
        assert len(list_pending()) == 1
        ok = mark_done(psf_id, note="shipped as commit abc1234")
        assert ok is True
        assert len(list_pending()) == 0
        # include_done returns the entry with status=done
        all_entries = list_pending(include_done=True)
        assert len(all_entries) == 1
        assert all_entries[0]["status"] == "done"
        assert all_entries[0]["done_note"] == "shipped as commit abc1234"


def test_mark_done_unknown_id_returns_false(tmp_path: Path) -> None:
    """mark_done on a non-existent id returns False (fail-soft)."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        assert mark_done("psf-nonexistent") is False


def test_list_pending_fail_open_on_missing_file(tmp_path: Path) -> None:
    """Missing file returns empty list, not exception."""
    missing = tmp_path / "definitely_does_not_exist.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(missing.parent)}):
        assert list_pending() == []


def test_list_pending_fail_open_on_malformed_file(tmp_path: Path) -> None:
    """Malformed JSON returns empty list, not exception."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    pending_file.write_text("not valid json {{{", encoding="utf-8")
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        assert list_pending() == []
