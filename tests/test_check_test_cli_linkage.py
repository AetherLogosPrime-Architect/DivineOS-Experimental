"""Tests for `scripts/check_test_cli_linkage.py`.

The check exists to catch the PR #264 failure mode: test file references
a CLI command that never got registered. These tests pin both halves —
the check passes when references match, and fails loudly when they
don't.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _load_module():
    """Import the check script as a module without running its main()."""
    spec = importlib.util.spec_from_file_location(
        "check_test_cli_linkage",
        _SCRIPTS_DIR / "check_test_cli_linkage.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def linkage():
    return _load_module()


class TestScanRegex:
    def test_invoke_pattern_extracts_first_arg(self, tmp_path, linkage):
        f = tmp_path / "test_x.py"
        f.write_text(
            'runner = CliRunner()\nrunner.invoke(cli, ["mycommand", "--flag"])\n',
            encoding="utf-8",
        )
        refs = linkage._scan_tests(tmp_path)
        assert "mycommand" in refs

    def test_run_helper_pattern(self, tmp_path, linkage):
        f = tmp_path / "test_y.py"
        f.write_text(
            'def _run(*args): ...\n_run("othercommand", "arg")\n',
            encoding="utf-8",
        )
        refs = linkage._scan_tests(tmp_path)
        assert "othercommand" in refs

    def test_skips_non_literal_args(self, tmp_path, linkage):
        f = tmp_path / "test_z.py"
        f.write_text(
            'name = get_name()\nrunner.invoke(cli, [name, "arg"])\n',
            encoding="utf-8",
        )
        refs = linkage._scan_tests(tmp_path)
        assert refs == {}

    def test_collects_paths_per_command(self, tmp_path, linkage):
        a = tmp_path / "test_a.py"
        b = tmp_path / "test_b.py"
        a.write_text('runner.invoke(cli, ["shared", "x"])\n', encoding="utf-8")
        b.write_text('runner.invoke(cli, ["shared", "y"])\n', encoding="utf-8")
        refs = linkage._scan_tests(tmp_path)
        assert len(refs["shared"]) == 2


class TestRegisteredCommands:
    def test_returns_real_command_set(self, linkage):
        cmds = linkage._registered_commands()
        # Sanity: known core commands must register.
        assert "briefing" in cmds
        assert "preflight" in cmds
        assert "extract" in cmds


class TestEndToEnd:
    """Verify the check itself catches the #264 failure mode."""

    def test_passes_when_all_refs_register(self, tmp_path, linkage, monkeypatch):
        f = tmp_path / "test_pass.py"
        f.write_text('runner.invoke(cli, ["briefing"])\n', encoding="utf-8")
        refs = linkage._scan_tests(tmp_path)
        registered = linkage._registered_commands()
        missing = {c: p for c, p in refs.items() if c not in registered}
        assert missing == {}

    def test_catches_unregistered_command(self, tmp_path, linkage):
        """Synthesize the exact #264 failure: test references a command
        the CLI never registered. The check must flag it."""
        f = tmp_path / "test_fake.py"
        f.write_text(
            'runner.invoke(cli, ["this_command_does_not_exist_anywhere"])\n',
            encoding="utf-8",
        )
        refs = linkage._scan_tests(tmp_path)
        registered = linkage._registered_commands()
        missing = {c: p for c, p in refs.items() if c not in registered}
        assert "this_command_does_not_exist_anywhere" in missing


class TestRunningCheckOnRepo:
    """Smoke: running the script over the actual tests/ tree should pass.
    If this fails, either the check has a regression OR a real failure
    of the #264 shape is in the tree."""

    def test_repo_passes(self, linkage):
        repo_root = Path(__file__).parent.parent
        refs = linkage._scan_tests(repo_root / "tests")
        registered = linkage._registered_commands()
        missing = {c: p for c, p in refs.items() if c not in registered}
        if missing:
            details = "\n".join(
                f"  '{c}' referenced in {[str(pp.relative_to(repo_root)) for pp in pps]}"
                for c, pps in missing.items()
            )
            raise AssertionError(f"Test-CLI linkage broken in repo:\n{details}")
