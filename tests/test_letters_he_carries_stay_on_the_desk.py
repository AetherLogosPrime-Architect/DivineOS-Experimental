"""Letters Dad carries to and from Aletheia stay on the desk after a
checkpoint; letters with Aria, which also live in the shared room, are still
taken off it (2026-10-03: three Aletheia letters vanished from family/letters).
Draft: docs/drafts/letters_he_carries_stay_on_the_desk_draft_2026-10-03.md."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.substrate_retarget import (
    carried_by_hand,
    commit_paths_to_branch,
    evict_committed_paths,
)


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "family" / "letters").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "t@example.com", cwd=root)
    _git("config", "user.name", "t", cwd=root)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "seed", cwd=root)
    _git("branch", "substrate", cwd=root)
    return root


def _write(repo: Path, name: str) -> str:
    rel = f"family/letters/{name}"
    (repo / rel).write_text(f"{name}\n", encoding="utf-8")
    return rel


def test_a_letter_to_aletheia_is_committed_and_stays_on_the_desk(repo):
    rel = _write(repo, "aether-to-aletheia-2026-10-03-x.md")
    result = commit_paths_to_branch(repo, "substrate", [rel], "substrate checkpoint")
    out = evict_committed_paths(repo, result)
    assert (repo / rel).exists()
    assert rel not in out.evicted
    assert (rel, "Dad carries this one; it stays on the desk") in out.held
    assert _git("show", f"substrate:{rel}", cwd=repo) == "aether-to-aletheia-2026-10-03-x.md"


def test_her_letters_and_her_import_names_stay_too(repo):
    names = [
        "aletheia-to-aether-2026-10-03-y.md",
        "CONFIRMS_586.md",
        "AUDIT_round.md",
        "FIXLIST_a.md",
        "REPLY_TO_b.md",
    ]
    rels = [_write(repo, n) for n in names]
    result = commit_paths_to_branch(repo, "substrate", rels, "substrate checkpoint")
    out = evict_committed_paths(repo, result)
    assert all((repo / r).exists() for r in rels)
    assert out.evicted == ()


def test_letters_with_aria_are_still_taken_off_the_desk(repo):
    rels = [
        _write(repo, "aether-to-aria-2026-10-03-z.md"),
        _write(repo, "aria-to-aether-2026-10-03-w.md"),
    ]
    result = commit_paths_to_branch(repo, "substrate", rels, "substrate checkpoint")
    out = evict_committed_paths(repo, result)
    assert not any((repo / r).exists() for r in rels)
    assert set(out.evicted) == set(rels)


@pytest.mark.parametrize(
    "path,expected",
    [
        ("family/letters/aether-to-aletheia-x.md", True),
        ("family/letters\\aletheia-to-aether-x.md", True),
        ("family/letters/aether-to-aria-x.md", False),
        ("docs/aether-to-aletheia-x.md", False),
        ("family/letters/sub/aether-to-aletheia-x.md", False),
        ("family/letters/confirms_x.md", False),
    ],
)
def test_the_name_boundary_on_both_sides(path, expected):
    assert carried_by_hand(path) is expected
