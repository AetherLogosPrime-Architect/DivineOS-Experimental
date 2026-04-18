"""Tests for the blind_coding behavioral test and its
positive-evidence path.

Locks four invariants:

1. ``analyze_edit_read_pairing`` produces one EditReadPairing per Edit,
   with read_before_edit reflecting whether a prior Read of the same
   path appeared earlier in the tool-call sequence.
2. ``test_blind_coding`` passes iff every Edit in the session was
   preceded by an in-session Read of the same file.
3. ``blind_coding`` is listed in the categories_with_evidence_detector
   so the lesson can transition to RESOLVED.
4. ``extract_lessons_from_report`` accepts edit_read_pairings so the
   detector can fire.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from divineos.analysis._session_types import EditReadPairing
from divineos.analysis.session_features import analyze_edit_read_pairing
from divineos.core.knowledge.lessons import _run_single_test


def _asst_tool(tool_name: str, file_path: str, ts: str = "1.0") -> dict:
    """Build one assistant record with one tool_use."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"tool-{tool_name}-{file_path}",
                    "name": tool_name,
                    "input": {"file_path": file_path},
                }
            ]
        },
        "timestamp": ts,
    }


class TestAnalyzeEditReadPairing:
    def test_empty_records(self):
        assert analyze_edit_read_pairing([]) == []

    def test_read_then_edit_same_path_is_paired(self):
        records = [
            _asst_tool("Read", "src/foo.py"),
            _asst_tool("Edit", "src/foo.py"),
        ]
        pairings = analyze_edit_read_pairing(records)
        assert len(pairings) == 1
        assert pairings[0].read_before_edit is True
        assert pairings[0].file_path == "src/foo.py"

    def test_edit_without_read_is_unpaired(self):
        records = [_asst_tool("Edit", "src/foo.py")]
        pairings = analyze_edit_read_pairing(records)
        assert len(pairings) == 1
        assert pairings[0].read_before_edit is False

    def test_read_of_different_file_does_not_pair(self):
        records = [
            _asst_tool("Read", "src/bar.py"),
            _asst_tool("Edit", "src/foo.py"),
        ]
        pairings = analyze_edit_read_pairing(records)
        assert pairings[0].read_before_edit is False

    def test_multiple_edits_one_read(self):
        """A single Read covers subsequent Edits of the same path."""
        records = [
            _asst_tool("Read", "src/foo.py"),
            _asst_tool("Edit", "src/foo.py"),
            _asst_tool("Edit", "src/foo.py"),
        ]
        pairings = analyze_edit_read_pairing(records)
        assert len(pairings) == 2
        assert all(p.read_before_edit for p in pairings)

    def test_edit_after_read_of_different_file(self):
        records = [
            _asst_tool("Read", "src/a.py"),
            _asst_tool("Edit", "src/a.py"),
            _asst_tool("Edit", "src/b.py"),
        ]
        pairings = analyze_edit_read_pairing(records)
        assert len(pairings) == 2
        assert pairings[0].read_before_edit is True
        assert pairings[1].read_before_edit is False

    def test_ignores_write_tool(self):
        """Write tool creates new files — no Read required."""
        records = [_asst_tool("Write", "src/new.py")]
        pairings = analyze_edit_read_pairing(records)
        assert pairings == []


class TestBlindCodingBehavioralTest:
    """_run_single_test dispatches to test_blind_coding."""

    def test_no_edits_passes(self):
        features = MagicMock(edit_read_pairings=[])
        passed, reason = _run_single_test("test_blind_coding", None, features)
        assert passed is True
        assert "no Edit" in reason

    def test_all_edits_paired_passes(self):
        features = MagicMock(
            edit_read_pairings=[
                EditReadPairing(edit_timestamp="1", file_path="a.py", read_before_edit=True),
                EditReadPairing(edit_timestamp="2", file_path="b.py", read_before_edit=True),
            ]
        )
        passed, reason = _run_single_test("test_blind_coding", None, features)
        assert passed is True
        assert "2 Edit" in reason

    def test_any_unpaired_fails(self):
        features = MagicMock(
            edit_read_pairings=[
                EditReadPairing(edit_timestamp="1", file_path="a.py", read_before_edit=True),
                EditReadPairing(edit_timestamp="2", file_path="b.py", read_before_edit=False),
            ]
        )
        passed, reason = _run_single_test("test_blind_coding", None, features)
        assert passed is False
        assert "1/2" in reason

    def test_feature_absent_passes_safely(self):
        """If edit_read_pairings feature isn't present, don't fail
        the test — the old behavior was no-op."""
        features = MagicMock(spec=[])
        passed, reason = _run_single_test("test_blind_coding", None, features)
        assert passed is True


class TestCategoriesWithEvidenceDetector:
    def test_blind_coding_listed_in_loop_status(self):
        from divineos.core.knowledge.lessons import _lesson_loop_status

        status = _lesson_loop_status()
        assert "blind_coding" in status


class TestExtractionSignature:
    """The extraction layer accepts edit_read_pairings so the detector
    can fire from the analysis pipeline."""

    def test_accepts_edit_read_pairings_param(self):
        import inspect

        from divineos.core.knowledge.lessons import extract_lessons_from_report

        sig = inspect.signature(extract_lessons_from_report)
        assert "edit_read_pairings" in sig.parameters
