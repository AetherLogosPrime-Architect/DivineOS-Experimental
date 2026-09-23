"""Which branches carry a file -- three answers, and a control before any of them.

Built because the shell one-liner for this question reported a branch as
missing a file it carried (2026-09-23). Every test runs real git in a repository
copied from the session template (the house's guard against the MSYS2 DLL-init
race a fresh `git init` can hit), so each expected answer is known before it is
asked.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
from _git_test_helpers import materialize_repo_from_template

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "which_refs_carry.py"


def _load():
    spec = importlib.util.spec_from_file_location("which_refs_carry", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(git_template_repo: Path, tmp_path: Path, monkeypatch) -> Path:
    """main carries .claude/hooks/x.sh; branch aria/without does not."""
    repo = materialize_repo_from_template(git_template_repo, tmp_path / "repo")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("r\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "branch", "aria/without")
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "x.sh").write_text("#!/bin/bash\n")
    _git(repo, "add", ".claude/hooks/x.sh")
    _git(repo, "commit", "-q", "-m", "hook")
    monkeypatch.chdir(repo)
    return repo


def test_the_three_answers_are_kept_apart(repo: Path) -> None:
    mod = _load()
    path = ".claude/hooks/x.sh"
    assert mod.verdict("main", path) == mod.CARRIES
    assert mod.verdict("aria/without", path) == mod.DOES_NOT
    assert mod.verdict("no/such-branch", path) == mod.COULD_NOT


def test_a_slashed_ref_with_a_dot_path_is_read_correctly(repo: Path) -> None:
    """The exact shape the shell rewrites. Asked through this tool it is never
    rewritten, because no shell stands between the tool and git."""
    mod = _load()
    _git(repo, "branch", "aria/with")
    assert mod.verdict("aria/with", ".claude/hooks/x.sh") == mod.CARRIES


def test_a_failed_control_prints_no_verdicts(repo: Path, capsys) -> None:
    mod = _load()
    rc = mod.main([".claude/hooks/x.sh", "--control", "aria/without", "main"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "CONTROL FAILED" in captured.err
    assert "carries" not in captured.out


def test_a_passing_control_prints_every_answer(repo: Path, capsys) -> None:
    mod = _load()
    rc = mod.main(
        [".claude/hooks/x.sh", "--control", "main", "main", "aria/without", "no/such-branch"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "carried by 1, absent from 1, could not look at 1" in out


def test_a_leading_dot_slash_names_the_same_path(repo: Path) -> None:
    mod = _load()
    assert mod.main(["./.claude/hooks/x.sh", "--control", "main", "main"]) == 0


@pytest.mark.skipif(os.name != "nt", reason="only meaningful where a shell could stand in between")
def test_no_shell_stands_between_the_tool_and_git() -> None:
    """Structural: the one call site passes an argument list and never asks for
    a shell, which is the whole reason the rewrite cannot reach it."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "shell=True" not in text
    assert 'subprocess.run(["git", *args]' in text
