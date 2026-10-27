"""The push check lists the files THIS BRANCH adds, not every file main changed.

2026-10-27, Dad: "every push fails three times and takes 30 mins per push." For a branch already on
GitHub the push check diffed the old remote tip against the new head, so folding main in made every
file main changed look pushed. Measured on a real push: 78 files transferred, 3 the branch's own, 1
new to GitHub. Those 78 went to the draft test picker, which named test files for all of them.

A real temp repository with a real bare remote; the real function is cut out of the real script.
"""

import os
import subprocess
from pathlib import Path

import pytest

# a bash proven to run a script, not the WSL relay that shutil.which can return
from tests.test_a_merge_cannot_commit_past_its_own_tests import BASH

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_push_readiness.sh"
GIT_STATE = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash to run the push check")


def _env(**extra):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        **extra,
    }
    for k in GIT_STATE:
        env.pop(k, None)
    return env


def _git(cwd, *args):
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=_env(), capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, f"git {' '.join(args)}: {done.stderr}"
    return done.stdout.strip()


def _commit(repo, name, text="x\n"):
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", f"add {name}")


def _function_text():
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("_collect_changed_files() {"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    return "\n".join(lines[start : end + 1])


def _collect(repo, local_sha, remote_sha):
    stdin = f"refs/heads/feature {local_sha} refs/heads/feature {remote_sha}"
    program = f"{_function_text()}\nHOOK_STDIN='{stdin}'\n_collect_changed_files"
    done = subprocess.run(
        [BASH, "-c", program], cwd=repo, env=_env(), capture_output=True, text=True, check=False
    )
    return sorted(done.stdout.split()), done.stderr


@pytest.fixture
def fold(tmp_path):
    """A branch pushed once, main moved on by two files, then main folded in and one own file added."""
    bare = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(bare), str(work))
    _git(work, "checkout", "-q", "-b", "main")
    _commit(work, "base.txt")
    _git(work, "push", "-q", "origin", "main")
    _git(work, "checkout", "-q", "-b", "feature")
    _commit(work, "own_first.txt")
    _git(work, "push", "-q", "origin", "feature")
    remote_tip = _git(work, "rev-parse", "HEAD")
    _git(work, "checkout", "-q", "main")
    _commit(work, "main_only_a.txt")
    _commit(work, "main_only_b.txt")
    _git(work, "push", "-q", "origin", "main")
    _git(work, "checkout", "-q", "feature")
    _git(work, "merge", "-q", "--no-edit", "origin/main")
    return work, remote_tip


def test_folding_main_in_does_not_make_main_files_look_pushed(fold):
    work, remote_tip = fold
    _commit(work, "own_second.txt")
    files, err = _collect(work, _git(work, "rev-parse", "HEAD"), remote_tip)
    assert files == ["own_second.txt"], (files, err)
    assert "3 file(s) in this push, 1 this branch's own" in err, err


def test_a_pure_fold_with_nothing_new_of_mine_falls_back_to_the_branchs_own_files(fold):
    """Never an empty list: an empty list is read downstream as 'could not tell'."""
    work, remote_tip = fold
    files, err = _collect(work, _git(work, "rev-parse", "HEAD"), remote_tip)
    assert files == ["own_first.txt"], (files, err)


def test_when_main_cannot_be_found_it_keeps_the_whole_transferred_list(fold):
    work, remote_tip = fold
    _commit(work, "own_second.txt")
    _git(work, "update-ref", "-d", "refs/remotes/origin/main")
    files, err = _collect(work, _git(work, "rev-parse", "HEAD"), remote_tip)
    assert files == ["main_only_a.txt", "main_only_b.txt", "own_second.txt"], (files, err)


def test_a_new_branch_still_diffs_against_main(fold):
    work, _remote_tip = fold
    _commit(work, "own_second.txt")
    files, err = _collect(work, _git(work, "rev-parse", "HEAD"), "0" * 40)
    assert files == ["own_first.txt", "own_second.txt"], (files, err)
