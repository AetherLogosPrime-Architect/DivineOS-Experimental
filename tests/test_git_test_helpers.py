"""Tests for the Windows-MSYS2-race git-init helper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from _git_test_helpers import (
    _DLL_INIT_FAILED_CODES,
    materialize_repo_from_template,
    safe_git_init,
)


def test_safe_git_init_succeeds_on_clean_run(tmp_path):
    repo = tmp_path / "fresh"
    safe_git_init(repo, "--initial-branch=main")
    assert (repo / ".git").is_dir()


def test_safe_git_init_creates_bare_when_asked(tmp_path):
    bare = tmp_path / "bare"
    safe_git_init(bare, "--bare", "--initial-branch=main")
    # Bare repos have HEAD at the top, not under .git/
    assert (bare / "HEAD").is_file()


def test_safe_git_init_retries_on_dll_init_failed(tmp_path):
    repo = tmp_path / "race"
    calls = {"n": 0}

    real_run = subprocess.run

    def flaky_run(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise subprocess.CalledProcessError(
                returncode=next(iter(_DLL_INIT_FAILED_CODES)),
                cmd=args[0],
                stderr="STATUS_DLL_INIT_FAILED",
            )
        return real_run(*args, **kwargs)

    with patch("_git_test_helpers.subprocess.run", side_effect=flaky_run):
        safe_git_init(repo, "--initial-branch=main", sleep_s=0)

    assert calls["n"] == 3
    assert (repo / ".git").is_dir()


def test_safe_git_init_does_not_retry_other_errors(tmp_path):
    repo = tmp_path / "real_error"

    def always_fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=args[0],
            stderr="fatal: not a real error code we retry",
        )

    with patch("_git_test_helpers.subprocess.run", side_effect=always_fail):
        with pytest.raises(subprocess.CalledProcessError) as exc:
            safe_git_init(repo, "--initial-branch=main", sleep_s=0)

    assert exc.value.returncode == 128


def test_safe_git_init_gives_up_after_retries(tmp_path):
    repo = tmp_path / "stuck"

    def always_dll_fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=3221225794,
            cmd=args[0],
            stderr="STATUS_DLL_INIT_FAILED",
        )

    with patch("_git_test_helpers.subprocess.run", side_effect=always_dll_fail):
        with pytest.raises(subprocess.CalledProcessError) as exc:
            safe_git_init(repo, "--initial-branch=main", retries=2, sleep_s=0)

    assert exc.value.returncode == 3221225794


def test_materialize_copies_template(tmp_path):
    template = tmp_path / "template"
    safe_git_init(template, "--initial-branch=main")
    (template / "marker.txt").write_text("from-template", encoding="utf-8")

    target = tmp_path / "copy"
    materialize_repo_from_template(template, target)
    assert (target / ".git").is_dir()
    assert (target / "marker.txt").read_text(encoding="utf-8") == "from-template"


def test_template_repo_fixture_provides_working_git_dir(git_template_repo):
    """The session-scoped fixture should yield a real .git directory."""
    assert (Path(git_template_repo) / ".git").is_dir()


def test_template_bare_repo_fixture_provides_bare_dir(git_template_bare_repo):
    """The bare-repo fixture should yield a bare repo (HEAD at top)."""
    assert (Path(git_template_bare_repo) / "HEAD").is_file()
