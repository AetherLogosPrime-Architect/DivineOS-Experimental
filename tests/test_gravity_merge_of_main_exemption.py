"""A commit that only seals a merge of origin/main owes no council walk.

Real git in a temp repo, no mocks: the exemption reads git state, so the
tests build that state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.gravity_classifier import (
    _concludes_clean_merge_of_main,
    score_substrate_modification,
)


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def repo_behind_main(tmp_path, monkeypatch):
    """A clone whose branch is one commit behind origin/main, merge not yet started."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", str(origin), str(work)], check=True, capture_output=True)
    for key, val in (("user.name", "t"), ("user.email", "t@t")):
        _git(work, "config", key, val)
    (work / "a.txt").write_text("a\n")
    _git(work, "add", "a.txt")
    _git(work, "commit", "-m", "base")
    _git(work, "push", "origin", "main")
    _git(work, "checkout", "-b", "mine")
    (work / "mine.txt").write_text("mine\n")
    _git(work, "add", "mine.txt")
    _git(work, "commit", "-m", "my own work")
    _git(work, "checkout", "main")
    (work / "from_main.txt").write_text("main\n")
    _git(work, "add", "from_main.txt")
    _git(work, "commit", "-m", "main moves")
    _git(work, "push", "origin", "main")
    _git(work, "checkout", "mine")
    monkeypatch.chdir(work)
    return work


def _start_merge(work: Path) -> None:
    _git(work, "merge", "--no-commit", "--no-ff", "origin/main")


COMMIT = "git commit --no-edit"


def test_clean_merge_of_main_is_exempt(repo_behind_main):
    _start_merge(repo_behind_main)
    assert _concludes_clean_merge_of_main(COMMIT)
    assert "git-commit" not in score_substrate_modification("Bash", (), COMMIT).fired_features


def test_message_form_is_exempt(repo_behind_main):
    _start_merge(repo_behind_main)
    assert _concludes_clean_merge_of_main('git commit -m "Merge main into mine"')


def test_no_merge_in_progress_is_not_exempt(repo_behind_main):
    assert not _concludes_clean_merge_of_main(COMMIT)
    assert "git-commit" in score_substrate_modification("Bash", (), COMMIT).fired_features


def test_extra_staged_file_of_mine_is_not_exempt(repo_behind_main):
    _start_merge(repo_behind_main)
    (repo_behind_main / "smuggled.txt").write_text("not from main\n")
    _git(repo_behind_main, "add", "smuggled.txt")
    assert not _concludes_clean_merge_of_main(COMMIT)


def test_all_flag_is_not_exempt(repo_behind_main):
    _start_merge(repo_behind_main)
    assert not _concludes_clean_merge_of_main("git commit -a --no-edit")


def test_merged_commit_not_on_main_is_not_exempt(repo_behind_main):
    work = repo_behind_main
    _git(work, "checkout", "-b", "other", "main")
    (work / "other.txt").write_text("unreviewed\n")
    _git(work, "add", "other.txt")
    _git(work, "commit", "-m", "never reached main")
    _git(work, "checkout", "mine")
    _git(work, "merge", "--no-commit", "--no-ff", "other")
    assert not _concludes_clean_merge_of_main(COMMIT)


def test_unparseable_command_is_not_exempt(repo_behind_main):
    _start_merge(repo_behind_main)
    assert not _concludes_clean_merge_of_main('git commit -m "unbalanced')


def test_a_chained_pipe_and_follow_up_command_do_not_hide_the_exemption(repo_behind_main):
    _start_merge(repo_behind_main)
    chained = "set -o pipefail && git commit --no-edit 2>&1 | tail -4; git rev-list --count HEAD"
    assert _concludes_clean_merge_of_main(chained)


def test_a_chained_commit_with_a_stray_flag_is_still_not_exempt(repo_behind_main):
    _start_merge(repo_behind_main)
    assert not _concludes_clean_merge_of_main("git status && git commit -a --no-edit | tail -1")
