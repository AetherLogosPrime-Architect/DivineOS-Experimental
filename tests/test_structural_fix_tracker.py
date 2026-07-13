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
    """Marking done MOVES the entry from main to the archive jsonl.

    Updated 2026-06-27 for Andrew architecture: items live in exactly
    one place based on state. mark_done is an atomic move (main → archive
    via the fallback path, or current → archive via the proper path).
    The entry is no longer findable in list_pending(include_done=True)
    after mark_done — it's in archive_structural_fixes.jsonl.
    """
    import json

    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        psf_id = record_pending_fix("the actual fix is X", trigger="the actual fix")
        assert len(list_pending()) == 1
        ok = mark_done(psf_id, note="shipped as commit abc1234")
        assert ok is True
        # Entry is gone from main entirely (not just status-flagged).
        assert len(list_pending()) == 0
        assert len(list_pending(include_done=True)) == 0
        # Entry is present in the archive jsonl with status=done.
        archive_path = pending_file.parent / "archive_structural_fixes.jsonl"
        assert archive_path.exists()
        archived = [
            json.loads(line) for line in archive_path.read_text().splitlines() if line.strip()
        ]
        matching = [e for e in archived if e["id"] == psf_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "done"
        assert matching[0]["done_note"] == "shipped as commit abc1234"


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


# --- source_kind field (added 2026-05-18 to broaden the wiring) ----------


def test_record_carries_source_kind_default_learn(tmp_path: Path) -> None:
    """Default source_kind='learn' preserves backward compatibility."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        record_pending_fix("should build a detector for X", trigger="should build")
        entries = list_pending()
        assert entries[0]["source_kind"] == "learn"


def test_record_carries_source_kind_correction(tmp_path: Path) -> None:
    """source_kind='correction' is preserved on read-back."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        record_pending_fix(
            "you should build a gate against this",
            trigger="should build",
            source_kind="correction",
        )
        entries = list_pending()
        assert entries[0]["source_kind"] == "correction"


def test_record_carries_source_kind_claim(tmp_path: Path) -> None:
    """source_kind='claim' is preserved on read-back."""
    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(pending_file.parent)}):
        record_pending_fix(
            "the actual fix is a new substrate-level check",
            trigger="the actual fix",
            source_kind="claim",
        )
        entries = list_pending()
        assert entries[0]["source_kind"] == "claim"


# --- CLI integration: correction triggers the tracker --------------------


def test_correction_cli_triggers_tracker(tmp_path: Path) -> None:
    """Filing a correction with structural-fix-shape language records
    a pending entry with source_kind='correction'. Closes the wiring
    gap Andrew named 2026-05-18."""
    from click.testing import CliRunner

    from divineos.cli import cli

    pending_file = tmp_path / "pending_structural_fixes.json"
    corrections_file = tmp_path / "corrections.jsonl"
    with patch.dict(
        "os.environ",
        {
            "DIVINEOS_HOME": str(pending_file.parent),
            "DIVINEOS_DATA_HOME": str(corrections_file.parent),
        },
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["correction", "you should build a detector that catches this pattern"],
        )
        assert result.exit_code == 0
        pending = list_pending()
        assert len(pending) == 1, (
            f"Expected the correction to trigger a pending entry; got {pending}. "
            f"Output was: {result.output}"
        )
        assert pending[0]["source_kind"] == "correction"
        assert pending[0]["trigger"]  # whichever trigger fired


def test_claim_cli_triggers_tracker(tmp_path: Path) -> None:
    """Filing a claim with structural-fix-shape language in statement
    OR context records a pending entry with source_kind='claim'."""
    from click.testing import CliRunner

    from divineos.cli import cli

    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict(
        "os.environ",
        {
            "DIVINEOS_HOME": str(pending_file.parent),
            "DIVINEOS_DATA_HOME": str(tmp_path),
        },
    ):
        runner = CliRunner()
        # Methodology gate (Andrew 2026-05-18) requires --promotes/--demotes
        # on tier 1-3 claims; provide them so this test exercises the
        # structural-fix tracker, not the gate.
        result = runner.invoke(
            cli,
            [
                "claim",
                "Pattern X recurs; we should build a substrate-level check for it.",
                "--tier",
                "3",
                "--promotes",
                "the substrate-level check fires on the next instance",
                "--demotes",
                "the pattern stops recurring without the substrate check",
            ],
        )
        assert result.exit_code == 0, f"Claim filing failed: {result.output}"
        pending = list_pending()
        assert len(pending) == 1, (
            f"Expected the claim to trigger a pending entry; got {pending}. "
            f"Output was: {result.output}"
        )
        assert pending[0]["source_kind"] == "claim"


def test_claim_cli_no_trigger_when_no_structural_language(tmp_path: Path) -> None:
    """A neutral claim (no structural-fix language) should NOT trigger
    the tracker. This guards against the broadening from over-firing."""
    from click.testing import CliRunner

    from divineos.cli import cli

    pending_file = tmp_path / "pending_structural_fixes.json"
    with patch.dict(
        "os.environ",
        {
            "DIVINEOS_HOME": str(pending_file.parent),
            "DIVINEOS_DATA_HOME": str(tmp_path),
        },
    ):
        runner = CliRunner()
        # Methodology gate requires --promotes/--demotes for tier 1-3.
        result = runner.invoke(
            cli,
            [
                "claim",
                "The sky appears blue from inside the atmosphere.",
                "--tier",
                "1",
                "--promotes",
                "atmospheric scattering analysis confirms blue at short wavelengths",
                "--demotes",
                "the sky appears non-blue at midday from sea level",
            ],
        )
        assert result.exit_code == 0
        # Neutral content should not trigger
        assert list_pending() == []


def test_correction_cli_no_trigger_when_no_structural_language(tmp_path: Path) -> None:
    """A neutral correction should NOT trigger the tracker."""
    from click.testing import CliRunner

    from divineos.cli import cli

    pending_file = tmp_path / "pending_structural_fixes.json"
    corrections_file = tmp_path / "corrections.jsonl"
    with patch.dict(
        "os.environ",
        {
            "DIVINEOS_HOME": str(pending_file.parent),
            "DIVINEOS_DATA_HOME": str(corrections_file.parent),
        },
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["correction", "you said the sky was green; it is blue."],
        )
        assert result.exit_code == 0
        assert list_pending() == []
