"""The prereg-before-infra gate must not flag merge-inherited files.

Aria 2026-07-31, found by hitting it on a real merge. Merging origin/main
into a working branch brought in src/divineos/core/auto_goal.py — Aether's
module, already carrying prereg-99f3fd587018 on its own commit. The gate
demanded a pre-registration for it anyway, because `git diff --cached`
during a merge compares the merge RESULT against HEAD only, so everything
the other side introduced reads as newly added by the merge commit.

These tests drive real git repositories rather than mocking the plumbing —
the bug lived entirely in what git reports during a merge, so a mock of git
would have reproduced the wrong behavior and passed.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def _load_gate_module():
    path = Path(__file__).resolve().parent.parent / "scripts" / "check_prereg_for_new_infra.py"
    spec = importlib.util.spec_from_file_location("check_prereg_for_new_infra", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_prereg_for_new_infra"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate_module()

INFRA = "src/divineos/core/thing.py"
OTHER_INFRA = "src/divineos/core/other.py"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=30
    )
    return r.stdout


def _write(repo: Path, rel: str, body: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t.t")
    _git(r, "config", "user.name", "t")
    _write(r, "README.md", "base\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "--no-verify", "-m", "base")
    return r


def test_merge_inherited_infra_is_not_flagged(repo: Path, monkeypatch) -> None:
    """A module introduced by the OTHER side of a merge is not 'new' here."""
    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo, INFRA, "# arrives from feature\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "feat: add infra per prereg-abc123abc123")

    _git(repo, "checkout", "-q", "main")
    _write(repo, "README.md", "moved on\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "docs: unrelated")

    _git(repo, "merge", "--no-commit", "--no-ff", "feature")

    monkeypatch.chdir(repo)
    assert gate._merge_head() is not None, "MERGE_HEAD should exist mid-merge"
    assert INFRA not in gate._staged_new_files()


def test_merge_commit_adding_its_own_infra_is_still_flagged(repo: Path, monkeypatch) -> None:
    """Not a blanket merge exemption — a file at NEITHER parent still counts."""
    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo, INFRA, "# arrives from feature\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "feat: add infra")

    _git(repo, "checkout", "-q", "main")
    _write(repo, "README.md", "moved on\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--no-verify", "-m", "docs: unrelated")

    _git(repo, "merge", "--no-commit", "--no-ff", "feature")
    # A module born in the merge itself, present on neither parent.
    _write(repo, OTHER_INFRA, "# born in the merge\n")
    _git(repo, "add", OTHER_INFRA)

    monkeypatch.chdir(repo)
    staged = gate._staged_new_files()
    assert OTHER_INFRA in staged, "merge-born infra must still be gated"
    assert INFRA not in staged, "inherited infra must still be exempt"


def test_normal_commit_behavior_unchanged(repo: Path, monkeypatch) -> None:
    """Outside a merge nothing is filtered — the original contract holds."""
    _write(repo, INFRA, "# plain new module\n")
    _git(repo, "add", "-A")

    monkeypatch.chdir(repo)
    assert gate._merge_head() is None
    assert INFRA in gate._staged_new_files()


def test_exists_in_fails_toward_flagging(repo: Path, monkeypatch) -> None:
    """An unresolvable revision must not silently exempt a file."""
    monkeypatch.chdir(repo)
    assert gate._exists_in("0000000000000000000000000000000000000000", INFRA) is False
