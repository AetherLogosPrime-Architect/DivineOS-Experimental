"""A file is removed only when the bytes on disk are the bytes that were saved.

Routing substrate to its own branch by plumbing is safe BECAUSE it never
touches the working tree -- that is what stops it losing a race with a push
already in flight. The consequence is that the letters it commits stay on disk
as untracked files on a branch that cannot see the commit holding them, so
every later checkpoint finds them again. The interim split named that tension
in its own comment and shipped the half that was safe under either answer.
This covers the other half.

THE FAILURE THIS IS BUILT AROUND IS ARIA'S, NOT A HYPOTHETICAL. Her eviction
command verified by asking whether the PATH existed on the substrate branch.
For a REWRITTEN file that is true of the copy being replaced -- so the check
passes on the strength of the old version and then deletes the new one. It ran,
reported success, and the push was refused again by eleven regenerated files it
had claimed to handle. Her sentence for it: presence is not safety.

So the predicate here is blob identity. Git objects are content-addressed, so
equal ids mean byte-identical content rather than probably-the-same-file, which
makes this an identity proof and not a heuristic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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


def test_a_file_that_matches_what_landed_is_taken_off_the_floor(repo):
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear\n", encoding="utf-8")

    result = _land(repo, ["family/letters/a.md"])
    out = evict_committed_paths(repo, result)

    assert out.evicted == ("family/letters/a.md",)
    assert out.held == ()
    assert not letter.exists()
    assert _git("status", "--porcelain", cwd=repo) == ""


def test_the_letter_is_readable_afterwards_from_the_branch_it_went_to(repo):
    """Removed is not lost, and this is the assertion that says so."""
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("dear Aria\n", encoding="utf-8")

    result = _land(repo, ["family/letters/a.md"])
    evict_committed_paths(repo, result)

    assert not letter.exists()
    back = _git("show", f"{result.commit}:family/letters/a.md", cwd=repo)
    assert back == "dear Aria", "the file was deleted and cannot be read back"


def test_a_file_rewritten_after_the_commit_is_kept_not_deleted(repo):
    """ARIA'S CASE, and the whole reason the predicate is bytes and not paths.

    The path is present on the branch -- as the copy being replaced. A
    presence check passes here and deletes the newer version. This must not.
    """
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("first draft\n", encoding="utf-8")
    result = _land(repo, ["family/letters/a.md"])

    letter.write_text("second draft, and this one is not saved anywhere\n", encoding="utf-8")
    out = evict_committed_paths(repo, result)

    assert out.evicted == ()
    assert letter.exists(), "the rewritten letter was deleted on the strength of the old one"
    assert letter.read_text(encoding="utf-8").startswith("second draft")
    assert [p for p, _ in out.held] == ["family/letters/a.md"]
    assert "differ" in out.held[0][1]


def test_the_control_a_presence_check_would_have_passed_this_case(repo):
    """The control test. Without it the one above proves nothing about WHY.

    If the path were absent from the commit, holding the file would be
    unremarkable -- any check would hold it. What makes the case sharp is that
    the path IS there, so the weaker predicate would have said yes.
    """
    letter = repo / "family" / "letters" / "a.md"
    letter.write_text("first draft\n", encoding="utf-8")
    result = _land(repo, ["family/letters/a.md"])
    letter.write_text("second draft\n", encoding="utf-8")

    present = subprocess.run(
        ["git", "cat-file", "-e", f"{result.commit}:family/letters/a.md"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    assert present.returncode == 0, (
        "the path is NOT on the branch, so this case never exercised the "
        "difference between a presence check and a byte check"
    )


def test_a_file_tracked_on_the_checked_out_branch_is_never_deleted(repo):
    """Deleting it would not clean the tree -- it would stage a deletion."""
    letter = repo / "family" / "letters" / "tracked.md"
    letter.write_text("already here\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "letter on main", cwd=repo)

    result = commit_paths_to_branch(
        repo, "substrate", ["family/letters/tracked.md"], "substrate checkpoint"
    )
    assert result is not None
    out = evict_committed_paths(repo, result)

    assert out.evicted == ()
    assert letter.exists()
    assert [p for p, _ in out.held] == ["family/letters/tracked.md"]
    assert "tracked" in out.held[0][1]


def test_a_path_already_deleted_on_disk_is_not_an_error(repo):
    """The deletion was carried through by --add --remove; nothing to remove."""
    letter = repo / "family" / "letters" / "gone.md"
    letter.write_text("here\n", encoding="utf-8")
    result = _land(repo, ["family/letters/gone.md"])
    letter.unlink()

    out = evict_committed_paths(repo, result)

    assert out.evicted == ()
    assert out.held == ()


def test_one_bad_file_does_not_stop_the_others(repo):
    """Held and evicted are independent, so a single hold cannot silently
    abandon the rest -- the shape that turns a partial run into a report of a
    clean one."""
    good = repo / "family" / "letters" / "good.md"
    bad = repo / "family" / "letters" / "bad.md"
    good.write_text("saved\n", encoding="utf-8")
    bad.write_text("saved\n", encoding="utf-8")

    result = _land(repo, ["family/letters/good.md", "family/letters/bad.md"])
    bad.write_text("changed after the commit\n", encoding="utf-8")

    out = evict_committed_paths(repo, result)

    assert out.evicted == ("family/letters/good.md",)
    assert [p for p, _ in out.held] == ["family/letters/bad.md"]
    assert not good.exists()
    assert bad.exists()
