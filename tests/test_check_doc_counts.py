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
