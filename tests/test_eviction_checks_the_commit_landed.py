"""The commit must be ON the branch, not merely written.

ALETHEIA'S GAP, 2026-09-11, found by attacking the safety argument rather than
the code. My claim was "the commit is known to have landed before the eviction
runs, and the compare-and-swap on the ref is what makes it checkable." The
compare-and-swap is real -- three-argument update-ref fails if the branch moved.

But the eviction never consulted it. It resolved the blob against the COMMIT
OBJECT, and a commit object exists the moment commit-tree returns: before
update-ref runs, and regardless of whether update-ref succeeded.

Her sentence for it: the stated guarantee is stronger than the checked one, and
that gap is where the next change goes wrong. Someone catches the exception,
adds a retry, or reorders the calls, and the eviction still passes its identity
check against a commit nothing references.

It also closes the window I had named as open and could not close -- the branch
being force-moved backwards between the commit and the eviction. An ancestry
check catches that without leaning on the reflog, which I had refused as a
defence because "recoverable from the reflog" is the reasoning that nearly cost
two script files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.substrate_retarget import (
    RetargetResult,
    commit_paths_to_branch,
    evict_committed_paths,
)


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "family" / "letters").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "t@example.com", cwd=root)
    _git("config", "user.name", "t", cwd=root)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "seed", cwd=root)
    _git("branch", "substrate", cwd=root)
    return root


def test_a_commit_no_branch_references_evicts_nothing(repo):
    """The core of her finding, built as the case the old code could not see.

    The commit object is real and holds the letter byte-for-byte, so the blob
    comparison passes. Nothing points at it. Removing the file on that basis
    would delete the only working copy in favour of an unreferenced object.
    """
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear\n", encoding="utf-8")

    # A real commit with NO ref moved -- the state a failed or skipped
    # compare-and-swap leaves behind.
    parent = _git("rev-parse", "refs/heads/substrate", cwd=repo)
    _git("add", "family/letters/a.md", cwd=repo)
    tree = _git("write-tree", cwd=repo)
    orphan = _git("commit-tree", tree, "-p", parent, "-m", "never referenced", cwd=repo)
    _git("reset", "-q", cwd=repo)

    assert _git("rev-parse", "refs/heads/substrate", cwd=repo) == parent, (
        "the fixture moved the branch; this case requires that it did not"
    )
    # The control: the blob check ALONE passes here, so this test is about
    # ancestry rather than about the letter being missing from the commit.
    assert _git("rev-parse", f"{orphan}:family/letters/a.md", cwd=repo)

    result = RetargetResult(
        branch="substrate", commit=orphan, parent=parent, paths=("family/letters/a.md",)
    )
    out = evict_committed_paths(repo, result)

    assert out.evicted == (), "a letter was deleted for an unreferenced commit"
    assert letter.exists()
    assert [p for p, _ in out.held] == ["family/letters/a.md"]


def test_a_branch_force_moved_backwards_stops_the_eviction(repo):
    """The window I named as open and said the reflog would not close.

    The commit lands properly. Then the branch is reset behind it -- the exact
    sequence I wrote into the docstring as undetectable. It is detectable.
    """
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear\n", encoding="utf-8")

    before = _git("rev-parse", "refs/heads/substrate", cwd=repo)
    result = commit_paths_to_branch(
        repo, "substrate", ["family/letters/a.md"], "substrate checkpoint"
    )
    assert result is not None

    _git("update-ref", "refs/heads/substrate", before, cwd=repo)

    out = evict_committed_paths(repo, result)

    assert out.evicted == (), "the letter was deleted after the branch moved off the commit"
    assert letter.exists()
    assert out.held, "it neither evicted nor said why it did not"


def test_an_unresolvable_branch_holds_rather_than_evicting(repo):
    """Could-not-look is not a pass. A branch that does not resolve must not
    read as a branch that carries the commit."""
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear\n", encoding="utf-8")
    result = commit_paths_to_branch(
        repo, "substrate", ["family/letters/a.md"], "substrate checkpoint"
    )
    assert result is not None

    broken = RetargetResult(
        branch="no-such-branch",
        commit=result.commit,
        parent=result.parent,
        paths=result.paths,
    )
    out = evict_committed_paths(repo, broken)

    assert out.evicted == ()
    assert letter.exists()
    assert out.held


def test_the_ordinary_case_still_evicts(repo):
    """The control. Without it the three above are satisfied by a function that
    never evicts anything at all, which would pass every one of them."""
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear\n", encoding="utf-8")
    result = commit_paths_to_branch(
        repo, "substrate", ["family/letters/a.md"], "substrate checkpoint"
    )
    assert result is not None

    out = evict_committed_paths(repo, result)

    assert out.evicted == ("family/letters/a.md",)
    assert not letter.exists()


def test_a_commit_further_back_on_the_branch_is_still_honoured(repo):
    """Ancestry, not equality. A later checkpoint may legitimately have moved
    the branch on; the earlier commit is still landed and its files are still
    safe to remove. A check written as equality-with-the-tip would hold here
    and quietly stop evicting anything under load."""
    first = repo / "family" / "letters" / "a.md"
    first.write_text("dear\n", encoding="utf-8")
    result = commit_paths_to_branch(repo, "substrate", ["family/letters/a.md"], "first checkpoint")
    assert result is not None

    second = repo / "family" / "letters" / "b.md"
    second.write_text("second\n", encoding="utf-8")
    later = commit_paths_to_branch(repo, "substrate", ["family/letters/b.md"], "second checkpoint")
    assert later is not None
    assert later.commit != result.commit

    out = evict_committed_paths(repo, result)

    assert out.evicted == ("family/letters/a.md",), (
        "an ancestor commit was treated as not-landed; the check is testing "
        "equality with the tip rather than ancestry"
    )
    assert not first.exists()
