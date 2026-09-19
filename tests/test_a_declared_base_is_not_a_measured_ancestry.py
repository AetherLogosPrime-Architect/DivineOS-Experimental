"""The tool that prints a declared base beside a measured ancestry.

Non-vacuity is the whole point of this file. An instrument that answers
SIBLINGS for every input would have printed the right answer on 2026-09-19 by
luck, and would have been worthless. So each verdict is proved reachable by
building a repository that genuinely has that shape.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.pr_base_vs_ancestry import ancestry


def _run(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name, encoding="utf-8")
    _run(repo, "add", name)
    _run(repo, "commit", "-m", name)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch repository whose branches are named like remote ones.

    ancestry() prefixes with origin/ and fetches. Creating the branches under
    those literal names and running from inside makes the fetch a no-op
    against a repo that has no remote, so the lookups resolve locally.
    """
    r = tmp_path / "scratch"
    r.mkdir()
    _run(r, "init", "-q", "-b", "main")
    _run(r, "config", "user.email", "t@t")
    _run(r, "config", "user.name", "t")
    _commit(r, "root")
    _run(r, "branch", "origin/main")
    monkeypatch.chdir(r)
    return r


def test_a_branch_built_on_top_of_another_reads_as_stacked(repo: Path):
    _run(repo, "checkout", "-q", "-b", "origin/lower")
    _commit(repo, "lower")
    _run(repo, "checkout", "-q", "-b", "origin/upper")
    _commit(repo, "upper")

    out = " ".join(ancestry("lower", "upper"))
    assert "STACKED" in out
    assert "SIBLINGS" not in out


def test_two_branches_off_a_shared_root_read_as_siblings(repo: Path):
    _run(repo, "checkout", "-q", "-b", "origin/left")
    _commit(repo, "left")
    _run(repo, "checkout", "-q", "main")
    _run(repo, "checkout", "-q", "-b", "origin/right")
    _commit(repo, "right")

    out = " ".join(ancestry("left", "right"))
    assert "SIBLINGS" in out
    assert "STACKED" not in out


def test_the_siblings_verdict_says_not_to_rebase_rather_than_only_naming_the_shape(repo: Path):
    """The 2026-09-19 fault was acting on the shape, so the shape alone is not enough."""
    _run(repo, "checkout", "-q", "-b", "origin/left")
    _commit(repo, "left")
    _run(repo, "checkout", "-q", "main")
    _run(repo, "checkout", "-q", "-b", "origin/right")
    _commit(repo, "right")

    out = " ".join(ancestry("left", "right")).lower()
    assert "rebase" in out
    assert "never had" in out


def test_a_base_already_containing_the_head_reads_as_behind(repo: Path):
    _run(repo, "checkout", "-q", "-b", "origin/upper")
    _commit(repo, "upper")
    _run(repo, "branch", "origin/lower")
    _commit(repo, "further")

    out = " ".join(ancestry("upper", "lower"))
    assert "BEHIND" in out


def test_a_branch_missing_from_this_machine_reports_unchecked_not_a_verdict(repo: Path):
    """A measurement that could not run must never be reported as a result."""
    out = " ".join(ancestry("main", "no-such-branch"))
    assert "UNCHECKED" in out
    for verdict in ("STACKED", "SIBLINGS", "BEHIND"):
        assert verdict not in out
