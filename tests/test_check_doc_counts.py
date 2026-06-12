"""Tests for the cited-path verification in scripts/check_doc_counts.py.

The check catches "doc cites X but X does not exist on disk" — the
fabricated-mansion-room / stale-package-list / wrong-file-path class
that numeric drift checks cannot catch. Added per Andrew 2026-05-16
after README audit found 16+ fact-errors in cited paths and names.

Pre-reg: prereg-4b5918f3b9fb (companion to stale-review surface — both
shipped same arc, both close fact-honesty discipline gaps).
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_doc_counts import (  # noqa: E402
    _extract_cited_paths,
    _files_with_conflict_markers,
    _resolve_cited_path,
    check_cited_paths,
)


class TestConflictMarkerGuard:
    """--fix must refuse to run on a conflicted doc — appending blindly into
    a merge-conflicted ARCHITECTURE.md duplicates entries into ghosts (the
    failure that broke PR #213, knowledge a9e533c2)."""

    def test_flags_file_with_conflict_markers(self, tmp_path):
        doc = tmp_path / "ARCHITECTURE.md"
        doc.write_text(
            "tree\n<<<<<<< HEAD\n  core/a.py\n=======\n  core/b.py\n>>>>>>> branch\n",
            encoding="utf-8",
        )
        result = _files_with_conflict_markers([doc])
        assert len(result) == 1

    def test_clean_file_not_flagged(self, tmp_path):
        doc = tmp_path / "ARCHITECTURE.md"
        doc.write_text("tree\n  core/a.py   does a thing\n", encoding="utf-8")
        assert _files_with_conflict_markers([doc]) == []

    def test_markdown_equals_rule_is_not_a_false_positive(self, tmp_path):
        # A run of '=' is legitimate Markdown (setext heading / rule); the
        # guard keys on the angle-bracket markers, not '=======', so this
        # must NOT be flagged as a conflict.
        doc = tmp_path / "README.md"
        doc.write_text("Title\n=======\n\nbody text\n", encoding="utf-8")
        assert _files_with_conflict_markers([doc]) == []

    def test_missing_file_skipped(self, tmp_path):
        assert _files_with_conflict_markers([tmp_path / "nope.md"]) == []


class TestExtractCitedPaths:
    def test_extracts_backticked_path(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("See `core/family/store.py` for details.", encoding="utf-8")
        result = _extract_cited_paths(doc)
        assert "core/family/store.py" in result

    def test_extracts_markdown_link_to_relative_file(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text(
            "Read [foundational truths](docs/foundational_truths.md) first.", encoding="utf-8"
        )
        result = _extract_cited_paths(doc)
        assert "docs/foundational_truths.md" in result

    def test_skips_external_urls(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("See [github](https://github.com/foo/bar) for source.", encoding="utf-8")
        result = _extract_cited_paths(doc)
        assert not any("github" in r for r in result)

    def test_strips_line_number_suffix(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("See `core/family/store.py:274` for wiring.", encoding="utf-8")
        result = _extract_cited_paths(doc)
        # Line-number-suffixed path should be stripped to just the file
        assert "core/family/store.py" in result

    def test_returns_empty_for_nonexistent_doc(self, tmp_path):
        doc = tmp_path / "nonexistent.md"
        assert _extract_cited_paths(doc) == set()


class TestResolveCitedPath:
    def test_resolves_repo_root_relative(self):
        # README.md exists at repo root
        result = _resolve_cited_path("README.md")
        assert result is not None
        assert result.exists()

    def test_resolves_src_divineos_relative(self):
        # core/holding.py is at src/divineos/core/holding.py
        result = _resolve_cited_path("core/holding.py")
        assert result is not None
        assert result.exists()

    def test_returns_none_for_missing(self):
        result = _resolve_cited_path("totally/fake/path/that/does/not/exist.py")
        assert result is None


class TestCheckCitedPaths:
    def test_empty_when_all_paths_resolve(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("See `core/holding.py` and `README.md`.", encoding="utf-8")
        errors = check_cited_paths([doc])
        assert errors == []

    def test_reports_missing_path(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("See `core/totally_fabricated_module.py` for details.", encoding="utf-8")
        errors = check_cited_paths([doc])
        assert len(errors) == 1
        assert "core/totally_fabricated_module.py" in errors[0]
        assert "MISSING-CITED-PATH" in errors[0]

    def test_handles_multiple_docs(self, tmp_path):
        doc1 = tmp_path / "doc1.md"
        doc1.write_text("Good: `README.md`. Bad: `fake/path.py`.", encoding="utf-8")
        doc2 = tmp_path / "doc2.md"
        doc2.write_text("Also bad: `another/fake.py`.", encoding="utf-8")
        errors = check_cited_paths([doc1, doc2])
        assert len(errors) == 2

    def test_skips_nonexistent_doc(self, tmp_path):
        doc = tmp_path / "nonexistent.md"
        errors = check_cited_paths([doc])
        assert errors == []


class TestMonotonicAutofix:
    """fix_test_counts and fix_hook_counts must be monotonic: only raise the
    documented count, never lower it. This breaks the cross-branch rebase
    conflict (Andrew 2026-06-12): two branches that both add tests can both
    auto-fix without colliding, because both raise toward higher numbers
    and the lower-count branch becomes a no-op once main has the higher
    count.

    Down-revisions (rare — test deletions or test-file removal) require
    manual edit; that's correct because down-revs deserve attention.
    """

    def _setup_doc_root(self, tmp_path, monkeypatch):
        """Point the check_doc_counts script at a temp ROOT so we don't
        modify the real repo docs during the test."""
        from scripts import check_doc_counts as cdc

        monkeypatch.setattr(cdc, "ROOT", tmp_path)
        # All four files fix_test_counts touches.
        (tmp_path / "CLAUDE.md").write_text("base", encoding="utf-8")
        (tmp_path / "README.md").write_text("base", encoding="utf-8")
        (tmp_path / "docs").mkdir(exist_ok=True)
        (tmp_path / "docs" / "ARCHITECTURE.md").write_text("base", encoding="utf-8")
        (tmp_path / "src" / "divineos").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "divineos" / "seed.json").write_text("{}", encoding="utf-8")
        return cdc

    def test_fix_test_counts_raises(self, tmp_path, monkeypatch):
        """Higher actual → rewrite happens."""
        cdc = self._setup_doc_root(tmp_path, monkeypatch)
        (tmp_path / "README.md").write_text("- **8,000+ tests**", encoding="utf-8")
        changed = cdc.fix_test_counts(8_500)
        assert "README.md" in changed
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "8,500" in text or "8500" in text
        assert "8,000" not in text

    def test_fix_test_counts_does_not_lower(self, tmp_path, monkeypatch):
        """Lower actual → no-op. The cross-branch conflict killer."""
        cdc = self._setup_doc_root(tmp_path, monkeypatch)
        (tmp_path / "README.md").write_text("- **8,500+ tests**", encoding="utf-8")
        changed = cdc.fix_test_counts(8_000)
        assert "README.md" not in changed
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        # The 8,500 stays untouched.
        assert "8,500" in text

    def test_fix_test_counts_equal_is_noop(self, tmp_path, monkeypatch):
        """Equal actual → no rewrite (nothing to change)."""
        cdc = self._setup_doc_root(tmp_path, monkeypatch)
        (tmp_path / "README.md").write_text("- **8,200+ tests**", encoding="utf-8")
        changed = cdc.fix_test_counts(8_200)
        assert "README.md" not in changed

    def test_fix_hook_counts_raises(self, tmp_path, monkeypatch):
        cdc = self._setup_doc_root(tmp_path, monkeypatch)
        (tmp_path / "README.md").write_text("(20 hooks, shell-level)", encoding="utf-8")
        changed = cdc.fix_hook_counts(35)
        assert "README.md" in changed
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "(35 hooks" in text

    def test_fix_hook_counts_does_not_lower(self, tmp_path, monkeypatch):
        cdc = self._setup_doc_root(tmp_path, monkeypatch)
        (tmp_path / "README.md").write_text("(35 hooks, shell-level)", encoding="utf-8")
        changed = cdc.fix_hook_counts(20)
        assert "README.md" not in changed
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        # The 35 stays untouched.
        assert "(35 hooks" in text
