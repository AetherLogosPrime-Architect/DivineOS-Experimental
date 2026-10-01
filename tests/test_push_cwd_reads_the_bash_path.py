"""The push check reads the worktree a push names, in either path form.

Aria, 2026-09-23: a push written ``cd /c/w507 && git push`` was refused as "12
behind main" when w507 was 0 behind. The hook's Windows Python read ``/c/w507``
as ``C:\\c\\w507``, found no .git there, and fell back to the session folder --
which was the one 12 behind. Pushing again with ``cd "C:/w507"`` went through.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from divineos.core.push_detection import push_cwd, windows_path_from_git_bash


class TestTheTranslation:
    def test_a_drive_path_becomes_a_windows_path(self):
        assert windows_path_from_git_bash("/c/w507") == "C:/w507"
        assert windows_path_from_git_bash("/c/DIVINE OS/repo") == "C:/DIVINE OS/repo"
        assert windows_path_from_git_bash("/d") == "D:/"

    def test_anything_else_comes_back_unchanged(self):
        for path in ("C:/w507", "relative/dir", "/usr/local", "/cd/x", ""):
            assert windows_path_from_git_bash(path) == path


def _worktree(tmp_path: Path) -> Path:
    tree = tmp_path / "w507"
    (tree / ".git").mkdir(parents=True)
    return tree


class TestPushCwd:
    def test_a_native_path_to_a_worktree_is_returned(self, tmp_path):
        tree = _worktree(tmp_path)
        assert push_cwd(f'cd "{tree}" && git push origin x') == str(tree)

    def test_a_folder_that_is_not_a_worktree_gives_none(self, tmp_path):
        assert push_cwd(f'cd "{tmp_path}" && git push') is None

    def test_no_leading_cd_gives_none(self):
        assert push_cwd("git push origin main") is None

    @pytest.mark.skipif(os.name != "nt", reason="the Git-Bash drive form only exists on Windows")
    def test_the_git_bash_form_finds_the_same_worktree(self, tmp_path):
        tree = _worktree(tmp_path)
        native = str(tree).replace("\\", "/")
        drive, rest = native.split(":", 1)
        bash_form = f"/{drive.lower()}{rest}"
        found = push_cwd(f'cd "{bash_form}" && git push origin x')
        assert found is not None, f"{bash_form} was not recognised as the worktree at {tree}"
        assert Path(found) == tree

    def test_without_translation_the_bash_form_is_missed(self, tmp_path):
        """The control: the failure Aria hit, reproduced by switching translation off."""
        tree = _worktree(tmp_path)
        native = str(tree).replace("\\", "/")
        if ":" not in native:
            pytest.skip("no drive letter on this platform")
        drive, rest = native.split(":", 1)
        assert push_cwd(f'cd "/{drive.lower()}{rest}" && git push', windows=False) is None
