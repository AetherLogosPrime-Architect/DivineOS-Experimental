"""A path deleted on the branch can still be sitting on disk, unique.

2026-09-16, second defect in this scan found the same day as the first, and
this one nearly cost eleven files.

``only_here`` asks git for the branch's blob at each path and, when git says
there is none, skips the path with the comment "Deleted on this branch.
Nothing here for a rebuild to take." Its docstring states the same premise
outright: *a path deleted on this branch has no content here to lose and is
skipped.*

The premise is false whenever a commit removed the file from the index and
left it in the working tree — which is exactly what an untrack-this-from-the
-code-branch commit does. The file is gone from the branch and present on
disk, and the copy on disk can be the only one of its version anywhere.

WHAT IT COST. A push refusal named eleven archive exports. Every one of them
had been untracked by a commit on the branch and every one was still on disk,
regenerated and newer than the copies on main. The scan skipped all eleven as
"nothing to lose", found no at-risk paths among what remained, and printed
*every one of these exists on another ref at the same bytes; none are unique
here.* Acting on that sentence — rebuilding the branch against main, which is
what the refusal instructs — would have replaced eleven current files with
older versions, silently, with nothing anywhere saying so.

TWO FAULTS, and the second is the one that makes the first dangerous:

1. Content present only in the working tree is invisible to the scan.
2. The reassurance is printed over a set the scan silently narrowed. A
   universal claim is made about a population the reader does not know was
   filtered.

So these tests pin both: the at-risk file must be FOUND, and the all-clear
must never be printed over a set that had paths removed from it without
saying so.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCOPE = _PROJECT_ROOT / "scripts" / "check_branch_scope.py"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "scripts").mkdir()
    shutil.copy2(_SCOPE, root / "scripts" / _SCOPE.name)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")

    # A substrate file that exists on main with OLD content. This is the
    # copy a rebuild would fall back to, and the reason the loss is silent:
    # the path still exists afterwards, holding a stale version.
    old = root / "dreams" / "aether" / "regenerated.md"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text("the old version, already on main\n", encoding="utf-8")

    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    return root


def _branch_that_untracked_a_regenerated_file(repo: Path) -> str:
    """Reproduce the real shape: the file is regenerated with new content,
    swept into a commit, then untracked by a later commit that leaves it on
    disk. Returns the branch's commit id — the identifier the push gate
    actually passes."""
    _git(repo, "checkout", "-q", "-B", "work")
    target = repo / "dreams" / "aether" / "regenerated.md"

    target.write_text("the CURRENT version, exists nowhere else\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "auto-commit: swept the regenerated file in")

    # Untrack it, leaving the working-tree copy in place. This is the commit
    # whose message reads like a cleanup and whose effect is a deletion.
    _git(repo, "rm", "-q", "--cached", "dreams/aether/regenerated.md")
    _git(repo, "commit", "-q", "-m", "take the substrate mirror off the code branch")

    assert target.exists(), "fixture is wrong: the file should still be on disk"
    return _git(repo, "rev-parse", "HEAD")


def _run_scope(repo: Path, rev: str) -> str:
    result = subprocess.run(
        [sys.executable, "scripts/check_branch_scope.py", rev, "--list"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def test_the_fixture_actually_reproduces_the_shape(repo: Path):
    """Control. If the file were not on disk, or not unique, the tests below
    would pass for the wrong reason — a scan that finds nothing because there
    is nothing to find looks identical to one that cannot see."""
    _branch_that_untracked_a_regenerated_file(repo)
    target = repo / "dreams" / "aether" / "regenerated.md"

    assert target.exists()
    assert "CURRENT" in target.read_text(encoding="utf-8")
    on_main = _git(repo, "show", "origin/main:dreams/aether/regenerated.md")
    assert "CURRENT" not in on_main, "main must hold only the older version"


def test_a_file_deleted_on_the_branch_but_present_on_disk_is_reported_at_risk(
    repo: Path,
):
    """The real case. The only current copy lives in the working tree, and the
    instruction the refusal gives would overwrite it with main's older one."""
    rev = _branch_that_untracked_a_regenerated_file(repo)

    out = _run_scope(repo, rev)

    assert "regenerated.md" in out, (
        "The scan did not mention a file whose only current copy is in the "
        "working tree. Deleted-on-the-branch is not the same as nothing-to-"
        "lose, and rebuilding would replace it with an older version.\n" + out
    )


def test_the_all_clear_is_never_printed_over_a_silently_narrowed_set(repo: Path):
    """The fault that made the first one dangerous. Skipping paths is fine;
    printing a universal all-clear about the survivors without saying paths
    were skipped is what turns a partial look into a clean bill of health."""
    rev = _branch_that_untracked_a_regenerated_file(repo)

    out = _run_scope(repo, rev)

    assert "none are unique here" not in out, (
        "The scan printed its all-clear while at least one path had been "
        "dropped from the comparison. A claim about every one of these must "
        "not be made about a set the reader does not know was filtered.\n" + out
    )
