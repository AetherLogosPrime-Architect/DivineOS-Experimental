"""Tests for audit auto-triage citation extraction + verification."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from divineos.core.audit_auto_triage import (
    _commit_exists,
    _extract_commit_shas,
    _extract_file_paths,
    _file_exists,
    _verify_finding,
    scan_open_findings,
)
from divineos.core.watchmen.types import (
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
    Tier,
)


def _make_finding(description: str, finding_id: str = "find-test") -> Finding:
    return Finding(
        finding_id=finding_id,
        round_id="round-test",
        created_at=0.0,
        actor="test",
        severity=Severity.HIGH,
        category=FindingCategory.KNOWLEDGE,
        title="t",
        description=description,
        status=FindingStatus.OPEN,
        tier=Tier.WEAK,
    )


class TestFilePathExtraction:
    def test_extracts_dotted_paths(self):
        text = "Fix landed in src/divineos/core/foo.py and tests/test_foo.py."
        assert _extract_file_paths(text) == [
            "src/divineos/core/foo.py",
            "tests/test_foo.py",
        ]

    def test_extracts_various_extensions(self):
        text = "Updated docs/ARCHITECTURE.md, settings.json, and scripts/run.sh."
        paths = _extract_file_paths(text)
        assert "docs/ARCHITECTURE.md" in paths
        assert "settings.json" in paths
        assert "scripts/run.sh" in paths

    def test_dedups(self):
        text = "foo.py and foo.py again, and foo.py once more"
        assert _extract_file_paths(text) == ["foo.py"]

    def test_no_paths(self):
        assert _extract_file_paths("Nothing here that looks like a file.") == []


class TestCommitShaExtraction:
    def test_requires_commit_context(self):
        """Bare hex words without commit-context are NOT extracted (UUIDs, hashes-in-text)."""
        text = "The id ab12cd34ef56 appears here but it is not a commit."
        assert _extract_commit_shas(text) == []

    def test_picks_up_commit_keyword(self):
        text = "Fix landed in commit 4bb774d for the logging bug."
        assert "4bb774d" in _extract_commit_shas(text)

    def test_picks_up_fixed_in_phrasing(self):
        text = "fixed: commit 42a7a8ff broadens the exception."
        assert "42a7a8ff" in _extract_commit_shas(text)

    def test_dedups(self):
        text = "commit 4bb774dd, commit 4bb774dd, commit 4bb774dd"
        assert _extract_commit_shas(text) == ["4bb774dd"]


class TestFileExists:
    def test_returns_true_for_existing_file(self, tmp_path):
        (tmp_path / "a.txt").write_text("x", encoding="utf-8")
        assert _file_exists("a.txt", tmp_path) is True

    def test_returns_false_for_missing_file(self, tmp_path):
        assert _file_exists("nope.txt", tmp_path) is False

    def test_handles_absolute_path(self, tmp_path):
        p = tmp_path / "abs.txt"
        p.write_text("x", encoding="utf-8")
        assert _file_exists(str(p), tmp_path) is True

    def test_falls_back_to_src_divineos_prefix(self, tmp_path):
        """Live-observed 2026-06-13: find-627bd61e3974 cited
        `core/family/store.py` (no `src/divineos/` prefix). Pre-fallback
        the tool returned not-verified; with the fallback it resolves."""
        nested = tmp_path / "src" / "divineos" / "core" / "family"
        nested.mkdir(parents=True)
        (nested / "store.py").write_text("x", encoding="utf-8")
        assert _file_exists("core/family/store.py", tmp_path) is True

    def test_falls_back_to_tests_prefix(self, tmp_path):
        """Same pattern for tests/ — finding bodies cite
        `test_detector_wiring_contract.py` without the tests/ prefix."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_detector_wiring_contract.py").write_text("x", encoding="utf-8")
        assert _file_exists("test_detector_wiring_contract.py", tmp_path) is True

    def test_glob_basename_resolves_in_deeper_subfolder(self, tmp_path):
        """Live-observed 2026-06-13: find-4d2de51ae999 cited
        `knowledge_commands.py` (actual location: src/divineos/cli/...).
        The prefix fallback alone misses; glob-by-basename catches it."""
        deep = tmp_path / "src" / "divineos" / "cli"
        deep.mkdir(parents=True)
        (deep / "knowledge_commands.py").write_text("x", encoding="utf-8")
        assert _file_exists("knowledge_commands.py", tmp_path) is True

    def test_glob_basename_ambiguous_resolves_first_hit(self, tmp_path):
        """Documented behavior: when a basename matches more than one
        file under the glob roots, the first hit counts as verified.
        Operator-decided resolution doesn't get blocked on ambiguity."""
        a = tmp_path / "src" / "divineos" / "core"
        b = tmp_path / "src" / "divineos" / "cli"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        (a / "shared_name.py").write_text("x", encoding="utf-8")
        (b / "shared_name.py").write_text("x", encoding="utf-8")
        assert _file_exists("shared_name.py", tmp_path) is True

    def test_glob_skipped_for_multi_segment_path(self, tmp_path):
        """A multi-segment path with no recognized prefix is unlikely
        to be a real citation; glob-search is bare-basename-only."""
        # No matching file exists; the multi-segment path with no known
        # prefix should NOT trigger the glob fallback.
        deep = tmp_path / "src" / "divineos" / "core" / "family"
        deep.mkdir(parents=True)
        (deep / "store.py").write_text("x", encoding="utf-8")
        # The same file resolves via prefix fallback (test above), but
        # an unrelated multi-segment string with no prefix shouldn't
        # accidentally resolve via glob.
        assert _file_exists("random/path/store.py", tmp_path) is False

    def test_does_not_double_prefix(self, tmp_path):
        """Paths already prefixed with src/divineos or tests must NOT be
        re-tried under another prefix — otherwise
        `src/divineos/nonexistent.py` would silently resolve against
        `tests/src/divineos/nonexistent.py`."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "src" / "divineos").mkdir(parents=True)
        (tmp_path / "tests" / "src" / "divineos" / "nope.py").write_text("x", encoding="utf-8")
        assert _file_exists("src/divineos/nope.py", tmp_path) is False


class TestCommitExists:
    def test_returns_false_when_git_fails(self, tmp_path):
        # tmp_path is not a git repo; cat-file should fail.
        assert _commit_exists("abc1234", tmp_path) is False

    def test_returns_true_when_git_succeeds(self, tmp_path):
        with patch("divineos.core.audit_auto_triage.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            assert _commit_exists("abc1234", tmp_path) is True

    def test_returns_false_on_timeout(self, tmp_path):
        with patch("divineos.core.audit_auto_triage.subprocess.run") as run:
            run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)
            assert _commit_exists("abc1234", tmp_path) is False


class TestVerifyFinding:
    def test_zero_citations_zero_confidence(self, tmp_path):
        f = _make_finding("No citations here at all.")
        verdict = _verify_finding(f, tmp_path)
        assert verdict.total == 0
        assert verdict.confidence == 0.0

    def test_partial_verification(self, tmp_path):
        (tmp_path / "exists.py").write_text("x", encoding="utf-8")
        f = _make_finding("Fix in exists.py and missing.py and commit deadbeef1234.")
        with patch("divineos.core.audit_auto_triage._commit_exists", return_value=False):
            verdict = _verify_finding(f, tmp_path)
        # 2 file citations + 1 commit citation; only exists.py verifies.
        assert verdict.total == 3
        assert verdict.verified_count == 1
        assert abs(verdict.confidence - 1 / 3) < 1e-6

    def test_full_verification(self, tmp_path):
        (tmp_path / "a.py").write_text("x", encoding="utf-8")
        f = _make_finding("Landed in commit abc1234 and file a.py.")
        with patch("divineos.core.audit_auto_triage._commit_exists", return_value=True):
            verdict = _verify_finding(f, tmp_path)
        assert verdict.verified_count == verdict.total == 2
        assert verdict.confidence == 1.0


class TestScanOpenFindings:
    def test_ranks_by_confidence(self, tmp_path):
        (tmp_path / "real.py").write_text("x", encoding="utf-8")
        a = _make_finding("All real: real.py.", "find-a")
        b = _make_finding("Half real: real.py and fake.py.", "find-b")
        with patch("divineos.core.audit_auto_triage.list_findings", return_value=[b, a]):
            verdicts = scan_open_findings(min_confidence=0.0, min_citations=1, repo_root=tmp_path)
        assert [v.finding.finding_id for v in verdicts] == ["find-a", "find-b"]

    def test_filters_below_min_confidence(self, tmp_path):
        a = _make_finding("Only fake: fake.py.", "find-a")
        with patch("divineos.core.audit_auto_triage.list_findings", return_value=[a]):
            verdicts = scan_open_findings(min_confidence=0.5, min_citations=1, repo_root=tmp_path)
        assert verdicts == []

    def test_filters_below_min_citations(self, tmp_path):
        a = _make_finding("No citations here.", "find-a")
        with patch("divineos.core.audit_auto_triage.list_findings", return_value=[a]):
            verdicts = scan_open_findings(min_confidence=0.0, min_citations=1, repo_root=tmp_path)
        assert verdicts == []
