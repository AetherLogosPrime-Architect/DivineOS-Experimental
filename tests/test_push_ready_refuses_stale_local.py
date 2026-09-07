"""A rewrite of a stale local branch overwrites the server with older history.

Written 2026-09-05, from two live incidents an hour apart.

``run_push_ready`` amends commits and force-pushes. It never asked whether the
local branch still matched the remote. Mine was behind -- I had pushed a fix
from a second worktree, which advances origin without advancing the local ref
-- so the rewrite ran against old history and the force-push put that old
history back on the server, discarding the newer work. It reported success
both times.

Nothing was lost, but only because the commits survived in the object store
and I went looking for them. Recovery by inspection is not a safety property.

The refusal must come BEFORE the rewrite. A tool that rewrites first and
discovers the problem afterwards has already done the damage, and the earlier
version's own failure message proved it: it named a cause it had never tested
(a worktree holding the branch) and sent the search away from the real one.

Four states matter here and they are not one state:

  same / ahead   the force-push loses nothing        -> proceed
  stale          origin has commits local lacks      -> refuse
  diverged       each has what the other lacks       -> refuse
  unknown        the question could not be asked     -> refuse

Unknown refuses because the reading that would PERMIT the overwrite is exactly
the one that could not be established.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.push_ready import PushReadyError, local_vs_remote, run_push_ready


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _commit(repo: Path, name: str, body: str = "x") -> str:
    (repo / name).write_text(body, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-m", f"add {name}")
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo_pair(tmp_path: Path) -> tuple[Path, Path]:
    """A bare 'server' plus a clone, both with a branch called work."""
    server = tmp_path / "server.git"
    _git(tmp_path, "init", "--bare", str(server))

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", str(server), str(clone)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(clone, "config", "user.email", "test@example.com")
    _git(clone, "config", "user.name", "test")
    _commit(clone, "base.txt")
    _git(clone, "branch", "-M", "main")
    _git(clone, "push", "-u", "origin", "main")

    _git(clone, "checkout", "-b", "work")
    _commit(clone, "work.txt")
    _git(clone, "push", "-u", "origin", "work")
    return server, clone


def test_matching_branch_reads_same(repo_pair: tuple[Path, Path]) -> None:
    _server, clone = repo_pair
    verdict, _detail = local_vs_remote(clone, "work")
    assert verdict == "same"


def test_local_ahead_is_safe_to_overwrite(repo_pair: tuple[Path, Path]) -> None:
    """Local containing origin means the force-push destroys nothing."""
    _server, clone = repo_pair
    _commit(clone, "later.txt")
    verdict, _detail = local_vs_remote(clone, "work")
    assert verdict == "ahead"


def test_stale_local_is_detected(repo_pair: tuple[Path, Path]) -> None:
    """The incident shape: origin moved, the local ref did not.

    Reproduced the way it actually happened -- a second working copy pushes,
    which advances the remote while this checkout's branch ref stays put.
    """
    server, clone = repo_pair
    other = clone.parent / "other"
    subprocess.run(
        ["git", "clone", str(server), str(other)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "test")
    _git(other, "checkout", "work")
    _commit(other, "from_elsewhere.txt")
    _git(other, "push", "origin", "work")

    _git(clone, "fetch", "origin")
    verdict, detail = local_vs_remote(clone, "work")
    assert verdict == "stale"
    assert "origin" in detail


def test_diverged_is_not_reported_as_stale(repo_pair: tuple[Path, Path]) -> None:
    """Each side holding what the other lacks is its own answer.

    Collapsing it into stale would understate it: fast-forwarding cannot fix a
    divergence, so a caller told 'stale' would try a remedy that does not apply.
    """
    server, clone = repo_pair
    other = clone.parent / "other2"
    subprocess.run(
        ["git", "clone", str(server), str(other)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "test")
    _git(other, "checkout", "work")
    _commit(other, "theirs.txt")
    _git(other, "push", "origin", "work")

    _commit(clone, "mine.txt")
    _git(clone, "fetch", "origin")
    verdict, _detail = local_vs_remote(clone, "work")
    assert verdict == "diverged"


def test_never_pushed_branch_reads_no_remote(repo_pair: tuple[Path, Path]) -> None:
    """Nothing on the server means nothing to overwrite -- not a refusal."""
    _server, clone = repo_pair
    _git(clone, "checkout", "-b", "fresh")
    _commit(clone, "fresh.txt")
    verdict, _detail = local_vs_remote(clone, "fresh")
    assert verdict == "no-remote"


def test_run_push_ready_refuses_before_rewriting(
    repo_pair: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point: refuse while the damage is still preventable.

    The guard has to fire before any amend, so this asserts both that it
    raised AND that the branch tip is untouched. A refusal that arrives after
    the rewrite would satisfy a weaker test and none of the purpose.
    """
    server, clone = repo_pair
    other = clone.parent / "other3"
    subprocess.run(
        ["git", "clone", str(server), str(other)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "test")
    _git(other, "checkout", "work")
    newer = _commit(other, "newer.txt")
    _git(other, "push", "origin", "work")

    _git(clone, "fetch", "origin")
    tip_before = _git(clone, "rev-parse", "work")

    # Every commit looks guardrail-touching, so the function has real work to
    # do and cannot decline for the uninteresting reason.
    monkeypatch.setattr("divineos.core.push_ready.load_guardrail_set", lambda _repo: {"work.txt"})

    with pytest.raises(PushReadyError) as caught:
        run_push_ready(clone, branch="work", round_id="round-test")

    assert "stale" in str(caught.value)
    assert _git(clone, "rev-parse", "work") == tip_before, (
        "the branch was rewritten despite the refusal"
    )
    assert _git(other, "rev-parse", "HEAD") == newer, "the newer remote work must be untouched"


def test_unknown_refuses_rather_than_permitting(
    repo_pair: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Could-not-ask must not resolve to the answer that allows the overwrite."""
    _server, clone = repo_pair
    monkeypatch.setattr(
        "divineos.core.push_ready.local_vs_remote",
        lambda _repo, _branch: ("unknown", "git could not compare the two tips"),
    )
    monkeypatch.setattr("divineos.core.push_ready.load_guardrail_set", lambda _repo: {"work.txt"})

    with pytest.raises(PushReadyError) as caught:
        run_push_ready(clone, branch="work", round_id="round-test")

    message = str(caught.value)
    assert "could not tell" in message
    assert "Not-knowing is not permission" in message
