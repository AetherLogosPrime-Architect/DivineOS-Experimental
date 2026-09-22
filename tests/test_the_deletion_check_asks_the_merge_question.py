"""The push gate's deletion count, measured against the right population.

The check calls its own number "file(s) would be deleted by merge", which is
the merge question. It asked that question with a two-dot diff, which answers
a different one: what differs between these two trees. A file main gained
AFTER the branch diverged is present on one side and absent on the other, so
that form reports it as a deletion. The merge keeps it. The branch never
touched it.

It fired on a branch that deletes nothing, named thirteen files, and blocked
the push. What makes it worth a test rather than a one-line fix: this
repository already BLOCKS me from typing that diff form by hand, and the
refusal carries the incident where it cost a false alarm. The forbidden
instrument was sitting inside the automated check the whole time. A defect
caught at the keyboard and left in the code keeps firing.

The control is the load-bearing half. A real deletion must still be counted,
or the fix would be indistinguishable from deleting the check.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.core.branch_health import check_deletion_shape


def _git(repo, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=180)
    assert done.returncode == 0, f"git {args[0]} failed: {done.stderr[:300]}"
    return done.stdout


def _a_repo_where_main_moved_on(tmp_path):
    """Main gains a file after the branch diverges. The branch removes nothing.

    This is the ordinary shape of every branch that is a few commits behind,
    which is why the false alarm was not rare.
    """
    repo = tmp_path / "checkout"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")

    (repo / "shared.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")

    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "mine.txt").write_text("branch work\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add my own file, remove nothing")

    _git(repo, "checkout", "-q", "main")
    for n in range(12):
        (repo / f"main_gained_{n}.txt").write_text("later\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "main moves on")
    # The check compares against a remote-tracking name, so give it one that
    # points at this main rather than reaching for a network.
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    _git(repo, "checkout", "-q", "feature")
    return repo


def test_a_branch_that_deletes_nothing_is_reported_as_deleting_nothing(tmp_path):
    repo = _a_repo_where_main_moved_on(tmp_path)

    finding = check_deletion_shape(base="origin/main", cwd=str(repo), threshold=10)

    assert finding.details.get("deletion_count") == 0, finding.message
    assert finding.severity == "ok", finding.message


def test_a_real_deletion_is_still_counted(tmp_path):
    """The control. Without it, the fix above is indistinguishable from
    silencing the check -- both make the alarm stop."""
    repo = _a_repo_where_main_moved_on(tmp_path)
    (repo / "shared.txt").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "genuinely remove a file the base had")

    finding = check_deletion_shape(base="origin/main", cwd=str(repo), threshold=10)

    assert finding.details.get("deletion_count") == 1, finding.message
    assert finding.details.get("files") == ["shared.txt"], finding.details


def test_an_unresolvable_base_says_it_did_not_run(tmp_path):
    """Could-not-look must not arrive wearing the same face as found-nothing.

    The three states -- no deletions, deletions found, could not compute --
    share one output field, and only the severity and the wording keep them
    apart. This pins the third one.
    """
    repo = tmp_path / "solo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    (repo / "only.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")

    finding = check_deletion_shape(base="origin/nonexistent", cwd=str(repo), threshold=10)

    assert finding.severity != "ok"
    assert "did NOT run" in finding.message
    assert "deletion_count" not in (finding.details or {})


@pytest.mark.parametrize("threshold", [1, 5])
def test_the_threshold_still_decides_severity(tmp_path, threshold):
    """The counting change must not quietly move where the alarm sits."""
    repo = _a_repo_where_main_moved_on(tmp_path)
    for n in range(6):
        path = repo / f"doomed_{n}.txt"
        path.write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add files that will be removed")
    for n in range(6):
        (repo / f"doomed_{n}.txt").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "remove them again")

    finding = check_deletion_shape(base="origin/main", cwd=str(repo), threshold=threshold)

    # Added and removed on the same branch: the merge base never had them, so
    # a merge deletes nothing, and no threshold should turn that into an alarm.
    assert finding.details.get("deletion_count") == 0, finding.message
    assert finding.severity == "ok", finding.message
