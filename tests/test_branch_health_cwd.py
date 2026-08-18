"""branch-health must measure the tree being pushed, not the ambient one.

The check is fired by a PreToolUse(Bash) hook that cd's to the ambient repo
root. When the push it polices targets a different worktree, it measured the
wrong HEAD: on 2026-08-15 it reported "25 file(s) would be deleted by merge"
against a push whose own branch deleted nothing, having read the main
checkout's branch instead of the worktree being pushed from.

Both numbers were correct about different trees, which is the worst kind of
wrong — it reads as a real finding, and the only way past it is a kill-switch
that disables the gate for EVERY later push, not just the misfiring one. A
gate that cries wolf spends its own authority; that is the bypass-groove shape
Aletheia named, where the gate trains the bypass.

The load-bearing property is therefore TWO-SIDED, and both sides are tested
here: pointing the check at the right tree must silence the false alarm AND
must leave a genuine mass-deletion still caught.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.core.branch_health import check_all, check_deletion_shape


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


@pytest.fixture
def repo(tmp_path):
    """A repo whose main branch holds files a second branch deletes."""
    r = tmp_path / "repo"
    r.mkdir()
    _git("init", "-q", "-b", "main", cwd=r)
    _git("config", "user.email", "t@t", cwd=r)
    _git("config", "user.name", "t", cwd=r)

    for i in range(12):
        (r / f"keep_{i}.txt").write_text("x", encoding="utf-8")
    _git("add", "-A", cwd=r)
    _git("commit", "-qm", "base", cwd=r)

    # Stand in for origin/main so the checks have a base to compare against.
    _git("branch", "origin-main", cwd=r)

    _git("checkout", "-q", "-b", "deleter", cwd=r)
    for i in range(12):
        (r / f"keep_{i}.txt").unlink()
    _git("add", "-A", cwd=r)
    _git("commit", "-qm", "delete everything", cwd=r)
    return r


def test_deletion_shape_sees_the_tree_it_is_pointed_at(repo):
    """The real catch must survive: 12 deletions, threshold 10, warns."""
    finding = check_deletion_shape(base="origin-main", cwd=str(repo), threshold=10)
    assert finding.severity in ("warn", "critical")
    assert "12" in finding.message


def test_a_branch_that_deletes_nothing_is_not_flagged(repo):
    """The false alarm must die: same repo, a branch with no deletions."""
    _git("checkout", "-q", "main", cwd=repo)
    _git("checkout", "-q", "-b", "adder", cwd=repo)
    (repo / "new.txt").write_text("y", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "add one", cwd=repo)

    finding = check_deletion_shape(base="origin-main", cwd=str(repo), threshold=10)
    assert finding.severity == "ok", finding.message


def test_cwd_decides_which_answer_you_get(repo, tmp_path):
    """The bug, pinned: the same call against a different tree must differ.

    This is the property the 2026-08-15 misfire violated — the check answered
    about whichever tree it happened to be standing in, and the caller had no
    way to say which one it meant.
    """
    other = tmp_path / "quiet"
    other.mkdir()
    _git("init", "-q", "-b", "main", cwd=other)
    _git("config", "user.email", "t@t", cwd=other)
    _git("config", "user.name", "t", cwd=other)
    (other / "a.txt").write_text("a", encoding="utf-8")
    _git("add", "-A", cwd=other)
    _git("commit", "-qm", "base", cwd=other)
    _git("branch", "origin-main", cwd=other)

    deleting = check_deletion_shape(base="origin-main", cwd=str(repo), threshold=10)
    quiet = check_deletion_shape(base="origin-main", cwd=str(other), threshold=10)

    assert deleting.severity in ("warn", "critical")
    assert quiet.severity == "ok"


def test_check_all_threads_cwd_to_both_checks(repo):
    """check_all already accepted cwd; the CLI is what lacked the option."""
    findings = check_all(base="origin-main", cwd=str(repo), fetch=False, deletion_threshold=10)
    names = {f.name for f in findings}
    assert names == {"base_freshness", "deletion_shape"}
    deletion = next(f for f in findings if f.name == "deletion_shape")
    assert deletion.severity in ("warn", "critical")
