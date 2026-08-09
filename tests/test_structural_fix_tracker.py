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
        # Correction body must satisfy the root-cause+fix pairing gate
        # (Andrew 2026-07-29): every filed correction requires "root
        # cause:" AND ("structural fix:" or "behavior change:"), plus
        # file-path evidence when "structural fix:" is claimed. The
        # structural-fix-shape trigger words ("you should build a
        # detector") appear inside the body so the tracker still fires.
        result = runner.invoke(
            cli,
            [
                "correction",
                "root cause: prior action X. positives: named the class. structural fix: modified "
                "src/example.py — you should build a detector that catches "
                "this pattern.",
            ],
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
        # Correction body satisfies the pairing gate but contains no
        # structural-fix-shape trigger words in the free-text portion,
        # so the tracker should NOT fire even though the correction
        # itself passes the gate.
        result = runner.invoke(
            cli,
            [
                "correction",
                "root cause: I said the sky was green. positives: caught before shipping. behavior change: "
                "I will call it blue from now on.",
            ],
        )
        assert result.exit_code == 0
        assert list_pending() == []


def test_identical_content_becomes_one_row_with_a_count(tmp_path: Path) -> None:
    """Andrew 2026-08-09: "65 duplicate rows IS noise and is junk to be
    deleted.. it should be a single row with 65 stamps on it."

    The backlog held 129 rows, 65 of them the same emergency-bypass text fired
    across 11 days. Those 64 extra rows carried nothing the first did not, and
    buried the 64 distinct obligations sharing the list with them.
    """
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(tmp_path)}):
        first = record_pending_fix("the same obligation, named again", trigger="structural fix")
        for _ in range(9):
            again = record_pending_fix("the same obligation, named again", trigger="structural fix")
            assert again == first, "a repeat must return the existing id, not mint a row"

        rows = list_pending()
        assert len(rows) == 1
        assert rows[0]["occurrences"] == 10
        assert rows[0]["last_seen"] >= rows[0]["created_at"]
        # Bounded on purpose: an unbounded stamp list re-grows the problem it fixes.
        assert len(rows[0]["stamps"]) <= 20


def test_distinct_obligations_are_not_collapsed(tmp_path: Path) -> None:
    """The dedup must be narrow. Collapsing genuinely different obligations
    would be the same information loss the duplicates caused, in reverse."""
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(tmp_path)}):
        a = record_pending_fix("wire the teachings module into pre-composition")
        b = record_pending_fix("auto-commit letters so branch ops cannot eat them")
        assert a != b
        texts = {(r.get("content_excerpt") or "") for r in list_pending()}
        assert "wire the teachings module into pre-composition" in texts
        assert "auto-commit letters so branch ops cannot eat them" in texts


def test_a_second_occurrence_arms_a_must_read(tmp_path: Path) -> None:
    """Andrew 2026-08-09: "willful ignorance is another issue on its own, and
    is treated the same way, so i still need to be sure."

    He could not be sure and neither could I. Nothing recorded whether the
    backlog was ever OPENED -- only whether it had content -- so "could not
    see it" and "did not look" were indistinguishable from outside, and my own
    testimony is exactly the evidence that cannot settle that question.

    A second occurrence means the first telling did not land, so that is where
    a panel I can read past becomes a door I have to open. After this, a
    further occurrence means I read it and still shipped nothing, which is the
    distinction he asked for -- recorded rather than asserted.
    """
    from divineos.core import must_read
    from divineos.core.multiplex_panels import _owed_fixes_panel_content

    with patch.dict("os.environ", {"DIVINEOS_HOME": str(tmp_path)}):
        must_read._dir(str(tmp_path)).mkdir(parents=True, exist_ok=True)

        record_pending_fix("an obligation nobody shipped for", trigger="structural fix")
        armed, _ = must_read.pending(str(tmp_path))
        _owed_fixes_panel_content()
        first_pass, _ = must_read.pending(str(tmp_path))
        assert not first_pass, "one telling is not yet evidence the telling failed"

        record_pending_fix("an obligation nobody shipped for", trigger="structural fix")
        rows = list_pending()
        assert len(rows) == 1 and rows[0]["occurrences"] == 2

        _owed_fixes_panel_content()
        armed, err = must_read.pending(str(tmp_path))
        assert err is None
        assert armed, "a repeated obligation must become unskippable"
