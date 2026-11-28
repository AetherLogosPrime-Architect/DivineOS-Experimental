"""A one-commit checkout makes git report every file as just added.

CI's test job checks out a single commit, so `git log --diff-filter=A` listed the whole
repo (980 files) as "recently added" and the probe scanned all of them instead of the ~20
that are really recent. It passed in two seconds locally and brushed the 30-second limit
on GitHub's machines, turning main red after merges. History that was never fetched cannot
say what is recent, so on a shallow repo the answer is "unknown", and the function's own
docstring promises to stay quiet there.
"""

import subprocess
from pathlib import Path

from divineos.core.completion_check import _recently_added_files

_ID = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo_with_two_commits(tmp_path: Path) -> Path:
    repo = tmp_path / "full"
    (repo / "src" / "divineos" / "core").mkdir(parents=True)
    (repo / "src" / "divineos" / "core" / "old_one.py").write_text("x = 1\n")
    _git(repo, "init", "-q")
    _git(repo, *_ID, "add", "-A")
    _git(repo, *_ID, "commit", "-q", "-m", "first")
    (repo / "src" / "divineos" / "core" / "new_one.py").write_text("y = 2\n")
    _git(repo, *_ID, "add", "-A")
    _git(repo, *_ID, "commit", "-q", "-m", "second")
    return repo


def test_a_full_clone_lists_what_was_added_recently(tmp_path):
    repo = _repo_with_two_commits(tmp_path)
    found = _recently_added_files(14, repo)
    assert "src/divineos/core/new_one.py" in found
    assert "src/divineos/core/old_one.py" in found  # control: the probe can find real cases


def test_a_one_commit_clone_says_nothing_instead_of_listing_the_whole_repo(tmp_path):
    repo = _repo_with_two_commits(tmp_path)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", repo.as_uri(), str(shallow)],
        check=True,
        capture_output=True,
    )
    # the control above shows these files DO list on a full clone; here git would also
    # list both (the single commit looks like a root commit that added everything)
    assert _recently_added_files(14, shallow) == []
