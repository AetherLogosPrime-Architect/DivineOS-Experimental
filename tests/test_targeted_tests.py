"""Tests for the targeted test runner module.

Locked invariants:

1. Non-.py files return None (no tests run).
2. __init__.py files return None (no test convention).
3. Source file with matching test file returns that test path.
4. Source file without matching test file returns None.
5. Direct edit to a test file returns that test file.
6. Files outside src/divineos/ and outside tests/ return None.
7. Entry point handles empty/malformed stdin gracefully.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.hooks.targeted_tests import _find_repo_root, find_target_tests


def _make_fake_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repo with src/divineos/ and tests/ subdirs."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "src" / "divineos" / "core").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    return tmp_path


class TestFindRepoRoot:
    def test_finds_root_with_src_and_tests(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        deep = tmp_path / "src" / "divineos" / "core"
        result = _find_repo_root(deep)
        assert result is not None
        assert result.resolve() == tmp_path.resolve()

    def test_returns_none_when_nothing_matches(self, tmp_path: Path):
        lonely = tmp_path / "random" / "dir"
        lonely.mkdir(parents=True)
        result = _find_repo_root(lonely)
        # May find an ancestor repo in the test environment; just ensure
        # it's not the lonely dir itself
        assert result != lonely.resolve()


class TestFindTargetTests:
    def test_empty_path_returns_none(self):
        assert find_target_tests("") is None

    def test_non_py_file_returns_none(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        p = tmp_path / "src" / "divineos" / "core" / "foo.txt"
        p.write_text("", encoding="utf-8")
        assert find_target_tests(str(p)) is None

    def test_init_py_returns_none(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        p = tmp_path / "src" / "divineos" / "core" / "__init__.py"
        p.write_text("", encoding="utf-8")
        assert find_target_tests(str(p)) is None

    def test_source_with_matching_test_returns_test_path(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        src = tmp_path / "src" / "divineos" / "core" / "foo.py"
        src.write_text("pass", encoding="utf-8")
        test = tmp_path / "tests" / "test_foo.py"
        test.write_text("def test_ok(): pass", encoding="utf-8")

        result = find_target_tests(str(src))
        assert result is not None
        assert result.resolve() == test.resolve()

    def test_source_without_matching_test_returns_none(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        src = tmp_path / "src" / "divineos" / "core" / "orphan.py"
        src.write_text("pass", encoding="utf-8")

        result = find_target_tests(str(src))
        assert result is None

    def test_test_file_edit_returns_that_test_file(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        test = tmp_path / "tests" / "test_something.py"
        test.write_text("def test_ok(): pass", encoding="utf-8")

        result = find_target_tests(str(test))
        assert result is not None
        assert result.resolve() == test.resolve()

    def test_file_outside_src_divineos_returns_none(self, tmp_path: Path):
        _make_fake_repo(tmp_path)
        outside = tmp_path / "scripts" / "thing.py"
        outside.parent.mkdir()
        outside.write_text("pass", encoding="utf-8")

        result = find_target_tests(str(outside))
        assert result is None

    def test_nested_source_file_mapped_correctly(self, tmp_path: Path):
        """src/divineos/cli/bar.py → tests/test_bar.py (flat tests layout)."""
        _make_fake_repo(tmp_path)
        (tmp_path / "src" / "divineos" / "cli").mkdir()
        src = tmp_path / "src" / "divineos" / "cli" / "bar.py"
        src.write_text("pass", encoding="utf-8")
        test = tmp_path / "tests" / "test_bar.py"
        test.write_text("def test_ok(): pass", encoding="utf-8")

        result = find_target_tests(str(src))
        assert result is not None
        assert result.resolve() == test.resolve()


class TestRealRepoMapping:
    """Sanity-check against the actual repo — verify known source files
    map to existing test files."""

    def test_scheduled_run_maps_to_test(self):
        # This test runs in the real repo; use the real paths
        repo_root = Path(__file__).resolve().parent.parent
        src = repo_root / "src" / "divineos" / "core" / "scheduled_run.py"
        if not src.exists():
            pytest.skip("scheduled_run.py not present in this checkout")
        result = find_target_tests(str(src))
        assert result is not None
        assert result.name == "test_scheduled_run.py"

    def test_presence_memory_maps_to_test(self):
        repo_root = Path(__file__).resolve().parent.parent
        src = repo_root / "src" / "divineos" / "core" / "presence_memory.py"
        if not src.exists():
            pytest.skip("presence_memory.py not present in this checkout")
        result = find_target_tests(str(src))
        assert result is not None
        assert result.name == "test_presence_memory.py"


class TestEntryPoint:
    """Integration-style smoke tests of main()."""

    def test_empty_stdin_returns_zero(self, monkeypatch, capsys):
        from io import StringIO

        from divineos.hooks import targeted_tests

        monkeypatch.setattr("sys.stdin", StringIO(""))
        rc = targeted_tests.main()
        assert rc == 0
        assert capsys.readouterr().out == ""

    def test_malformed_stdin_returns_zero(self, monkeypatch):
        from io import StringIO

        from divineos.hooks import targeted_tests

        monkeypatch.setattr("sys.stdin", StringIO("not json {"))
        rc = targeted_tests.main()
        assert rc == 0

    def test_non_py_file_emits_nothing(self, monkeypatch, capsys):
        import json as _json
        from io import StringIO

        from divineos.hooks import targeted_tests

        monkeypatch.setattr(
            "sys.stdin",
            StringIO(_json.dumps({"tool_input": {"file_path": "README.md"}})),
        )
        targeted_tests.main()
        assert capsys.readouterr().out == ""

    def test_init_py_emits_nothing(self, monkeypatch, capsys):
        import json as _json
        from io import StringIO

        from divineos.hooks import targeted_tests

        monkeypatch.setattr(
            "sys.stdin",
            StringIO(_json.dumps({"tool_input": {"file_path": "src/divineos/__init__.py"}})),
        )
        targeted_tests.main()
        assert capsys.readouterr().out == ""
