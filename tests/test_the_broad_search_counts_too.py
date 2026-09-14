"""The gate that asks me to look could not see me looking.

2026-09-14. It refused twenty-six times in one session, more than every other
gate combined, and the refusal-reader built that same morning named it as the
largest source of friction before I understood why. Two separate breaks, and
between them the gate was unsatisfiable by any search of any shape — which is
why a walk-record was its only working exit all day, and why I filed four of
those purely to pass one door.

BREAK ONE — the broad search failed where the narrow one passed. The rule was
"contains the docs segment AND ends in the markdown suffix": two proxies doing
one job, whose conjunction excluded the design tree itself. A sweep of the
whole shelf missed; opening one named file on it passed. Backwards against the
module's own header, which argues that opening a file you already knew about is
not searching and that the searching is the cure.

BREAK TWO — the area check compared an ABSOLUTE class directory against the
RELATIVE paths the search tools record, so that disjunct could never match
either.

I ALREADY KNEW AND FILED IT WRONG, and this is the part worth keeping. The
neighbouring test file, written 2026-09-02, opens: *"I followed it twice in one
turn, with backslashes and then with forward slashes, concluded the path
matching was broken, and wrote that wrong cause into a decision record before
testing it."* The path matching WAS broken, in two ways. Twelve days ago I was
accidentally right and dismissed it as my own error; today I was confidently
wrong twice — telling Andrew, and writing into a commit, that a space in the
repository's folder name was the cause, because the refusal prints the path
chopped at that space. Both times the settling experiment was calling the
predicate directly, and it takes under a minute.

That earlier file pinned the block MESSAGE against the accepted tool set and
never touched the matcher. A fix that names its own generality applied to
exactly one case, for the fifth time this fortnight.

The refusals below are the load-bearing half: a gate loosened past its meaning
is worse than one that refuses too much.
"""

from __future__ import annotations

import pytest

from divineos.core.verify_before_build_signal import _is_in_design_tree, _same_area

REPO = "C:/DIVINE OS/DivineOS-Experimental-Aria-new"
CORE = f"{REPO}/src/divineos/core"


class TestTheSweepThatUsedToMiss:
    """The case that cost the day: searching the whole design tree."""

    def test_the_bare_design_directory_counts(self):
        # This exact call was made repeatedly and read as did-not-look.
        assert _is_in_design_tree("docs")

    def test_a_single_design_file_still_counts(self):
        assert _is_in_design_tree("docs/signal-based-gates-design-2026-06-16.md")

    def test_a_design_tree_nested_under_a_worktree_counts(self):
        assert _is_in_design_tree("a/b/docs/anything.md")

    def test_a_trailing_separator_does_not_change_the_answer(self):
        assert _is_in_design_tree("docs/")

    @pytest.mark.parametrize("path", ["mydocs/x.md", "src/docsy/z.md", "adocs"])
    def test_the_word_must_be_a_whole_segment(self, path):
        # A path merely CONTAINING the letters is not the design tree. The
        # widening is one condition over a set, not a substring search.
        assert not _is_in_design_tree(path)

    @pytest.mark.parametrize("path", ["src/divineos/core", "tests/test_x.py", ""])
    def test_everything_else_is_still_refused(self, path):
        assert not _is_in_design_tree(path)


class TestTheAbsoluteAgainstRelativeBreak:
    """Break two, found one refusal after break one was fixed — and only
    because fixing the first left this one still refusing."""

    def test_an_absolute_area_matches_the_relative_path_actually_recorded(self):
        assert _same_area(CORE, "src/divineos/core")

    def test_it_matches_a_search_of_one_file_inside_that_area(self):
        # The case both of my first two attempts failed. A tail comparison
        # missed it because the file carries one segment more than its
        # directory; a containment test missed it because the absolute prefix
        # makes the directory trail the longer of the two. Two plausible,
        # confidently wrong fixes inside the repair of a plausible,
        # confidently wrong rule — caught by running them, not reading them.
        assert _same_area(CORE, "src/divineos/core/verify_before_build_signal.py")

    def test_it_matches_a_file_deeper_inside(self):
        assert _same_area(CORE, "src/divineos/core/sub/thing.py")

    def test_it_works_when_both_sides_are_relative(self):
        assert _same_area("src/divineos/core", "src/divineos/core/x.py")

    def test_an_unrelated_area_is_refused(self):
        assert not _same_area(CORE, "tests/test_something.py")

    def test_a_sibling_area_is_refused(self):
        assert not _same_area(CORE, "src/divineos/cli/commands.py")

    @pytest.mark.parametrize("a,b", [("", "src"), (CORE, ""), ("", "")])
    def test_an_empty_side_is_not_a_match(self, a, b):
        # Could-not-tell must never arrive wearing the face of a match, in
        # the direction that would let a gate pass on nothing.
        assert not _same_area(a, b)


class TestWhatDidNotMove:
    """A gate loosened past its meaning stops meaning anything. These pin the
    parts the repair deliberately left alone."""

    def test_source_paths_are_not_design_documents(self):
        # The two rules stay separate: being in the source tree is not
        # evidence of having consulted the design tree.
        assert not _is_in_design_tree("src/divineos/core/verify_before_build_signal.py")

    def test_the_design_rule_does_not_answer_area_questions(self):
        # and the converse — a design-tree path is not automatically the same
        # area as arbitrary source.
        assert not _same_area("docs", "src/divineos/core")
