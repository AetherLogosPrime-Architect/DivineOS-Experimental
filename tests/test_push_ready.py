"""Tests for divineos.core.push_ready.

Each test spins up a throwaway git repo in a tmp_path so we never touch
the real repository or remote.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core import push_ready
from divineos.core.push_ready import (
    _commits_needing_trailer,
    detect_commits,
    load_guardrail_set,
    run_push_ready,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(origin)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)], capture_output=True, check=True
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "remote", "add", "origin", str(origin))

    (repo / "scripts").mkdir()
    (repo / "scripts" / "guardrail_files.txt").write_text(
        "# comment\nsrc/guarded.py\n", encoding="utf-8"
    )
    (repo / "src").mkdir()
    (repo / "src" / "guarded.py").write_text("# guarded\n", encoding="utf-8")
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "push", "origin", "main")

    _git(repo, "checkout", "-b", "feat/x")
    return repo


def _commit(repo: Path, path: str, content: str, msg: str) -> str:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)
    return _git(repo, "rev-parse", "HEAD").strip()


def test_load_guardrail_set(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    assert load_guardrail_set(repo) == {"src/guarded.py"}


def test_detect_guardrail_touching(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "README.md", "changed\n", "docs: harmless")
    _commit(repo, "src/guarded.py", "# v2\n", "touch guardrail")
    commits = detect_commits(repo, "feat/x")
    assert len(commits) == 2
    subjects = [c.subject for c in commits]
    assert subjects == ["docs: harmless", "touch guardrail"]
    assert commits[0].touches_guardrail is False
    assert commits[1].touches_guardrail is True
    assert commits[1].guardrail_files == ["src/guarded.py"]


def test_skips_commits_with_existing_valid_trailer(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(
        repo,
        "src/guarded.py",
        "# v2\n",
        "touch guardrail\n\nExternal-Review: round-abc123",
    )
    commits = detect_commits(repo, "feat/x")
    assert commits[0].has_trailer is True
    assert commits[0].trailer_value == "round-abc123"
    assert _commits_needing_trailer(commits) == []


def test_no_guardrail_commits_returns_noop(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "README.md", "a\n", "docs a")
    _commit(repo, "README.md", "b\n", "docs b")
    result = run_push_ready(repo, dry_run=True)
    assert result.needing_trailer == []
    assert result.round_id is None
    assert "Nothing to do" in result.message


def test_dry_run_does_not_modify_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    sha = _commit(repo, "src/guarded.py", "# v2\n", "touch guardrail")

    def _boom(*a: object, **k: object) -> str:
        raise AssertionError("dry-run should not open audit rounds")

    monkeypatch.setattr(push_ready, "open_audit_round", _boom)
    monkeypatch.setattr(push_ready, "amend_trailers", _boom)
    monkeypatch.setattr(push_ready, "force_push_branch", _boom)

    result = run_push_ready(repo, dry_run=True)
    assert len(result.needing_trailer) == 1
    assert result.round_id is None
    assert result.amended_shas == []
    assert not result.pushed
    assert "dry-run" in result.message
    assert _git(repo, "rev-parse", "HEAD").strip() == sha
