"""Tests for committing substrate to a named branch without touching HEAD.

Real repositories throughout. The defect under repair is entirely about which
ref a commit lands on and what the working tree looks like afterwards, so a
mocked git would test the mock and nothing else.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.substrate_retarget import (
    RetargetRefused,
    commit_paths_to_branch,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    (r / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "-m", "seed")
    _git(r, "branch", "substrate")
    _git(r, "checkout", "-q", "-b", "work")
    return r


def test_commits_to_named_branch_not_head(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    head_before = _git(repo, "rev-parse", "HEAD")

    result = commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    assert result is not None
    assert _git(repo, "rev-parse", "refs/heads/substrate") == result.commit
    assert _git(repo, "rev-parse", "HEAD") == head_before, "HEAD must not move"
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "work"


def test_working_tree_and_index_are_untouched(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    (repo / "wip.py").write_text("x = 1\n", encoding="utf-8")

    commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    # Both files are still present and still untracked on the occupant's branch.
    assert (repo / "letter.md").read_text(encoding="utf-8") == "hello\n"
    assert (repo / "wip.py").read_text(encoding="utf-8") == "x = 1\n"
    porcelain = _git(repo, "status", "--porcelain")
    assert "?? wip.py" in porcelain
    assert _git(repo, "diff", "--cached", "--name-only") == "", "real index must stay clean"


def test_work_in_progress_does_not_ride_along(repo: Path) -> None:
    """The whole defect, from the other direction.

    Naming the substrate branch correctly still sends half-finished work there
    if the commit is built from `add -A`. Only the declared paths may travel.
    """
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    (repo / "half_finished.py").write_text("def broken(\n", encoding="utf-8")

    result = commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    assert result is not None
    landed = _git(repo, "show", "--name-only", "--format=", result.commit).split()
    assert landed == ["letter.md"]


def test_missing_branch_refuses_and_commits_nothing(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    head_before = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(RetargetRefused, match="does not exist"):
        commit_paths_to_branch(repo, "no-such-branch", ["letter.md"], "m")

    assert _git(repo, "rev-parse", "HEAD") == head_before
    assert _git(repo, "status", "--porcelain") != "", "the file is still uncommitted"


def test_no_change_makes_no_commit(repo: Path) -> None:
    """An empty commit would make the log assert work that did not happen."""
    tip_before = _git(repo, "rev-parse", "refs/heads/substrate")

    assert commit_paths_to_branch(repo, "substrate", ["seed.txt"], "m") is None
    assert _git(repo, "rev-parse", "refs/heads/substrate") == tip_before


def test_empty_path_list_is_a_noop(repo: Path) -> None:
    tip_before = _git(repo, "rev-parse", "refs/heads/substrate")
    assert commit_paths_to_branch(repo, "substrate", [], "m") is None
    assert _git(repo, "rev-parse", "refs/heads/substrate") == tip_before


def test_does_not_seed_from_head(repo: Path) -> None:
    """Seeding the scratch index from HEAD would carry the occupant's branch
    across onto substrate -- the same contamination pointed the other way."""
    (repo / "only_on_work.txt").write_text("work\n", encoding="utf-8")
    _git(repo, "add", "only_on_work.txt")
    _git(repo, "commit", "-q", "-m", "work-only commit")

    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    result = commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    assert result is not None
    files = _git(repo, "ls-tree", "-r", "--name-only", result.commit).split()
    assert "only_on_work.txt" not in files
    assert sorted(files) == ["letter.md", "seed.txt"]


def test_deleted_substrate_file_records_as_deleted(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    first = commit_paths_to_branch(repo, "substrate", ["letter.md"], "add")
    assert first is not None

    (repo / "letter.md").unlink()
    second = commit_paths_to_branch(repo, "substrate", ["letter.md"], "remove")

    assert second is not None
    files = _git(repo, "ls-tree", "-r", "--name-only", second.commit).split()
    assert "letter.md" not in files


def test_more_paths_than_fit_on_a_command_line(repo: Path) -> None:
    """The ceiling that stopped a learning checkpoint on 2026-09-17.

    Windows caps a command line at 32767 characters. Passing each substrate
    path as an argument put 342 of our letter filenames -- which run long on
    purpose -- at roughly 37k, and CreateProcess refused with a
    FileNotFoundError that reads like git is missing rather than like the
    invocation is too big.

    The names here are deliberately letter-shaped and long enough that the
    argument form would still fail, so this test fails against the old code
    rather than merely passing against the new.
    """
    letters = repo / "letters"
    letters.mkdir()
    names = [
        f"letters/aria-to-aether-2026-09-17-a-long-subject-line-of-the-kind-we-actually-write-{i:04d}.md"
        for i in range(400)
    ]
    for name in names:
        (repo / name).write_text("body\n", encoding="utf-8")

    assert sum(len(n) + 1 for n in names) > 32767, "names too short to exercise the ceiling"

    result = commit_paths_to_branch(repo, "substrate", names, "substrate: many letters")

    assert result is not None
    committed = _git(repo, "ls-tree", "-r", "--name-only", result.commit).split()
    assert len(committed) == len(names) + 1  # every letter, plus seed.txt
    assert names[0] in committed
    assert names[-1] in committed


def test_concurrent_branch_move_is_refused_not_clobbered(repo: Path) -> None:
    """The in-flight window, made explicit.

    If the substrate branch moves between our read and our write, the update
    must fail rather than discard whatever arrived.
    """
    from divineos.core import substrate_retarget as sr

    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    real_commit_tree = sr._git
    state = {"moved": False}

    def racing_git(
        root: Path,
        *args: str,
        env: dict[str, str] | None = None,
        stdin_data: str | None = None,
    ) -> str:
        # stdin_data forwarded, not dropped: the path list travels through the
        # pipe now, so a stand-in that swallowed it would build an empty index
        # and this test would pass for the wrong reason.
        #
        # The name follows substrate_retarget, where the merge picked
        # stdin_data over main's stdin. Not a free choice here: a double whose
        # signature disagrees with the real function is the failure this
        # comment already describes, arriving through the parameter list.
        out = real_commit_tree(root, *args, env=env, stdin_data=stdin_data)
        if args and args[0] == "commit-tree" and not state["moved"]:
            state["moved"] = True
            # Someone else advances substrate while we were building the tree.
            _git(repo, "branch", "-f", "substrate", "main")
            (repo / "other.txt").write_text("other\n", encoding="utf-8")
        return out

    sr._git = racing_git
    try:
        # substrate == main here, so force it somewhere else first to make the
        # move observable.
        _git(repo, "commit", "-q", "--allow-empty", "-m", "advance work")
        _git(repo, "branch", "-f", "substrate", "HEAD")
        with pytest.raises(RetargetRefused):
            commit_paths_to_branch(repo, "substrate", ["letter.md"], "m")
    finally:
        sr._git = real_commit_tree


def test_paths_do_not_travel_as_command_line_arguments(repo: Path) -> None:
    """The path list goes through the pipe, so a length limit cannot reach it.

    2026-09-17. This used to splat every declared substrate path as a separate
    argument, and Windows refuses a command line past a fixed length. With
    hundreds of letters and dreams declared, that line was too long and the
    weave died with an error about a filename being too long -- confusing,
    because no filename was.

    WHY THIS IS SHAPED AS A PROPERTY RATHER THAN A SIZE. The faithful
    reproduction needs enough files to exceed an operating-system limit, which
    means choosing a number to stand for that limit -- a literal with nothing
    linking it back to the fact it represents. That is the exact defect that
    cost two full suite runs on the night this was written, and putting it in
    the test for the fix would be remarkable.

    So this asserts what is true at ANY size on ANY platform: the paths are not
    in the argument list. It fails on the old code for the right reason and
    passes on the new one for the right reason, with no constant to go stale.

    WHAT IT DOES NOT PROVE, said because a green result would otherwise imply
    it: that git accepts this input form with these flags. No assertion about
    this code can establish a fact about another program. That evidence came
    from running the real weave end to end, separately, and the two must not be
    collapsed into one result.
    """
    from divineos.core import substrate_retarget as sr

    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    (repo / "second.md").write_text("also\n", encoding="utf-8")
    real_git = sr._git
    seen: list[tuple[tuple[str, ...], str | None]] = []

    def recording_git(
        root: Path,
        *args: str,
        env: dict[str, str] | None = None,
        stdin_data: str | None = None,
    ) -> str:
        if args and args[0] == "update-index":
            seen.append((args, stdin_data))
        return real_git(root, *args, env=env, stdin_data=stdin_data)

    sr._git = recording_git
    try:
        result = commit_paths_to_branch(repo, "substrate", ["letter.md", "second.md"], "m")
    finally:
        sr._git = real_git

    assert result is not None, "the commit must still land"
    assert seen, "update-index must still be the call that stages the paths"
    args, stdin_data = seen[0]

    for path in ("letter.md", "second.md"):
        assert path not in args, f"{path} still travels as a command-line argument"
        assert stdin_data is not None and path in stdin_data, f"{path} must arrive on stdin"

    # The separator is NUL, not newline: a newline is legal inside a filename,
    # so a newline-separated list would silently split such a path in two.
    assert chr(0) in stdin_data
    assert "-z" in args
    assert "--stdin" in args
