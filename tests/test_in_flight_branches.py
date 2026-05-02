"""Tests for the in-flight branches briefing surface.

Uses real git — sets up a temp repo with branches at varying offsets
from main and asserts the formatter sees them. No mocking of subprocess
since the whole point of the module is "actually ask git."
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from divineos.core.in_flight_branches import (
    BASE_REF,
    BRANCH_PREFIX,
    MAX_BRANCHES,
    InFlightBranch,
    _list_in_flight_branches,
    format_for_briefing,
)


def _git(repo: Path, *args: str) -> str:
    """Run a git command in the test repo, asserting success."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


_FILENAME_SAFE = str.maketrans({c: "_" for c in r':\/<>|*?"'})


def _commit(repo: Path, message: str) -> None:
    """Make a commit so each branch has distinct content."""
    safe = message[:20].translate(_FILENAME_SAFE).replace(" ", "_") or "f"
    fname = repo / f"f-{safe}-{abs(hash(message)) % 10**8}.txt"
    fname.write_text(message, encoding="utf-8")
    _git(repo, "add", str(fname.name))
    _git(repo, "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Construct a temp repo simulating a clone with origin/main and several
    claude/* branches at varying offsets from origin/main.
    """
    upstream = tmp_path / "upstream.git"
    upstream.mkdir()
    _git(upstream, "init", "--bare", "--initial-branch=main")

    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "--initial-branch=main")
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "test")
    _git(work, "remote", "add", "origin", str(upstream))
    _commit(work, "initial main")
    _git(work, "push", "-u", "origin", "main")
    return work


def test_no_branches_returns_empty(repo: Path):
    assert format_for_briefing(cwd=str(repo)) == ""
    assert _list_in_flight_branches(cwd=str(repo)) == []


def test_branch_at_parity_not_surfaced(repo: Path):
    """A claude/* branch with zero commits ahead of origin/main is noise."""
    _git(repo, "checkout", "-b", "claude/parity")
    # No commits added — branch tip == main tip.
    assert _list_in_flight_branches(cwd=str(repo)) == []


def test_single_branch_ahead_surfaced(repo: Path):
    _git(repo, "checkout", "-b", "claude/feature-a")
    _commit(repo, "feature a commit 1")
    _commit(repo, "feature a commit 2")

    branches = _list_in_flight_branches(cwd=str(repo))
    assert len(branches) == 1
    assert branches[0].name == "claude/feature-a"
    assert branches[0].commits_ahead == 2
    assert "feature a commit 2" in branches[0].last_subject


def test_non_claude_branches_filtered(repo: Path):
    """Branches outside the claude/ prefix must not appear."""
    _git(repo, "checkout", "-b", "release/foo")
    _commit(repo, "release commit")
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "experimental")
    _commit(repo, "experimental commit")
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "claude/real-arc")
    _commit(repo, "real arc commit")

    branches = _list_in_flight_branches(cwd=str(repo))
    names = [b.name for b in branches]
    assert names == ["claude/real-arc"]


def test_multiple_branches_ordered_newest_first(repo: Path):
    """Branches are sorted by committerdate descending.

    Sleep between commits so committerdate (1-second resolution) actually
    differs — without this, three commits in the same second tie and
    git's secondary sort decides ordering, which isn't what we contract.
    """
    _git(repo, "checkout", "-b", "claude/oldest")
    _commit(repo, "oldest")
    time.sleep(1.1)
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "claude/middle")
    _commit(repo, "middle")
    time.sleep(1.1)
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "claude/newest")
    _commit(repo, "newest")

    branches = _list_in_flight_branches(cwd=str(repo))
    names = [b.name for b in branches]
    assert names == ["claude/newest", "claude/middle", "claude/oldest"]


def test_max_branches_cap_enforced(repo: Path):
    """When more than MAX_BRANCHES exist, only the top-N appear."""
    for i in range(MAX_BRANCHES + 3):
        _git(repo, "checkout", "main")
        _git(repo, "checkout", "-b", f"claude/arc-{i:02d}")
        _commit(repo, f"arc {i} commit")

    branches = _list_in_flight_branches(cwd=str(repo))
    assert len(branches) == MAX_BRANCHES


def test_format_for_briefing_includes_branch_name_and_subject(repo: Path):
    _git(repo, "checkout", "-b", "claude/example")
    _commit(repo, "example: distinctive subject 42")

    block = format_for_briefing(cwd=str(repo))
    assert "[in-flight branches]" in block
    assert "claude/example" in block
    assert "distinctive subject 42" in block
    assert "1 ahead" in block


def test_format_for_briefing_recognition_prompt_disclaimer(repo: Path):
    """The block names itself as recognition-only, not a priority list."""
    _git(repo, "checkout", "-b", "claude/arc")
    _commit(repo, "arc commit")
    block = format_for_briefing(cwd=str(repo))
    assert "Not prioritized" in block or "recognition prompt" in block


def test_long_subject_truncated(repo: Path):
    _git(repo, "checkout", "-b", "claude/long-subject")
    long_msg = "x" * 200
    _commit(repo, long_msg)
    block = format_for_briefing(cwd=str(repo))
    # Truncated form contains "..." and is shorter than the original.
    assert "..." in block
    assert "x" * 200 not in block


def test_git_unavailable_returns_empty():
    """Running outside any git repo returns empty, no exception.

    Uses OS-level tempdir (not pytest tmp_path) to escape the project's
    git tree — pytest's tmp_path is configured under <repo>/tmp/pytest/
    by conftest.py, which would let git's parent-walk discover the host
    repo and contaminate the test.
    """
    with tempfile.TemporaryDirectory() as raw:
        not_a_repo = Path(raw) / "not_a_repo"
        not_a_repo.mkdir()
        assert format_for_briefing(cwd=str(not_a_repo)) == ""


def test_module_constants_sane():
    assert BRANCH_PREFIX == "claude/"
    assert BASE_REF == "origin/main"
    assert MAX_BRANCHES > 0
    assert isinstance(InFlightBranch.__dataclass_fields__, dict)


def test_remote_only_branch_surfaced(repo: Path):
    """Branches that exist only as origin/claude/* (not local) still surface."""
    # Create on local, push, then delete local — leaves only origin/claude/foo.
    _git(repo, "checkout", "-b", "claude/remote-only")
    _commit(repo, "remote only commit")
    _git(repo, "push", "-u", "origin", "claude/remote-only")
    _git(repo, "checkout", "main")
    _git(repo, "branch", "-D", "claude/remote-only")

    branches = _list_in_flight_branches(cwd=str(repo))
    names = [b.name for b in branches]
    assert "claude/remote-only" in names
