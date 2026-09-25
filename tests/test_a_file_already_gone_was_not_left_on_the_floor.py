"""A removal that fails because the file is already absent is a removal done.

THE INCIDENT, 2026-09-15. Eleven of Aria's regenerated record-books came back
from a checkpoint reported as "committed to the substrate branch but LEFT on
disk", each with a not-found error printed beside it. She read that as the
retarget having failed to cover a path -- hours after we had agreed the class
was closed -- and so did I. Neither of us noticed that the two halves of the
sentence contradict each other: a file the operating system cannot find is not
a file left on the floor.

The eviction had done its job. What failed was the vocabulary. ``held`` is the
bucket for "this is still here and something is stopping me", and a vanished
file was being posted into it because the only distinction the code drew was
whether the unlink call returned cleanly.

An absence and an obstruction are indistinguishable from inside a grip. The
remedy is not to grip harder, it is to give the report a second column.

WHY THIS IS REACHABLE AT ALL, since ``evict_committed_paths`` checks
``exists()`` before touching anything: the check and the removal are two
separate syscalls, and between them another process can take the file --
another checkpoint, a push-readiness tidy, the occupant's own hand. The tests
below reproduce exactly that, by removing the file inside the last read that
happens before the unlink. The FileNotFoundError is raised by the real
filesystem at the real call site; nothing about the unlink is simulated.

THE COST OF THE OLD BEHAVIOUR WAS NOT COSMETIC. A held path is a path the next
checkpoint is told to worry about, and a standing list of phantom stuck files
is how a covered mechanism gets diagnosed as an uncovered one -- which is the
several-hour hunt this file exists to prevent recurring.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core import substrate_retarget
from divineos.core.substrate_retarget import commit_paths_to_branch, evict_committed_paths


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


def _land(repo: Path, paths: list[str]):
    result = commit_paths_to_branch(repo, "substrate", paths, "substrate checkpoint")
    assert result is not None, "the fixture did not actually commit anything"
    return result


@pytest.fixture()
def vanish_before_removal(monkeypatch):
    """Take the file away in the last read before the unlink.

    This is the genuine race window: ``exists()`` has already said yes and the
    blob comparison has already passed, so the code is committed to removing a
    file that is no longer there. Patching the reader rather than the unlink is
    deliberate -- the error under test has to come from the operating system,
    or the test is only asserting that the handler handles what it was handed.
    """
    real = substrate_retarget._blob_in_commit
    taken: list[str] = []

    def take_it_then_answer(root, commit, rel_path):
        answer = real(root, commit, rel_path)
        target = Path(root) / rel_path
        if target.exists():
            target.unlink()
            taken.append(rel_path)
        return answer

    monkeypatch.setattr(substrate_retarget, "_blob_in_commit", take_it_then_answer)
    return taken


def test_a_file_taken_by_someone_else_counts_as_evicted(repo, vanish_before_removal):
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear\n", encoding="utf-8")
    result = _land(repo, ["family/letters/a.md"])

    out = evict_committed_paths(repo, result)

    assert vanish_before_removal == ["family/letters/a.md"], "the race never happened"
    assert out.evicted == ("family/letters/a.md",)
    assert out.held == ()
    assert not letter.exists()


def test_it_is_never_reported_as_still_on_the_floor(repo, vanish_before_removal):
    """The sentence that sent two of us hunting, pinned so it cannot come back."""
    letter = repo / "family" / "letters" / "b.md"
    letter.write_text("dear\n", encoding="utf-8")
    result = _land(repo, ["family/letters/b.md"])

    out = evict_committed_paths(repo, result)

    assert "family/letters/b.md" not in [p for p, _ in out.held]
    assert not any("removal failed" in why for _, why in out.held)


def test_a_file_that_is_genuinely_stuck_is_still_held(repo, monkeypatch):
    """The other column, so the fix cannot become a blanket 'call it done'.

    A removal refused for any reason OTHER than the file being absent is still
    an obstruction and must still be named. Without this, the change above
    reads as 'unlink failures are fine', which is the opposite of the finding.
    """
    letter = repo / "family" / "letters" / "c.md"
    letter.write_text("dear\n", encoding="utf-8")
    result = _land(repo, ["family/letters/c.md"])

    def refuse(self, *a, **k):
        raise PermissionError("in use by another process")

    monkeypatch.setattr(Path, "unlink", refuse)
    out = evict_committed_paths(repo, result)

    assert out.evicted == ()
    assert [p for p, _ in out.held] == ["family/letters/c.md"]
    assert "removal failed" in out.held[0][1]
    assert letter.exists()
