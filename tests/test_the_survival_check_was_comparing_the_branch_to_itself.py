"""The right property was already tested, against a caller that does not ship.

``check_branch_scope`` refuses a push carrying substrate files on a code branch
and tells you to rebuild against main. Immediately BEFORE that instruction it
prints whether any of those files exist nowhere else -- because the instruction
is fatal for exactly those, and ``only_here`` exists because following the
refusal literally once would have destroyed four dreams and a letter.

That reassurance was false every time the gate ran for real. The pre-push hook
passes each ref's COMMIT ID. ``rev-parse --abbrev-ref`` on a bare commit id
returns an empty string, so the name-based exclusion set came out empty, the
branch's own ref stayed among the refs consulted, every blob matched itself on
the first comparison, and the gate printed that nothing was unique -- over a
dream that existed on exactly one ref in this repository.

WHAT MAKES THIS WORTH ITS OWN FILE. A test for this precise property was
already written: test_branch_scope_only_here.py has
``test_the_branch_being_checked_does_not_count_as_somewhere_else``, whose
docstring calls it "the bug a careless version would have" and says letting the
branch prove its own files live elsewhere "makes the check pass every single
time and print the one reassurance that costs the most." It is exactly right and
it passed throughout, because it names the branch the way a person would and
production names it the way a hook does.

So the gap was never the property. It was that the property was only ever asked
in one dialect, and the dialect that ships was the broken one. These tests pin
the AGREEMENT between the two spellings -- a question neither caller can answer
alone, and the only question whose answer changes when the defect is present.

Caught 2026-09-15 on a live push, by checking a file the gate had just called
safe. A self-comparison has no tell: it returns instantly, agrees completely,
and looks exactly like a clean result.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_branch_scope import _other_refs  # noqa: E402


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def _current_branch() -> str:
    name = _git("rev-parse", "--abbrev-ref", "HEAD")
    if name == "HEAD":
        pytest.skip("detached HEAD; there is no branch name to compare a commit id against")
    return name


def test_a_branch_and_its_commit_id_exclude_the_same_refs() -> None:
    """The two spellings of one branch must agree about what counts as OTHER.

    This fails on the defect and passes on the fix without depending on which
    answer is correct -- only on the fact that naming the same branch two ways
    cannot change who its neighbours are.
    """
    by_name = set(_other_refs(_current_branch()))
    by_commit = set(_other_refs(_git("rev-parse", "HEAD")))
    assert by_name == by_commit, (
        "_other_refs disagrees about the same branch depending on whether it is "
        "named or given as a commit id. Production passes a commit id, so the "
        "disagreeing answer is the one that ships. Seen by one and not the "
        f"other: {sorted(by_name ^ by_commit)[:5]}"
    )


def test_the_branch_under_check_is_never_among_its_own_others() -> None:
    """Whichever way it is spelled, a branch may not prove its own files survive.

    The existing suite asserts this for a branch name. The addition here is the
    commit-id spelling, which is the one the pre-push hook uses.
    """
    branch = _current_branch()
    own = f"refs/heads/{branch}"
    for label, spelling in (("name", branch), ("commit id", _git("rev-parse", "HEAD"))):
        assert own not in _other_refs(spelling), (
            f"called by {label}, the branch's own ref is among the refs used to "
            "decide whether its files exist anywhere else. Every blob then "
            "matches itself and the gate reports nothing is unique -- directly "
            "above the instruction to rebuild, which deletes them."
        )


def test_an_unidentifiable_ref_reports_could_not_look() -> None:
    """A failed lookup must not degrade into a confident all-clear.

    This is the discipline the module states plainly and the defect broke: the
    name lookup failed, and the failure was absorbed into an empty exclusion set
    rather than reported. An empty return is how the caller is told the scan did
    not happen.
    """
    assert _other_refs("refs/heads/branch-that-does-not-exist-anywhere") == [], (
        "a ref that cannot be resolved produced a list of refs to compare "
        "against. Comparing against them answers a question about a branch "
        "nobody could identify, and the caller prints the answer as fact."
    )


def test_the_probe_can_actually_fail() -> None:
    """Prove the scan finds refs at all, so an empty result stays meaningful.

    Every assertion above is satisfied by ``_other_refs`` returning nothing for
    every input. This repository has many refs, so nothing-for-everything means
    the function is broken rather than that the branch is alone in the world.
    """
    assert _other_refs(_current_branch()), (
        "_other_refs returned no refs at all for a live branch in a repository "
        "that has many. Every check above would pass vacuously on that, so an "
        "empty result here is a broken instrument, not a clean one."
    )
