"""The board's verdict comes from the checkout, and now the board says so.

Aria and I have each reported a board reading to the other from a different
working tree, more than once, and both readings were honest. The trouble is
that the page printed the verdict and not the rulebook, so a green earned under
a widened station check read exactly like a green earned without one. I named
it to her on 2026-09-01 and again on 2026-09-10, both times as a finding I had
not repaired.

It cannot be repaired by making the reading independent of the checkout. The
station rules ARE code, and the code that runs is whichever copy the tree
carries; fetching them from somewhere else only moves the variance into the
fetch. What was actually missing is the disclosure, and that is what these
tests hold: the reading says which rulebook spoke, and an unanswerable question
is reported as unanswered rather than as agreement.

Every test here builds a real repository on disk. The earlier version of this
kind of check could only ever run against the tree the suite was sitting in,
which meant two of its three answers were never observed once.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core.build_flow import Status, judging_code_provenance

RULES = "rules.py"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, check=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A small repository with a main branch carrying one rules file."""
    if shutil.which("git") is None:
        pytest.skip("no git on this machine — could-not-look, not a pass")

    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / RULES).write_text("STATION_FLOOR = 2\n", encoding="utf-8")
    _git(tmp_path, "add", RULES)
    _git(tmp_path, "commit", "-q", "-m", "rules")
    return tmp_path


def test_the_same_rules_as_main_says_so_plainly(repo: Path) -> None:
    status, detail = judging_code_provenance(
        main_ref="main", module_path=repo / RULES, tracked_path=RULES
    )
    assert status is Status.SATISFIED
    assert "same station rules" in detail


def test_a_tree_carrying_its_own_rules_is_told_another_tree_may_disagree(repo: Path) -> None:
    """The live case. This is the state my own checkout has been in all week."""
    (repo / RULES).write_text("STATION_FLOOR = 3  # widened here, not on main\n", encoding="utf-8")

    status, detail = judging_code_provenance(
        main_ref="main", module_path=repo / RULES, tracked_path=RULES
    )
    assert status is Status.MISSING
    assert "THIS checkout" in detail
    assert "may read the same pull requests differently" in detail


def test_an_unreadable_shared_copy_is_unknown_and_never_agreement(repo: Path) -> None:
    """The one that matters most, and the one a two-valued answer gets wrong.

    A branch that does not exist, a repository without the file, a git that
    will not run — every one of those means the question was not answered. If
    any of them returned the same value as a match, the page would print
    agreement it had never established, which is the whole defect family this
    module was written against.
    """
    status, detail = judging_code_provenance(
        main_ref="no-such-branch", module_path=repo / RULES, tracked_path=RULES
    )
    assert status is Status.CANNOT_CHECK
    assert "not agreed" in detail


def test_the_three_answers_are_actually_three(repo: Path) -> None:
    """Control. Without this, every assertion above survives a function that
    has quietly collapsed into always returning the same thing."""
    same = judging_code_provenance(main_ref="main", module_path=repo / RULES, tracked_path=RULES)[0]
    missing_ref = judging_code_provenance(
        main_ref="no-such-branch", module_path=repo / RULES, tracked_path=RULES
    )[0]
    (repo / RULES).write_text("STATION_FLOOR = 99\n", encoding="utf-8")
    differs = judging_code_provenance(
        main_ref="main", module_path=repo / RULES, tracked_path=RULES
    )[0]

    assert len({same, missing_ref, differs}) == 3
