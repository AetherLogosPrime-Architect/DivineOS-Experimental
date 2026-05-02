"""Tests for the upstream-freshness briefing surface.

Builds a real temp upstream + clone, then exercises the formatter
against synthesized states (parity, behind, ahead+behind, missing
local-main, no remote). No mocking of subprocess — same discipline
as in_flight_branches: actually call git.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from divineos.core.upstream_freshness import (
    BASE_BRANCH,
    REMOTE,
    UpstreamFreshness,
    _check_freshness,
    format_for_briefing,
)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def _commit(repo: Path, message: str) -> None:
    safe = "".join(c if c.isalnum() else "_" for c in message)[:30] or "f"
    fname = repo / f"f-{safe}-{abs(hash(message)) % 10**8}.txt"
    fname.write_text(message, encoding="utf-8")
    _git(repo, "add", str(fname.name))
    _git(repo, "commit", "-m", message)


@pytest.fixture
def two_clones() -> tuple[Path, Path, Path]:
    """Build a bare upstream + two clones (clone_a as 'us', clone_b to advance origin).

    Returns (upstream, clone_a, clone_b). Pushing from clone_b simulates
    "someone else (or another machine) pushed to origin/main." clone_a
    is the repo whose upstream-freshness we test.
    """
    base_tmp = Path(tempfile.mkdtemp())
    upstream = base_tmp / "upstream.git"
    upstream.mkdir()
    _git(upstream, "init", "--bare", "--initial-branch=main")

    clone_a = base_tmp / "clone_a"
    clone_a.mkdir()
    _git(clone_a, "init", "--initial-branch=main")
    _git(clone_a, "config", "user.email", "a@example.com")
    _git(clone_a, "config", "user.name", "a")
    _git(clone_a, "remote", "add", "origin", str(upstream))
    _commit(clone_a, "initial main")
    _git(clone_a, "push", "-u", "origin", "main")

    clone_b = base_tmp / "clone_b"
    clone_b.mkdir()
    _git(clone_b, "clone", str(upstream), ".")
    _git(clone_b, "config", "user.email", "b@example.com")
    _git(clone_b, "config", "user.name", "b")

    yield upstream, clone_a, clone_b

    shutil.rmtree(base_tmp, ignore_errors=True)


def test_local_main_at_parity_returns_empty(two_clones):
    _, clone_a, _ = two_clones
    block = format_for_briefing(cwd=str(clone_a))
    assert block == ""


def test_local_main_behind_surfaces_block(two_clones):
    _, clone_a, clone_b = two_clones
    # clone_b advances origin/main
    _commit(clone_b, "remote moved forward — distinctive subject")
    _git(clone_b, "push", "origin", "main")

    block = format_for_briefing(cwd=str(clone_a))
    assert "[upstream freshness]" in block
    assert "1 commit behind" in block
    assert "distinctive subject" in block
    assert "fetch" in block.lower()


def test_multiple_commits_behind_pluralized(two_clones):
    _, clone_a, clone_b = two_clones
    _commit(clone_b, "advance one")
    _commit(clone_b, "advance two")
    _commit(clone_b, "advance three")
    _git(clone_b, "push", "origin", "main")

    block = format_for_briefing(cwd=str(clone_a))
    assert "3 commits behind" in block


def test_local_main_ahead_only_returns_empty(two_clones):
    """Local main has unpushed commits but is not behind — surface should stay silent."""
    _, clone_a, _ = two_clones
    _commit(clone_a, "local-only work on main")
    block = format_for_briefing(cwd=str(clone_a))
    assert block == ""


def test_local_main_ahead_and_behind_surfaces_with_note(two_clones):
    _, clone_a, clone_b = two_clones
    _commit(clone_a, "local-side commit on main")
    _commit(clone_b, "remote-side commit")
    _git(clone_b, "push", "origin", "main")

    block = format_for_briefing(cwd=str(clone_a))
    assert "behind" in block
    assert "unpushed" in block.lower()


def test_check_returns_dataclass_with_counts(two_clones):
    _, clone_a, clone_b = two_clones
    _commit(clone_b, "remote moved")
    _git(clone_b, "push", "origin", "main")

    result = _check_freshness(cwd=str(clone_a))
    assert isinstance(result, UpstreamFreshness)
    assert result.local_behind == 1
    assert result.local_ahead == 0
    assert "remote moved" in result.remote_subject


def test_no_local_main_branch_returns_empty(two_clones):
    """Workflows without a local main should produce no signal."""
    _, clone_a, _ = two_clones
    # Move off main, delete it locally.
    _git(clone_a, "checkout", "-b", "claude/feature")
    _git(clone_a, "branch", "-D", "main")
    block = format_for_briefing(cwd=str(clone_a))
    assert block == ""


def test_long_subject_truncated(two_clones):
    _, clone_a, clone_b = two_clones
    long_msg = "x" * 200
    _commit(clone_b, long_msg)
    _git(clone_b, "push", "origin", "main")
    block = format_for_briefing(cwd=str(clone_a))
    assert "..." in block
    assert "x" * 200 not in block


def test_git_unavailable_returns_empty():
    """Running outside any git repo returns empty, no exception."""
    with tempfile.TemporaryDirectory() as raw:
        not_a_repo = Path(raw) / "not_a_repo"
        not_a_repo.mkdir()
        # The fetch will fail (no remote). Surface stays silent.
        block = format_for_briefing(cwd=str(not_a_repo))
        assert block == ""


def test_constants_match_expected_remote_and_branch():
    assert BASE_BRANCH == "main"
    assert REMOTE == "origin"


def test_block_includes_fast_forward_command(two_clones):
    """Surface gives the operator the exact command to bring local up to date."""
    _, clone_a, clone_b = two_clones
    _commit(clone_b, "advance")
    _git(clone_b, "push", "origin", "main")
    block = format_for_briefing(cwd=str(clone_a))
    assert "git fetch origin" in block
    assert "merge --ff-only" in block
