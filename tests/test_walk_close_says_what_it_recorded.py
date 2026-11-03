"""`walk close` says which walked head it recorded, or that it recorded none and why.

Aether and Aria each closed a walk before committing, got no walked head, and `walk amend`
refused with no hint of the cause. These tests use a real temporary git repository and the
real walk store. Nothing about what counts as a valid close is tested or changed here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from divineos.cli.council_walk_commands import register
from divineos.core import council_walk as cw

from _walk_helpers import apply_delivered


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "work"
    r.mkdir()
    _git(r, "init", "-q", "--initial-branch=main")
    (r / "base.txt").write_text("base\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "base")
    _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(r, "switch", "-qc", "feature")
    return r


def _ready_walk() -> str:
    opened = cw.open_walk("does this change hold across every file it touches", scope=("a.py",))
    for lens in opened["lenses"]:
        apply_delivered(
            cw, opened["walk_id"], lens, "a finding that is long enough to count: " + lens
        )
    return opened["walk_id"]


def _close_via_cli(walk_id: str, repo: Path) -> str:
    group = click.Group()
    register(group)
    result = CliRunner().invoke(group, ["walk", "close", walk_id, "--repo", str(repo)])
    assert result.exit_code == 0, result.output
    return result.output


def test_a_close_with_a_committed_change_prints_the_short_sha(repo):
    (repo / "a.py").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "add a.py")
    head = _git(repo, "rev-parse", "HEAD")
    out = _close_via_cli(_ready_walk(), repo)
    assert f"walked head recorded: {head[:9]}" in out
    assert "NO walked head" not in out


def test_a_close_with_only_uncommitted_changes_says_none_and_names_the_fix(repo):
    (repo / "a.py").write_text("x\n", encoding="utf-8")  # never committed
    out = _close_via_cli(_ready_walk(), repo)
    assert "NO walked head recorded" in out
    assert "uncommitted changes" in out
    assert "commit the change by exact path" in out
    assert "--repo <work copy>" in out


def test_a_close_with_no_commit_ahead_of_base_says_so(repo):
    out = _close_via_cli(_ready_walk(), repo)
    assert "NO walked head recorded" in out
    assert "no commit ahead" in out
    assert "commit the change by exact path" in out


def test_the_amend_refusal_names_the_recovery(repo):
    (repo / "a.py").write_text("x\n", encoding="utf-8")
    walk = _ready_walk()
    cw.close_walk(walk, repo=repo)  # uncommitted: no walked head
    with pytest.raises(cw.WalkRefused) as caught:
        cw.amend_walk(walk, "a long enough sentence about what changed here", repo=repo)
    text = str(caught.value)
    assert "no walked head" in text
    assert "commit the change by exact path" in text
    assert "--repo <work copy>" in text
