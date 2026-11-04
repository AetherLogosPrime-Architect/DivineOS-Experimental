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


def _walk_with_scope(scope: tuple[str, ...]) -> str:
    opened = cw.open_walk("does this change hold across every file it touches", scope=scope)
    for lens in opened["lenses"]:
        apply_delivered(
            cw, opened["walk_id"], lens, "a finding that is long enough to count: " + lens
        )
    return opened["walk_id"]


def _one_line(out: str) -> str:
    return " ".join(out.split())


def _commit_file(repo: Path, name: str) -> None:
    (repo / name).write_text("x\n", encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-qm", f"add {name}")


def test_a_scoped_file_uncommitted_while_an_outside_file_is_committed(repo):
    _commit_file(repo, "b.py")
    (repo / "a.py").write_text("x\n", encoding="utf-8")  # scoped, never committed
    out = _one_line(_close_via_cli(_ready_walk(), repo))
    assert "outside this walk's scope (b.py)" in out
    assert "the scoped files have uncommitted changes" not in out
    assert "Move b.py to its own branch" in out
    assert "commit the scoped files by exact path" in out
    assert "To bind it" not in out


def test_only_an_unrelated_change_committed(repo):
    _commit_file(repo, "b.py")
    out = _one_line(_close_via_cli(_ready_walk(), repo))
    assert "outside this walk's scope (b.py)" in out
    assert "Move b.py to its own branch" in out
    assert "commit the scoped files" not in out
    assert "commit the change by exact path first" not in out


def test_a_repo_that_is_not_a_git_repository(repo):
    import tempfile

    # The system temp folder, not tmp_path: pytest's tmp_path can sit inside this very checkout.
    with tempfile.TemporaryDirectory() as plain:
        nogit = Path(plain)
        assert not (nogit / ".git").exists()
        out = _one_line(_close_via_cli(_ready_walk(), nogit))
    assert "is not a git repository" in out
    assert "passing --repo <work copy>" in out
    assert "not a non-empty subset" not in out


def test_an_empty_scope(repo):
    _commit_file(repo, "a.py")
    out = _one_line(_close_via_cli(_walk_with_scope(()), repo))
    assert "this walk has no scope" in out
    assert "--scope" in out
    assert "commit the change by exact path" not in out


def test_an_uncommitted_scoped_file_in_a_brand_new_folder_gets_the_true_reason(repo):
    (repo / "newdir").mkdir()
    (repo / "newdir" / "a.py").write_text("x\n", encoding="utf-8")  # git status shows "newdir/"
    out = _one_line(_close_via_cli(_walk_with_scope(("newdir/a.py",)), repo))
    assert "the scoped files have uncommitted changes: newdir/a.py" in out


def test_an_uncommitted_scoped_file_with_a_space_in_its_name_gets_the_true_reason(repo):
    (repo / "my file.py").write_text("x\n", encoding="utf-8")
    out = _one_line(_close_via_cli(_walk_with_scope(("my file.py",)), repo))
    assert "the scoped files have uncommitted changes: my file.py" in out


def test_the_amend_refusal_for_an_empty_scope_gives_that_reasons_fix(repo):
    _commit_file(repo, "a.py")
    walk = _walk_with_scope(())
    cw.close_walk(walk, repo=repo)
    with pytest.raises(cw.WalkRefused) as caught:
        cw.amend_walk(walk, "a long enough sentence about what changed here", repo=repo)
    text = " ".join(str(caught.value).split())
    assert "this walk has no scope" in text
    assert "commit the change by exact path" not in text


def test_the_amend_refusal_for_an_out_of_scope_commit_gives_that_reasons_fix(repo):
    _commit_file(repo, "b.py")
    walk = _ready_walk()
    cw.close_walk(walk, repo=repo)
    with pytest.raises(cw.WalkRefused) as caught:
        cw.amend_walk(walk, "a long enough sentence about what changed here", repo=repo)
    text = " ".join(str(caught.value).split())
    assert "outside this walk's scope (b.py)" in text
    assert "Move b.py to its own branch" in text
    assert "commit the change by exact path first" not in text


def test_the_printed_fix_is_one_line_never_two(repo):
    out = _close_via_cli(_ready_walk(), repo)
    assert out.count("To fix it") + out.count("To bind it") <= 1
