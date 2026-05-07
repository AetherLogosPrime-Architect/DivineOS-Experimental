"""Tests for the expanded doc-drift checker (architecture tree verification)."""

import sys
from pathlib import Path

# scripts/ isn't a package — add project root to sys.path so we can import it
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.check_doc_counts import (  # noqa: E402
    _extract_tree_paths,
    _format_count,
    _get_actual_py_files,
    check_architecture_tree,
    count_hooks_wired,
    extract_documented_counts,
    fix_hook_counts,
    fix_test_counts,
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
        paths = _extract_tree_paths(readme, arch_doc_path=tmp_path / "nonexistent.md")
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
        paths = _extract_tree_paths(readme, arch_doc_path=tmp_path / "nonexistent.md")
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
        paths = _extract_tree_paths(readme, arch_doc_path=tmp_path / "nonexistent.md")
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
        paths = _extract_tree_paths(readme, arch_doc_path=tmp_path / "nonexistent.md")
        assert "seed.json" not in paths
        assert "core/ledger.py" in paths

    def test_returns_empty_for_no_section(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# No architecture section here\n\nJust text.\n")
        paths = _extract_tree_paths(readme, arch_doc_path=tmp_path / "nonexistent.md")
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
        paths = _extract_tree_paths(readme, arch_doc_path=tmp_path / "nonexistent.md")
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
        errors = check_architecture_tree(readme, arch_doc_path=tmp_path / "nonexistent.md")
        ghost_errors = [e for e in errors if "GHOST" in e]
        assert len(ghost_errors) >= 1

    def test_missing_readme_no_errors(self, tmp_path):
        errors = check_architecture_tree(tmp_path / "nope.md")
        assert errors == []


class TestAutoFix:
    """Test the --fix auto-update functionality."""

    def test_format_count(self):
        assert _format_count(3646) == "3,646+"
        assert _format_count(100) == "100+"
        assert _format_count(0) == "0+"

    def test_fix_updates_drifted_file(self, tmp_path, monkeypatch):
        """fix_test_counts should update stale test counts in doc files."""
        # Create a fake doc file with old count
        fake_doc = tmp_path / "CLAUDE.md"
        fake_doc.write_text("tests/  # 2,000+ tests (real DB)")

        # Monkeypatch ROOT so fix_test_counts finds our fake file
        import scripts.check_doc_counts as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)

        changed = fix_test_counts(3646)
        assert "CLAUDE.md" in changed

        updated = fake_doc.read_text()
        assert "3,646+ tests" in updated
        assert "2,000" not in updated

    def test_fix_no_change_when_current(self, tmp_path, monkeypatch):
        """If counts are already correct, no files should be changed."""
        fake_doc = tmp_path / "CLAUDE.md"
        fake_doc.write_text("tests/  # 500+ tests (real DB)")

        import scripts.check_doc_counts as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)

        changed = fix_test_counts(500)
        assert changed == []


class TestHookCounts:
    """Test hook-count tracking added 2026-05-07 per round-2 audit.

    The README claimed "9 enforcement hooks" while settings.json wired
    16; the drift went undetected for months because no checker tracked
    it. These tests pin the mechanism so future drift gets caught at
    test-time and on every commit via the precommit gate.
    """

    def test_count_hooks_wired_real_settings(self):
        """count_hooks_wired returns non-zero for the real settings.json."""
        n = count_hooks_wired()
        assert n > 0, (
            "count_hooks_wired() returned 0 for the real settings.json. "
            "Either the file is missing/empty/malformed, or the schema "
            "changed and this counter needs updating."
        )

    def test_count_hooks_missing_settings(self, tmp_path, monkeypatch):
        """Missing settings.json returns 0, not exception."""
        import scripts.check_doc_counts as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        assert count_hooks_wired() == 0

    def test_count_hooks_malformed_settings(self, tmp_path, monkeypatch):
        """Unparseable settings.json returns 0 (fail-soft)."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{ not valid json")
        import scripts.check_doc_counts as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        assert count_hooks_wired() == 0

    def test_extract_documented_counts_finds_hooks(self, tmp_path):
        """Extractor picks up both shapes: 'N enforcement hooks' and '(N hooks,'."""
        fake = tmp_path / "README.md"
        content = (
            "- **9 Claude Code enforcement hooks**\n"
            "- enforcement hooks (9 hooks, shell-level entry points)\n"
        )
        fake.write_text(content)
        findings = extract_documented_counts(fake)
        hook_findings = [f for f in findings if f[0] == "hooks"]
        assert len(hook_findings) == 2
        assert all(f[1] == 9 for f in hook_findings)

    def test_fix_updates_drifted_hook_count(self, tmp_path, monkeypatch):
        """fix_hook_counts updates both shapes of the hook claim."""
        fake = tmp_path / "README.md"
        content = (
            "## At a glance\n"
            "- **9 Claude Code enforcement hooks**\n"
            "## Top-level\n"
            "Claude Code enforcement hooks (9 hooks, shell-level entry points).\n"
        )
        fake.write_text(content)
        import scripts.check_doc_counts as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        changed = fix_hook_counts(16)
        assert "README.md" in changed

        updated = fake.read_text()
        assert "16 Claude Code enforcement hooks" in updated
        assert "(16 hooks," in updated
        assert "9 Claude Code enforcement hooks" not in updated
        assert "(9 hooks," not in updated

    def test_fix_no_change_when_current(self, tmp_path, monkeypatch):
        """When doc already matches actual count, no file changes."""
        fake = tmp_path / "README.md"
        fake.write_text("- **16 Claude Code enforcement hooks**\n")
        import scripts.check_doc_counts as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        changed = fix_hook_counts(16)
        assert changed == []
