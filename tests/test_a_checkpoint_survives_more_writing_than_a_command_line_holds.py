"""The substrate checkpoint must not die of having too much substrate.

2026-09-21. The compaction cycle crashed at the first step with WinError 206 --
"the filename or extension is too long" -- which is what Windows says when a
command line exceeds its limit. Nothing was too long. There were simply more
substrate files than fit in one command, because every letter and dream written
since the last checkpoint gets named on that line, and the names are sentences.

THE SHAPE IS WHY IT MATTERS MORE THAN THE BUG. The failure scales with how much
writing exists. It cannot happen in a small test, it cannot happen early, and
it arrives on the day with the most unsaved work -- the checkpoint stops being
able to save precisely as the amount it is saving becomes worth saving. A
mechanism whose reliability falls as its subject grows is worse than no
mechanism, because the promise held for months before it broke.

CONTROLS IN BOTH DIRECTIONS. The scaling test would pass on the broken code if
the sample were small, so it carries a control proving the old argument-list
form genuinely dies at this size. And the ordinary small case still runs, so a
fix that broke everyday commits could not hide behind the large one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.substrate_retarget import commit_paths_to_branch


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "dreams").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "t@example.com", cwd=root)
    _git("config", "user.name", "t", cwd=root)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "seed", cwd=root)
    _git("branch", "substrate", cwd=root)
    return root


def _write_many(repo: Path, count: int) -> list[str]:
    """Substrate-shaped names: long, dated, slugged, one sentence each."""
    paths = []
    for i in range(count):
        name = (
            f"dreams/{i:04d}-the-house-where-every-alarm-was-ringing-"
            f"somewhere-else-and-nobody-had-the-key-{i:04d}.md"
        )
        (repo / name).write_text(f"entry {i}\n", encoding="utf-8")
        paths.append(name)
    return paths


def test_a_checkpoint_with_more_paths_than_one_command_line_holds_still_commits(repo):
    paths = _write_many(repo, 500)
    assert sum(len(p) for p in paths) > 40_000, (
        "the sample is too small to exercise the limit this test exists for"
    )

    result = commit_paths_to_branch(repo, "substrate", paths, "substrate checkpoint")

    assert result is not None, "the checkpoint reported nothing to commit"
    landed = _git("ls-tree", "-r", "--name-only", result.commit, cwd=repo).splitlines()
    assert set(paths) <= set(landed), "files were named to the checkpoint and did not land"


def test_the_argument_list_form_really_does_die_at_this_size(repo):
    """The control. Without it, the test above passes on the broken code.

    This asserts the PLATFORM refuses, not that our code does -- so if a future
    platform raises its limit, this fails loudly and says the scaling test has
    stopped measuring anything, rather than quietly going green forever.
    """
    paths = _write_many(repo, 400)
    with pytest.raises((OSError, subprocess.SubprocessError)):
        subprocess.run(
            ["git", "update-index", "--add", "--remove", "--", *paths],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )


def test_an_ordinary_small_checkpoint_still_lands(repo):
    """A fix for the large case that broke the everyday one would be no fix."""
    (repo / "dreams" / "one.md").write_text("just the one\n", encoding="utf-8")

    result = commit_paths_to_branch(repo, "substrate", ["dreams/one.md"], "substrate checkpoint")

    assert result is not None
    assert _git("rev-parse", f"{result.commit}:dreams/one.md", cwd=repo)


def test_nothing_to_commit_is_still_distinct_from_committed(repo):
    """Two calls, same content. The second must say nothing changed rather than
    writing a commit that claims work happened."""
    (repo / "dreams" / "one.md").write_text("just the one\n", encoding="utf-8")

    first = commit_paths_to_branch(repo, "substrate", ["dreams/one.md"], "checkpoint")
    second = commit_paths_to_branch(repo, "substrate", ["dreams/one.md"], "checkpoint")

    assert first is not None
    assert second is None, "an unchanged tree produced a commit saying work landed"
