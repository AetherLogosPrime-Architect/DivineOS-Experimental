"""Tests for scripts/divineos_wrapper.py — pip ping-pong CLI-dispatch fix."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


def _load_wrapper_module():
    """Load the wrapper as a module without needing it in the package tree."""
    repo_root = Path(__file__).resolve().parents[1]
    wrapper_path = repo_root / "scripts" / "divineos_wrapper.py"
    spec = importlib.util.spec_from_file_location("divineos_wrapper", wrapper_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wrapper = _load_wrapper_module()


class TestFindMarkerDir:
    def test_finds_marker_at_start(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        assert wrapper.find_marker_dir(tmp_path) == tmp_path

    def test_walks_up_to_parent(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        child = tmp_path / "sub" / "nested"
        child.mkdir(parents=True)
        assert wrapper.find_marker_dir(child) == tmp_path

    def test_returns_none_when_no_marker(self, tmp_path):
        # tmp_path has no .envrc anywhere up to root — walk terminates None.
        # Use a nested dir so we exhaust several parents before hitting root.
        child = tmp_path / "a" / "b" / "c"
        child.mkdir(parents=True)
        # If any parent of tmp_path happens to have a .envrc, this test is
        # invalid — but on CI the tmp is under a safe root. Assert defensively.
        result = wrapper.find_marker_dir(child)
        # Result is None OR is some ancestor above tmp_path that happens to
        # have a marker (developer machine edge case). Accept both cleanly.
        if result is not None:
            pytest.skip(
                f"An ancestor of tmp_path has a .envrc marker ({result}); "
                "test only valid on clean filesystems."
            )
        assert result is None


class TestFindSealedCli:
    def test_finds_windows_scripts_cli(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        venv = tmp_path / ".direnv" / "python-3.12.5"
        (venv / "Scripts").mkdir(parents=True)
        cli = venv / "Scripts" / "divineos.exe"
        cli.write_text("stub")
        assert wrapper.find_sealed_cli(tmp_path) == cli

    def test_finds_unix_bin_cli(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        venv = tmp_path / ".direnv" / "python-3.12.5"
        (venv / "bin").mkdir(parents=True)
        cli = venv / "bin" / "divineos"
        cli.write_text("#!/bin/sh")
        assert wrapper.find_sealed_cli(tmp_path) == cli

    def test_returns_none_when_no_direnv(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        # No .direnv/ at all.
        assert wrapper.find_sealed_cli(tmp_path) is None

    def test_returns_none_when_direnv_empty(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        (tmp_path / ".direnv").mkdir()
        # No python-* subdir.
        assert wrapper.find_sealed_cli(tmp_path) is None

    def test_returns_none_when_cli_missing(self, tmp_path):
        (tmp_path / ".envrc").write_text("")
        # python-* dir exists but no Scripts/ or bin/ with the CLI.
        (tmp_path / ".direnv" / "python-3.12").mkdir(parents=True)
        assert wrapper.find_sealed_cli(tmp_path) is None

    def test_picks_first_of_multiple_venvs(self, tmp_path):
        """If multiple python-* dirs exist (upgrade scenario), pick the
        first sorted match — matches Aria's hook `ls -d ... | head -1`."""
        (tmp_path / ".envrc").write_text("")
        for ver in ("python-3.11.0", "python-3.12.5"):
            v = tmp_path / ".direnv" / ver
            (v / "Scripts").mkdir(parents=True)
            (v / "Scripts" / "divineos.exe").write_text("stub")
        found = wrapper.find_sealed_cli(tmp_path)
        assert found is not None
        # sorted() gives 3.11 first alphabetically
        assert "python-3.11.0" in str(found)


class TestFailLoud:
    def test_no_marker_fails_with_helpful_message(self, tmp_path, capsys):
        exit_code = wrapper.fail_loud(None, tmp_path)
        assert exit_code == 2
        captured = capsys.readouterr()
        assert ".envrc" in captured.err
        assert "walked up" in captured.err.lower()
        # Explicitly names why fail-loud instead of fallback
        assert "ping pong" in captured.err.lower() or "ping-pong" in captured.err.lower()

    def test_no_sealed_venv_fails_with_helpful_message(self, tmp_path, capsys):
        exit_code = wrapper.fail_loud(tmp_path, tmp_path / "somewhere")
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "sealed venv" in captured.err.lower()
        assert "pip install" in captured.err.lower()
        assert "git-bash" in captured.err.lower()

    def test_never_returns_zero(self, tmp_path):
        """Fail-loud must exit non-zero — otherwise a caller might treat
        it as success and continue."""
        assert wrapper.fail_loud(None, tmp_path) != 0
        assert wrapper.fail_loud(tmp_path, tmp_path) != 0


class TestMain:
    def test_no_marker_returns_fail_loud_code(self, tmp_path, monkeypatch, capsys):
        # Use a nested tmp so we walk up several dirs before hitting root.
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)
        # Only meaningful if no ancestor has .envrc.
        if wrapper.find_marker_dir(deep) is not None:
            pytest.skip("An ancestor has .envrc — test invalid on this filesystem.")
        exit_code = wrapper.main([])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert ".envrc" in captured.err

    def test_missing_sealed_venv_returns_fail_loud_code(self, tmp_path, monkeypatch, capsys):
        (tmp_path / ".envrc").write_text("")
        # Marker exists; no .direnv/ → sealed CLI missing.
        monkeypatch.chdir(tmp_path)
        exit_code = wrapper.main([])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "sealed venv" in captured.err.lower()

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only subprocess dispatch path")
    def test_dispatches_via_subprocess_on_windows(self, tmp_path, monkeypatch):
        """When a valid sealed CLI exists, main() should invoke it via
        subprocess on Windows and return its exit code."""
        (tmp_path / ".envrc").write_text("")
        venv = tmp_path / ".direnv" / "python-3.12"
        (venv / "Scripts").mkdir(parents=True)
        # Use a real Python one-liner as the "sealed CLI" so we can verify
        # dispatch actually invokes it and returns its exit code.
        cli = venv / "Scripts" / "divineos.exe"
        # Copy the real python.exe so subprocess.run can execute something
        # meaningful. Cheap: symlink or copy the current interpreter.
        import shutil

        shutil.copyfile(sys.executable, cli)
        monkeypatch.chdir(tmp_path)
        # Invoke with `-c 'import sys; sys.exit(7)'` via the shim.
        exit_code = wrapper.main(["-c", "import sys; sys.exit(7)"])
        assert exit_code == 7


class TestF_PipPingPongContract:
    """Contract tests pinning the design intent so a regression fires.

    F3 falsifier: `divineos` from OUTSIDE any checkout MUST fail loud
    rather than fall back to any install. If someone ever changes the
    wrapper to fall back to system install "just in case," these tests
    fail loud and force the conversation.
    """

    def test_wrapper_never_calls_system_install_on_missing_marker(self, tmp_path, monkeypatch):
        """No .envrc anywhere → wrapper must NOT attempt to find a
        system-wide divineos.exe. Contract: fail_loud is the only
        exit path when no marker is found."""
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)
        if wrapper.find_marker_dir(deep) is not None:
            pytest.skip("Ancestor .envrc present — test invalid here.")
        # Monkey-patch fail_loud to a sentinel so we can verify it was
        # called (and no other exit path was reached).
        called = {"count": 0}

        def sentinel_fail(marker, cwd):
            called["count"] += 1
            return 99

        monkeypatch.setattr(wrapper, "fail_loud", sentinel_fail)
        exit_code = wrapper.main([])
        assert called["count"] == 1
        assert exit_code == 99  # returned sentinel, not any dispatch result
