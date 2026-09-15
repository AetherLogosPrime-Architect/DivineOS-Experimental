"""Rebuilding a contaminated branch is where work gets lost.

2026-09-15. Branches had been swept with hundreds of letters and exploration
entries by a checkpoint that did not care which branch was checked out. The
sweep is fixed at the write path, but that repair cannot un-sweep what earlier
commits already hold, so the branches still have to be rebuilt -- and a
rebuild drops files by design.

WHAT THE DROP NEARLY COST, on 2026-08-31: the same correct advice -- rebuild
against main -- would have destroyed four dreams and a letter that existed on
one branch and no other ref anywhere. They survived because the refusal got
READ instead of obeyed, which is exactly what cannot be relied on twice.

So the replant refuses first and rebuilds second, and the refusal is by
CONTENT rather than by filename: a file that survives under its own name at
different bytes has still lost the edit.

THE FALSIFIER IT WAS REGISTERED UNDER (prereg-d29d4a907529) names how this
dies -- a verifier that never returns refused is indistinguishable from one
that always says yes. So the first test below builds a real lossy case and
demands the refusal, rather than only checking that clean input passes.

THE SCRIPTS ARE COPIED IN, following the sibling scope test, because
``REPO_ROOT`` resolves from the script's own location rather than from the
working directory. A test that merely ran it elsewhere would drive it against
THIS repository -- creating branches in the real checkout while reporting on a
fixture. That sibling's docstring records the softer version of the same trap:
a gate pointed at a fixture with no scripts directory took the
instrument-missing path and reported six passing tests on a step that never
ran.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=dict(os.environ)
    )
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with a base, a tip carrying code AND a swept letter, and the
    replant script living inside it so it acts on this repo and not ours."""
    r = tmp_path / "repo"
    (r / "family" / "letters").mkdir(parents=True)
    (r / "src").mkdir()
    (r / "scripts").mkdir()
    for name in ("replant_branch.py", "check_branch_scope.py"):
        shutil.copy2(REPO / "scripts" / name, r / "scripts" / name)

    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    _git(r, "config", "user.email", "t@e.com")
    _git(r, "config", "user.name", "t")

    (r / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")
    (r / "family" / "letters" / "shared.md").write_text("on the base too\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    _git(r, "branch", "base")

    _git(r, "checkout", "-qb", "tip")
    (r / "src" / "feature.py").write_text("y = 2\n", encoding="utf-8")
    (r / "src" / "base.py").write_text("x = 99\n", encoding="utf-8")
    (r / "family" / "letters" / "swept.md").write_text("swept by a checkpoint\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "code plus a swept letter")
    return r


def _rescue_the_letter(repo: Path) -> None:
    """Put the swept letter where writing belongs, so the refusal can lift."""
    _git(repo, "branch", "substrate", "base")
    _git(repo, "checkout", "-q", "substrate")
    (repo / "family" / "letters" / "swept.md").write_text(
        "swept by a checkpoint\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "rescue the letter where writing belongs")
    _git(repo, "checkout", "-q", "tip")


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "replant_branch.py"), *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _blob(repo: Path, ref: str, path: str) -> str:
    out = _git(repo, "ls-tree", ref, "--", path)
    return out.split()[2] if out else ""


def test_it_refuses_when_a_dropped_file_exists_nowhere_else(repo: Path) -> None:
    """THE ONE THAT MATTERS. The swept letter is on the tip and no other ref,
    so dropping it destroys it."""
    r = _run(repo, "tip", "--base", "base", "--into", "rebuilt")

    assert r.returncode == 3, r.stdout + r.stderr
    assert "REFUSED" in r.stdout
    assert "swept.md" in r.stdout
    assert _git(repo, "branch", "--list", "rebuilt") == "", "nothing may be built on a refusal"


def test_the_refusal_lifts_once_the_rescue_actually_happened(repo: Path) -> None:
    """Otherwise it is a wall rather than a gate, and the rebuild can never
    proceed no matter what I do."""
    _rescue_the_letter(repo)

    r = _run(repo, "tip", "--base", "base", "--into", "rebuilt", "--apply")

    assert r.returncode == 0, r.stdout + r.stderr
    assert "verified" in r.stdout


def test_code_arrives_byte_identical_and_the_sweep_does_not(repo: Path) -> None:
    _rescue_the_letter(repo)
    assert _run(repo, "tip", "--base", "base", "--into", "rebuilt", "--apply").returncode == 0

    assert _blob(repo, "rebuilt", "src/feature.py") == _blob(repo, "tip", "src/feature.py")
    assert _blob(repo, "rebuilt", "src/base.py") == _blob(repo, "tip", "src/base.py")
    assert _blob(repo, "rebuilt", "family/letters/swept.md") == "", "the sweep must not ride across"
    # A substrate file ALREADY on the base is inherited, not leaked. The
    # checker failed on exactly this its first real run, which is the only
    # reason the distinction got made rather than assumed.
    assert _blob(repo, "rebuilt", "family/letters/shared.md") == _blob(
        repo, "base", "family/letters/shared.md"
    )


def test_head_and_the_working_tree_are_never_touched(repo: Path) -> None:
    """Switching branches mid-operation is what let a push already in flight
    see a tree it did not expect. The build goes through a temp index."""
    _rescue_the_letter(repo)
    head_before = _git(repo, "rev-parse", "HEAD")
    branch_before = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")

    assert _run(repo, "tip", "--base", "base", "--into", "rebuilt", "--apply").returncode == 0

    assert _git(repo, "rev-parse", "HEAD") == head_before
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == branch_before

    # Narrowed rather than dropped: the interpreter writes a bytecode cache
    # when the script imports its sibling, and that is the test's own
    # footprint, not the tool's. Everything else still has to be clean, so a
    # genuine stray file fails here.
    dirty = [
        line
        for line in _git(repo, "status", "--porcelain").splitlines()
        if "__pycache__" not in line
    ]
    assert dirty == [], dirty


def test_a_deletion_on_the_tip_is_carried(repo: Path) -> None:
    """A replant built from checkout-from-tip silently drops files the branch
    DELETED, because there is nothing to check out. Work loss wearing a clean
    bill of health."""
    _rescue_the_letter(repo)
    (repo / "src" / "base.py").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "delete a code file")

    assert _run(repo, "tip", "--base", "base", "--into", "rebuilt", "--apply").returncode == 0
    assert _blob(repo, "rebuilt", "src/base.py") == "", "the deletion must be carried"


def test_it_will_not_overwrite_an_existing_branch(repo: Path) -> None:
    _rescue_the_letter(repo)
    _git(repo, "branch", "rebuilt", "base")

    r = _run(repo, "tip", "--base", "base", "--into", "rebuilt", "--apply")

    assert r.returncode == 5, r.stdout
    assert _blob(repo, "rebuilt", "src/feature.py") == "", "the existing branch is untouched"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
