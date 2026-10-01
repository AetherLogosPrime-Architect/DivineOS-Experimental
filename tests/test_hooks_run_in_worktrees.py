"""Git hooks must run in a worktree, not only in the main checkout.

setup/setup-hooks.sh used to set core.hooksPath to the relative ".git/hooks".
That setting lives in the config every worktree shares, and in a worktree
".git" is a file, so the path pointed at nothing and no hook ran -- pre-commit,
commit-msg, pre-push. Found 2026-09-23 when a push from a worktree showed no
test run. Andrew said yes to removing it from the live config the same day.

The existing setup tests check WHAT the installer writes. None checked WHERE
git looks for it from a worktree, which is the half that was broken.

Runs the real installer in a scratch repo, then asks git from inside a worktree
where its hooks are.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "init")
    return repo


def _install(repo: Path) -> None:
    subprocess.run(
        [BASH, str(REPO / "setup" / "setup-hooks.sh")],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )


def _hook_from_worktree(repo: Path, tmp: Path, name: str) -> Path:
    wt = tmp / "wt"
    # Detached: several worktrees per test would otherwise all try to create
    # a branch named after the same folder, "wt".
    _git(repo, "worktree", "add", "-q", "--detach", str(wt))
    found = _git(wt, "rev-parse", "--git-path", f"hooks/{name}")
    path = Path(found)
    return path if path.is_absolute() else wt / path


def _hooks_path(repo: Path) -> str:
    return _git(repo, "config", "--default", "", "--get", "core.hooksPath")


@pytest.mark.skipif(BASH is None, reason="needs bash to run the installer")
def test_a_worktree_finds_the_installed_hooks(scratch: Path, tmp_path: Path) -> None:
    _install(scratch)
    assert _hooks_path(scratch) == ""
    for name in ("pre-commit", "commit-msg", "pre-push"):
        assert _hook_from_worktree(scratch, tmp_path / name, name).is_file(), name


@pytest.mark.skipif(BASH is None, reason="needs bash to run the installer")
def test_the_installer_clears_the_setting_an_old_run_left(scratch: Path, tmp_path: Path) -> None:
    _git(scratch, "config", "core.hooksPath", ".git/hooks")
    _install(scratch)
    assert _hooks_path(scratch) == ""
    assert _hook_from_worktree(scratch, tmp_path, "pre-push").is_file()


def test_neither_installer_sets_a_hooks_path() -> None:
    for script in ("setup-hooks.sh", "setup-hooks.ps1"):
        text = (REPO / "setup" / script).read_text(encoding="utf-8")
        setting = [
            ln
            for ln in text.splitlines()
            if "config core.hooksPath" in ln
            and "--unset" not in ln
            and not ln.lstrip().startswith("#")
        ]
        assert not setting, f"{script} sets core.hooksPath again: {setting}"
