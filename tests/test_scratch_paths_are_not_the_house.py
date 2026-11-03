"""A path outside the repository is not an edit of the house.

The build-flow door fingerprinted any path containing ``/.claude/hooks/`` (and the
hook files by name, ``dads_room_stop.py`` among them) as an edit of the guardrail
layer, even when the file sat in a scratch folder far from the repository. A
throwaway test copy therefore owed a council walk and a game-walk for touching
nothing real. The rule under test: a path that resolves outside the repository
root is not an edit of the house. The controls matter as much as the frees: the
real hooks folder inside the repository must still be gated.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from divineos.core.gravity_classifier import (
    _guardrail_listed_paths,
    score_substrate_modification,
)


@pytest.fixture
def tmp_path():
    """A folder under the OS temp directory, deliberately shadowing pytest's own.

    The suite's conftest points pytest's basetemp INSIDE the repository, so the
    stock ``tmp_path`` is part of the house and would prove nothing here.
    """
    folder = Path(tempfile.mkdtemp(prefix="scratch_outside_the_house_"))
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)  # fail-soft: cleanup of an OS-temp scratch folder only; a leftover temp dir must not fail the test that already passed


def _repo_root() -> Path:
    _, root = _guardrail_listed_paths()
    assert root, "repository root could not be found; the controls below would prove nothing"
    return Path(root)


def _scratch_hooks_file(tmp_path: Path, name: str = "check-council-required.sh") -> Path:
    folder = tmp_path / "scratch_copy" / ".claude" / "hooks"
    folder.mkdir(parents=True)
    target = folder / name
    target.write_text("#!/bin/bash\n", encoding="utf-8")
    return target


def test_scratch_path_containing_claude_hooks_is_free(tmp_path):
    target = _scratch_hooks_file(tmp_path)
    for tool in ("Edit", "Write", "MultiEdit"):
        gravity = score_substrate_modification(tool, (str(target),), "")
        assert gravity.fired_features == (), (tool, gravity)
        assert not gravity.is_council_required


def test_scratch_copy_of_dads_room_stop_is_free(tmp_path):
    target = _scratch_hooks_file(tmp_path, "dads_room_stop.py")
    gravity = score_substrate_modification("Edit", (str(target),), "")
    assert gravity.fired_features == ()
    assert not gravity.is_council_required


def test_scratch_path_containing_src_divineos_is_free(tmp_path):
    folder = tmp_path / "scratch_copy" / "src" / "divineos"
    folder.mkdir(parents=True)
    gravity = score_substrate_modification("Write", (str(folder / "x.py"),), "")
    assert gravity.fired_features == ()


def test_real_claude_hooks_inside_the_repo_is_still_gated():
    """CONTROL: absolute and repo-relative spellings of the real folder both fire."""
    real = _repo_root() / ".claude" / "hooks" / "check-council-required.sh"
    for spelling in (str(real), ".claude/hooks/check-council-required.sh"):
        gravity = score_substrate_modification("Edit", (spelling,), "")
        assert "edit-guardrail" in gravity.fired_features, spelling
        assert gravity.is_council_required, spelling


def test_dotdot_escape_from_the_repo_is_free_but_dotdot_inside_is_gated():
    root = _repo_root()
    escaped = str(root / ".." / "elsewhere" / ".claude" / "hooks" / "x.sh")
    assert score_substrate_modification("Edit", (escaped,), "").fired_features == ()
    inside = str(root / "docs" / ".." / ".claude" / "hooks" / "x.sh")
    assert "edit-guardrail" in score_substrate_modification("Edit", (inside,), "").fired_features


def test_redirect_to_scratch_file_in_compound_command_is_free(tmp_path):
    scratch = tmp_path / "scratch_copy" / ".claude" / "hooks" / "out.txt"
    scratch.parent.mkdir(parents=True)
    command = f"echo one > {scratch} && echo two"
    gravity = score_substrate_modification("Bash", (), command)
    assert gravity.fired_features == (), gravity
    assert not gravity.is_council_required


def test_redirect_into_the_real_hooks_folder_in_compound_command_is_still_gated():
    """CONTROL: the same compound shape aimed at the real folder still fires."""
    real = _repo_root() / ".claude" / "hooks" / "out.sh"
    command = f"echo one > {real} && echo two"
    gravity = score_substrate_modification("Bash", (), command)
    assert "edit-guardrail" in gravity.fired_features
    assert gravity.is_council_required


def test_mixed_compound_with_one_real_target_is_still_gated(tmp_path):
    """CONTROL: one scratch redirect must not launder a real one beside it."""
    scratch = tmp_path / "scratch_copy" / ".claude" / "hooks" / "out.txt"
    scratch.parent.mkdir(parents=True)
    real = _repo_root() / ".claude" / "hooks" / "out.sh"
    command = f"echo one > {scratch} && echo two > {real}"
    gravity = score_substrate_modification("Bash", (), command)
    assert "edit-guardrail" in gravity.fired_features


def test_linked_worktree_of_this_repo_outside_the_root_is_still_gated(tmp_path):
    """CONTROL: a linked git worktree of THIS repository is the house at another address.

    A linked worktree's ``.git`` is a file pointing back into this repository's
    ``.git/worktrees/``. Edits there are real edits of the house even though the
    folder sits outside the root, so the scratch rule must not free them.
    """
    root = _repo_root()
    worktree = tmp_path / "linked_work_copy"
    (worktree / ".claude" / "hooks").mkdir(parents=True)
    (worktree / ".git").write_text(f"gitdir: {root}/.git/worktrees/linked_work_copy\n")
    gravity = score_substrate_modification(
        "Edit", (str(worktree / ".claude" / "hooks" / "x.sh"),), ""
    )
    assert "edit-guardrail" in gravity.fired_features


def test_unrelated_git_clone_outside_the_root_is_free(tmp_path):
    """A separate clone is somebody's scratch copy, not this house."""
    clone = tmp_path / "throwaway_clone"
    (clone / ".claude" / "hooks").mkdir(parents=True)
    (clone / ".git").mkdir()
    gravity = score_substrate_modification("Edit", (str(clone / ".claude" / "hooks" / "x.sh"),), "")
    assert gravity.fired_features == ()
