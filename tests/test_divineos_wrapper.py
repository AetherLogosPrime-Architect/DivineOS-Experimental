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


class TestWorktreeWalkUp:
    """The case that locked Aether out of his own shell, 2026-08-06.

    A git worktree carries a stray empty `.envrc` and never carries a venv --
    untracked directories do not travel with it. The walk used to stop at the
    first marker, so it refused at the worktree while the enclosing clone's
    sealed venv sat one directory up.

    What that cost: the engagement gate blocks Bash until a thinking command
    runs, and prints `divineos ask / recall / context` as the remedy. The shim
    refused that exact command. He routed git through PowerShell to escape a
    gate whose prescribed remedy was unreachable, and reported it rather than
    loosening the guard.
    """

    def _fake_venv(self, root):
        scripts = root / ".venv" / "Scripts"
        scripts.mkdir(parents=True)
        cli = scripts / "divineos.exe"
        cli.write_text("")
        binv = root / ".venv" / "bin"
        binv.mkdir(parents=True, exist_ok=True)
        (binv / "divineos").write_text("")
        return cli

    def test_walks_past_a_markered_worktree_to_the_clone_venv(self, tmp_path):
        clone = tmp_path / "clone"
        worktree = clone / ".claude" / "worktrees" / "wt"
        worktree.mkdir(parents=True)
        (clone / ".envrc").write_text("")
        (worktree / ".envrc").write_text("")
        self._fake_venv(clone)

        # The nearest marker is the worktree and it cannot satisfy the request.
        assert wrapper.find_sealed_cli(worktree) is None
        # The walk must not stop there.
        found = wrapper.find_marker_dirs(worktree)
        assert found[0] == worktree
        assert clone in found
        assert wrapper.find_sealed_cli(clone) is not None

    def test_nearest_marker_still_wins_when_it_has_a_venv(self, tmp_path):
        """Precedence unchanged: a workspace with its own venv uses its own."""
        clone = tmp_path / "clone"
        inner = clone / "inner"
        inner.mkdir(parents=True)
        (clone / ".envrc").write_text("")
        (inner / ".envrc").write_text("")
        self._fake_venv(clone)
        inner_cli = self._fake_venv(inner)

        found = wrapper.find_marker_dirs(inner)
        first_with_venv = next(d for d in found if wrapper.find_sealed_cli(d))
        assert first_with_venv == inner
        assert wrapper.find_sealed_cli(inner) == inner_cli

    def test_no_venv_anywhere_still_refuses(self, tmp_path):
        """The seal holds. Walking up is not falling back to system-wide."""
        clone = tmp_path / "clone"
        worktree = clone / "wt"
        worktree.mkdir(parents=True)
        (clone / ".envrc").write_text("")
        (worktree / ".envrc").write_text("")
        for d in wrapper.find_marker_dirs(worktree):
            if d in (clone, worktree):
                assert wrapper.find_sealed_cli(d) is None


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

    def test_missing_sealed_venv_returns_fail_loud_code(self, tmp_path, monkeypatch):
        """Marker present, no sealed venv anywhere up the chain -> refuse.

        Rewritten 2026-08-06 (Aria) alongside the walk-up change. Two moves:

        1. The premise is now explicit. The walk no longer stops at the first
           marker, so "no sealed CLI here" is not enough -- the test must
           establish that no ancestor can satisfy it either, the same way
           test_no_marker_returns_fail_loud_code already guards its own.

        2. It asserts the CONTRACT rather than captured stderr. capsys does
           not reliably capture in this file's harness; a debug print placed
           directly in the test body also came back empty, so an output
           assertion here fails for reasons unrelated to behaviour.
           fail_loud's message is covered by TestFailLoud above; what belongs
           here is that main REFUSES.
        """
        (tmp_path / ".envrc").write_text("")
        monkeypatch.chdir(tmp_path)

        for ancestor in wrapper.find_marker_dirs(tmp_path):
            if wrapper.find_sealed_cli(ancestor) is not None:
                pytest.skip(f"{ancestor} has a real sealed venv -- premise invalid here.")

        assert wrapper.find_sealed_cli(tmp_path) is None
        assert wrapper.main([]) == 2

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
        # A venv interpreter is a LAUNCHER, not a standalone binary: copied on
        # its own it aborts with "failed to locate pyvenv.cfg" and exit 106, so
        # the assertion below read 106 == 7 and the failure looked like a
        # dispatch bug rather than a missing file. Whether it passed depended
        # entirely on which interpreter happened to be running pytest — system
        # python copies fine, the project's own venv does not, which is why this
        # was red under precommit and green for whoever last looked.
        # base_prefix is the real install under a venv and equals prefix
        # outside one, so this line is correct either way.
        (venv / "pyvenv.cfg").write_text("home = " + sys.base_prefix + "\n", encoding="utf-8")
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
