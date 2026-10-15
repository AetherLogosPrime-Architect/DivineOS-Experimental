"""The checkout says how far behind origin/main it is.

Found 2026-10-12: Aria's live checkout was 23 behind and mine 11, and a stale copy
ran stale rules (no silence rule, a retired hook still wired) with nobody told.
Real git repositories throughout; the instrument is proven to see a known gap
before an absence is believed.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from divineos.core import checkout_behind_main as cb


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
    )


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)


def _world(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A bare origin on main, a clone that is current, and a second clone to advance main."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True, capture_output=True)
    _git(seed, "checkout", "-q", "-b", "main")
    _commit(seed, "first")
    _git(seed, "push", "-q", "origin", "main")
    mine = tmp_path / "mine"
    subprocess.run(["git", "clone", "-q", str(origin), str(mine)], check=True, capture_output=True)
    return origin, seed, mine


_ADVANCED = [0]


def _advance(seed: Path, n: int) -> None:
    for _ in range(n):
        _ADVANCED[0] += 1
        _commit(seed, f"later{_ADVANCED[0]}")
    _git(seed, "push", "-q", "origin", "main")


def test_a_current_checkout_says_so(tmp_path):
    _, _, mine = _world(tmp_path)
    assert cb.measure(mine) == (0, 0, True)
    assert "current with origin/main" in cb.report(mine)


def test_control_the_instrument_counts_a_known_gap_exactly(tmp_path):
    _, seed, mine = _world(tmp_path)
    _advance(seed, 3)
    assert cb.measure(mine) == (3, 0, True)


def test_a_few_behind_is_a_line_and_many_behind_is_loud(tmp_path):
    _, seed, mine = _world(tmp_path)
    _advance(seed, 2)
    few = cb.report(mine)
    assert "2 commit(s) behind" in few and "BEHIND" not in few
    _advance(seed, 5)
    many = cb.report(mine)
    assert "7 commits BEHIND origin/main" in many and "git merge origin/main" in many


def test_local_work_ahead_is_not_counted_as_behind(tmp_path):
    _, _, mine = _world(tmp_path)
    _commit(mine, "mine1")
    _commit(mine, "mine2")
    assert cb.measure(mine) == (0, 2, True)


def test_a_folder_git_cannot_read_is_could_not_measure_never_current():
    # The system temp folder, not pytest's: that one sits inside this repository.
    with tempfile.TemporaryDirectory() as plain:
        assert cb.measure(Path(plain), fetch=False) is None
        out = cb.report(Path(plain))
    assert "could not measure" in out and "current with" not in out


def test_a_failed_fetch_is_named_and_measured_against_the_last_fetch(tmp_path):
    _, seed, mine = _world(tmp_path)
    _advance(seed, 1)
    # Origin unreachable: the fetch fails, the old remote ref remains.
    _git(mine, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    got = cb.measure(mine)
    assert got == (0, 0, False)
    assert "the fetch failed" in cb.report(mine)
