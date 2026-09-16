"""The candidate list must be short, honest, and loud about what it cannot see.

Aria is building a stop at the door to main that refuses a branch until someone
has looked at whether it duplicates work already sitting on a bench. That door
is hers. This is my half: the list it puts in front of the person, so the
question gets answered by looking rather than from memory.

The risk in a list like this is not that it is wrong. It is that it goes quiet
and the quiet gets read as an all-clear. A shared filename is a weak signal by
construction, and the case it cannot see -- two branches solving one problem in
different files -- is precisely how the duplicate that prompted all of this was
built. So the instrument is blind in the direction of the incident it exists to
catch, and the tests below pin that the blindness is stated rather than hidden.

The assertions run against synthetic branches rather than the live repository.
That is deliberate: a test reading real branches would pass or fail on whatever
happens to be checked out, which makes it a report rather than a check.

These are also the board's first tests. It shipped without any, which is worth
saying out loud rather than quietly fixing.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from sort_the_branch_board import Branch, neighbours, sweep_signatures  # noqa: E402


def _branch(name: str, *code_files: str, writing: tuple[str, ...] = ()) -> Branch:
    return Branch(
        name=name,
        files=len(code_files) + len(writing),
        substrate=len(writing),
        commits=1,
        pr=None,
        code_files=frozenset(code_files),
        substrate_files=frozenset(writing),
    )


def test_branches_sharing_files_are_offered_most_shared_first() -> None:
    """Ordering is the whole value: the reader stops after the first few rows."""
    mine = _branch("mine", "a.py", "b.py", "c.py")
    rows = neighbours(
        [
            mine,
            _branch("one_shared", "a.py", "z.py"),
            _branch("three_shared", "a.py", "b.py", "c.py"),
            _branch("two_shared", "a.py", "b.py"),
        ],
        "mine",
    )
    assert [name for name, _ in rows] == ["three_shared", "two_shared", "one_shared"]
    assert [count for _, count in rows] == [3, 2, 1]


def test_a_branch_is_never_its_own_candidate() -> None:
    """Every file it touches, it shares with itself.

    Left in, the branch under review would always top its own list -- the same
    self-comparison that made the push gate's survival check useless.
    """
    mine = _branch("mine", "a.py")
    assert [name for name, _ in neighbours([mine, _branch("other", "a.py")], "mine")] == ["other"]


def test_no_shared_file_returns_nothing_and_that_is_not_an_all_clear() -> None:
    """The dangerous case, pinned as a limit rather than a result.

    Two branches solving the same problem in different files produce exactly
    this empty list. The emptiness is asserted so the behaviour is deliberate,
    and the docstring is asserted so the caller is never handed the silence
    without the warning attached to it.
    """
    rows = neighbours(
        [_branch("mine", "a.py"), _branch("elsewhere", "totally_different.py")],
        "mine",
    )
    assert rows == []
    doc = (neighbours.__doc__ or "").lower()
    assert "empty list means no shared file" in doc
    assert "does not mean no overlap" in doc


def test_writing_only_branches_do_not_become_candidates() -> None:
    """Substrate is read, not diffed, so shared letters are not shared work.

    Without this, every branch an automatic checkpoint had swept would share
    hundreds of letters with every other and the list would be unreadable --
    which is the failure that matters, because a list nobody reads sends the
    door's question back to being answered from memory.
    """
    mine = Branch(
        name="mine", files=2, substrate=1, commits=1, pr=None, code_files=frozenset({"a.py"})
    )
    swept = Branch(
        name="swept", files=200, substrate=200, commits=1, pr=None, code_files=frozenset()
    )
    assert neighbours([mine, swept], "mine") == []


def test_the_list_is_capped_so_it_stays_short_enough_to_read() -> None:
    """A list longer than anyone reads is the same as no list."""
    mine = _branch("mine", "a.py")
    others = [_branch(f"other{i:02d}", "a.py") for i in range(40)]
    assert len(neighbours([mine, *others], "mine")) == 8


def test_shared_writing_is_kept_and_reported_apart_from_the_ranking() -> None:
    """Aria's amendment: exclude it from the ranking, do not discard it.

    Two branches sharing swept letters and no code are not solving one problem.
    They are evidence the checkpoint was in both places -- the defect that cost
    a whole session. Wrong answer to the duplicate question is not no
    information, and the first version of this threw it away for being the
    wrong answer.
    """
    mine = _branch("mine", "a.py", writing=("family/letters/x.md", "family/letters/y.md"))
    swept = _branch("swept", "z.py", writing=("family/letters/x.md", "family/letters/y.md"))
    assert neighbours([mine, swept], "mine") == []
    assert sweep_signatures([mine, swept], "mine") == [("swept", 2)]


def test_a_branch_sharing_code_is_not_also_a_sweep_signature() -> None:
    """The two lists answer different questions and must not double-report.

    A branch already offered as a duplicate candidate is being looked at.
    Listing it again under a heading that says 'this is not a relationship'
    would contradict the list above it.
    """
    mine = _branch("mine", "a.py", writing=("family/letters/x.md",))
    both = _branch("both", "a.py", writing=("family/letters/x.md",))
    assert [n for n, _ in neighbours([mine, both], "mine")] == ["both"]
    assert sweep_signatures([mine, both], "mine") == []


def test_the_probe_can_actually_fail() -> None:
    """Prove the function discriminates, so an empty result carries meaning.

    Every assertion about emptiness above is satisfied by a function that
    always returns nothing. Pairing the two directions is what makes a silence
    a finding rather than a broken instrument reporting one.
    """
    shared = [_branch("mine", "a.py"), _branch("other", "a.py")]
    unshared = [_branch("mine", "a.py"), _branch("other", "b.py")]
    assert neighbours(shared, "mine"), "the list found nothing where files are shared"
    assert not neighbours(unshared, "mine"), "the list found something where no file is shared"
    assert neighbours(shared, "no-such-branch") == []
