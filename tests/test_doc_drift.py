"""Tests for the expanded doc-drift checker (architecture tree verification)."""

from pathlib import Path

from scripts.check_doc_counts import (
    _extract_tree_paths,
    _get_actual_py_files,
    check_architecture_tree,
)


class TestExtractTreePaths:
    """Parse architecture tree from README markdown."""

    def test_extracts_top_level_files(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Architecture\n\n```\nsrc/divineos/\n"
            "  __init__.py       Package init\n"
            "  __main__.py       Entry point\n"
            "```\n"
        )
        paths = _extract_tree_paths(readme)
        assert "__init__.py" in paths
        assert "__main__.py" in paths

    def test_extracts_nested_files(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Architecture\n\n```\nsrc/divineos/\n"
            "  cli/               CLI package\n"
            "    __init__.py      Entry point\n"
            "    commands.py      Commands\n"
            "  core/              Core package\n"
            "    ledger.py        Event store\n"
            "```\n"
        )
        paths = _extract_tree_paths(readme)
        assert "cli/__init__.py" in paths
        assert "cli/commands.py" in paths
        assert "core/ledger.py" in paths

    def test_extracts_deeply_nested(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Architecture\n\n```\nsrc/divineos/\n"
            "  core/\n"
            "    knowledge/       Knowledge engine\n"
            "      _base.py      DB connection\n"
            "      extraction.py Extraction\n"
            "```\n"
        )
        paths = _extract_tree_paths(readme)
        assert "core/knowledge/_base.py" in paths
        assert "core/knowledge/extraction.py" in paths

    def test_skips_non_py_files(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Architecture\n\n```\nsrc/divineos/\n"
            "  seed.json         Seed data\n"
            "  core/\n"
            "    ledger.py       Store\n"
            "```\n"
        )
        paths = _extract_tree_paths(readme)
        assert "seed.json" not in paths
        assert "core/ledger.py" in paths

    def test_returns_empty_for_no_section(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# No architecture section here\n\nJust text.\n")
        paths = _extract_tree_paths(readme)
        assert paths == []

    def test_sibling_directories_not_nested(self, tmp_path):
        """cli/ and core/ at same indent should be siblings, not nested."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Architecture\n\n```\nsrc/divineos/\n"
            "  cli/\n"
            "    a.py            A\n"
            "  core/\n"
            "    b.py            B\n"
            "```\n"
        )
        paths = _extract_tree_paths(readme)
        assert "cli/a.py" in paths
        assert "core/b.py" in paths
        # Should NOT have cli/core/b.py
        assert "cli/core/b.py" not in paths


class TestGetActualFiles:
    """Verify actual file collection."""

    def test_returns_set(self):
        files = _get_actual_py_files()
        assert isinstance(files, set)
        assert len(files) > 0

    def test_includes_known_file(self):
        files = _get_actual_py_files()
        assert "core/ledger.py" in files

    def test_uses_forward_slashes(self):
        files = _get_actual_py_files()
        for f in files:
            assert "\\" not in f


class TestCheckArchitectureTree:
    """Full architecture tree verification."""

    def test_real_readme_passes(self):
        readme = Path(__file__).parent.parent / "README.md"
        errors = check_architecture_tree(readme)
        assert len(errors) == 0, f"Tree drift: {errors}"

    def test_detects_ghost_file(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Architecture\n\n```\nsrc/divineos/\n"
            "  core/\n"
            "    nonexistent_file.py  Does not exist\n"
            "```\n"
        )
        errors = check_architecture_tree(readme)
        ghost_errors = [e for e in errors if "GHOST" in e]
        assert len(ghost_errors) >= 1

    def test_missing_readme_no_errors(self, tmp_path):
        errors = check_architecture_tree(tmp_path / "nope.md")
        assert errors == []
