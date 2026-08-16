"""The prereg gate must not read merge-inherited modules as newly authored.

``git diff --cached --name-status`` during a merge compares the index against
the FIRST parent only, so every file arriving from the branch being merged in
reads as status 'A'. It is not new — it landed on the other side, under its own
commit, where this same gate already applied.

It fired that way twice on 2026-08-15, while merging main into two stale PR
branches: seven core modules each time, none authored in the merge, all already
pre-registered when they first landed. The honest response each time was a
provenance paragraph in the commit message — a cost paid by the writer to
satisfy a check that was wrong, which is exactly the shape that teaches me to
stop reading gate output.

Falsifier-first discipline targets the moment a NEW capability lands. A merge
propagates a capability; it does not land one.

BOTH SIDES ARE TESTED. A gate made quieter is not a gate made better, and the
whole value of this one is that it still blocks genuinely new infra — including
a module authored WHILE a merge is open, which is the hole the cheap fix
(skip everything during a merge) would have left.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def _run_gate(repo, message, script):
    msg = repo / "COMMIT_MSG"
    msg.write_text(message, encoding="utf-8")
    return subprocess.run(
        ["python", str(script), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def script():
    return Path(__file__).parent.parent / "scripts" / "check_prereg_for_new_infra.py"


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "src" / "divineos" / "core").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=r)
    _git("config", "user.email", "t@t", cwd=r)
    _git("config", "user.name", "t", cwd=r)
    (r / "README.md").write_text("base\n", encoding="utf-8")
    _git("add", "-A", cwd=r)
    _git("commit", "-qm", "base", cwd=r)
    return r


def _open_a_merge(repo):
    """Leave repo mid-merge with core/from_side.py arriving from the side branch."""
    _git("checkout", "-q", "-b", "side", cwd=repo)
    (repo / "src" / "divineos" / "core" / "from_side.py").write_text("y = 2\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "feat: side module\n\nper prereg-111111111111", cwd=repo)

    _git("checkout", "-q", "main", cwd=repo)
    (repo / "README.md").write_text("moved on\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "main moves", cwd=repo)

    _git("merge", "side", "--no-commit", "--no-ff", cwd=repo)


def test_new_infra_still_blocks(repo, script):
    """The catch must survive: a genuinely new core module with no prereg."""
    (repo / "src" / "divineos" / "core" / "brand_new.py").write_text("x = 1\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)

    result = _run_gate(repo, "feat: add a thing\n", script)

    assert result.returncode == 1, result.stderr
    assert "brand_new.py" in result.stderr


def test_new_infra_passes_with_a_prereg_reference(repo, script):
    (repo / "src" / "divineos" / "core" / "brand_new.py").write_text("x = 1\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)

    result = _run_gate(repo, "feat: add a thing\n\nper prereg-abc123def456\n", script)

    assert result.returncode == 0, result.stderr


def test_merge_inherited_module_is_not_treated_as_new(repo, script):
    """The misfire, pinned."""
    _open_a_merge(repo)
    assert (repo / ".git" / "MERGE_HEAD").exists(), "fixture must leave a merge in progress"
    staged = _git("diff", "--cached", "--name-status", cwd=repo).stdout
    assert "from_side.py" in staged, "fixture must stage the inherited file as added"

    result = _run_gate(repo, "Merge side into main\n", script)

    assert result.returncode == 0, f"merge-inherited module should not block: {result.stderr}"
    assert "inherited from the merged-in side" in result.stderr


def test_a_module_authored_during_the_merge_still_blocks(repo, script):
    """The hole the cheap fix would have left.

    Skipping the gate whenever a merge is open would mean a module written
    while resolving conflicts is never seen. Only files present on the
    merged-in side are exempt.
    """
    _open_a_merge(repo)
    (repo / "src" / "divineos" / "core" / "smuggled.py").write_text("z = 3\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)

    result = _run_gate(repo, "Merge side into main\n", script)

    assert result.returncode == 1, "a module authored during the merge must still be gated"
    assert "smuggled.py" in result.stderr
