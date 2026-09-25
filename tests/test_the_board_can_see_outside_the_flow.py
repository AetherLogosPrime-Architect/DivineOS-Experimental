"""The branch verdict, checkable without a remote.

Andrew sees seventy branches; the board saw twelve, because it only reported
open requests. Four fifths of the estate was invisible to the instrument the
house uses to see its own work — which is why the pile felt unaddressable
rather than merely large. Deming: a queue nobody can see cannot be drained,
and no amount of inspection substitutes for the system observing itself.

These test the VERDICT, which is the part that decides what a reader does
next. It lived inside the git-shelling loop and was therefore only reachable
through a live remote, so the rule could only be checked by running the whole
board and squinting. It misfired once that way — sorting an archive into
unfinished work because it keyed on the branch NAME — and I caught it by eye.
Catching a thing by eye is not a mechanism.
"""

from __future__ import annotations

from divineos.cli.build_flow_commands import classify_branch


class TestNothingMissingMeansLanded:
    def test_no_unlanded_files_is_landed(self) -> None:
        assert classify_branch([]) == ("landed", 0)

    def test_landed_reports_no_code_count(self) -> None:
        """A landed branch has nothing owing, so a count would imply work."""
        verdict, count = classify_branch([])
        assert verdict == "landed"
        assert count == 0


class TestAnArchiveIsNotUnfinishedWork:
    """Substrate branches are supposed to sit there. Counting them as
    unfinished makes the estate look worse than it is, and a number that
    overstates trains the reader to ignore it."""

    def test_letters_only_is_substrate(self) -> None:
        verdict, _ = classify_branch(
            ["family/letters/a.md", "family/letters/b.md", "dreams/aether/1.md"]
        )
        assert verdict == "substrate"

    def test_docs_only_is_substrate(self) -> None:
        assert classify_branch(["docs/a.md", "exploration/b.md"])[0] == "substrate"

    def test_the_name_does_not_decide_it(self) -> None:
        """THE MISFIRE THIS IS FOR. The rule keyed on the branch name and sorted
        a branch called for substrate into unfinished work because the word sat
        in the wrong position. The classifier now never sees a name at all —
        it cannot make that mistake because it is not given the chance."""
        import inspect

        assert "name" not in inspect.signature(classify_branch).parameters


class TestRealCodeIsARealDecision:
    def test_one_source_file_is_carrying(self) -> None:
        assert classify_branch(["src/divineos/core/x.py"]) == ("carrying", 1)

    def test_the_count_is_code_only(self) -> None:
        """The number is what a reader weighs, so it counts the part that
        needs review — not the letters riding along beside it."""
        verdict, count = classify_branch(
            ["src/divineos/a.py", "tests/test_a.py", "family/letters/x.md", "docs/y.md"]
        )
        assert verdict == "carrying"
        assert count == 2

    def test_each_code_area_counts(self) -> None:
        verdict, count = classify_branch(
            ["src/a.py", "tests/b.py", "scripts/c.py", ".claude/hooks/d.sh"]
        )
        assert verdict == "carrying"
        assert count == 4

    def test_a_single_hook_beside_many_letters_still_carries(self) -> None:
        """The case that matters most: one real change buried in an archive.
        If the letters outvoted it, the branch would read as safe to ignore."""
        files = [f"family/letters/{i}.md" for i in range(200)] + [".claude/hooks/x.sh"]
        assert classify_branch(files) == ("carrying", 1)
