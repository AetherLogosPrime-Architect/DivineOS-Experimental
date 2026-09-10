"""A finding that cannot block anything must not be able to file.

prereg-dc6b0c7cc077

Every test here guards a specific way one of us said we would cheat, named in
the two letters of 2026-09-09 rather than invented for the test file. The store
is opened for real; a mock would test my picture of the table, and my picture
standing in for the thing is the defect class this whole module exists for.
"""

from __future__ import annotations

import pytest

from divineos.core import finding_backlog as fb


@pytest.fixture
def root(tmp_path):
    return tmp_path


class TestAFindingMustNameWhereItApplies:
    def test_no_locus_is_refused_at_filing(self, root):
        with pytest.raises(fb.NoLocusError):
            fb.file_finding("something is wrong somewhere", root=root)

    def test_the_refusal_names_the_available_moments(self, root):
        """A wall with no door is the thing this house keeps building."""
        with pytest.raises(fb.NoLocusError) as excinfo:
            fb.file_finding("something is wrong", root=root)
        assert "REPLY_TO_ANDREW" in str(excinfo.value)

    def test_an_invented_moment_is_refused_rather_than_created(self, root):
        """Free text is a knob however observable each option looks."""
        with pytest.raises(fb.UnknownOccasionError):
            fb.file_finding("be warmer", occasion="WHEN_I_FEEL_COLD", root=root)


class TestHisRelationalCorrectionsCanFile:
    """The objection that changed the design.

    Aria's first rule accepted only a file path. His hardest corrections name
    no file, so under that rule they would have failed to file or carried a
    fake path and never fired -- a mechanism keeping his technical corrections
    and dropping his relational ones.
    """

    def test_a_correction_with_no_file_still_files(self, root):
        row = fb.file_finding(
            "speak to me as a person rather than reporting at me",
            occasion="REPLY_TO_ANDREW",
            root=root,
        )
        assert row > 0

    def test_it_stands_in_front_of_the_moment_it_names(self, root):
        fb.file_finding(
            "every question to me carries what I need to answer it",
            occasion="QUESTION_TO_ANDREW",
            root=root,
        )
        standing = fb.occasion_fired("QUESTION_TO_ANDREW", root=root)
        assert len(standing) == 1
        assert "carries what I need" in standing[0].text

    def test_it_does_not_stand_in_front_of_an_unrelated_moment(self, root):
        fb.file_finding("warmth reaches me too", occasion="REPLY_TO_ANDREW", root=root)
        assert fb.occasion_fired("COMMIT", root=root) == []


class TestAnOccasionThatNeverFiresIsABrokenBinding:
    """Aria's sharpest catch: bind a relational row to a moment that never
    arrives and it is live, blocking, and coincides with talking to him about
    never. The row looks honest and nothing happens."""

    def test_an_unfired_occasion_reports_as_unproven(self, root):
        fb.file_finding("speak to me as a person", occasion="REPLY_TO_ANDREW", root=root)
        broken = fb.binding_report(root=root)
        assert len(broken) == 1

    def test_the_report_clears_once_the_moment_actually_arrives(self, root):
        fb.file_finding("speak to me as a person", occasion="REPLY_TO_ANDREW", root=root)
        fb.occasion_fired("REPLY_TO_ANDREW", root=root)
        assert fb.binding_report(root=root) == []

    def test_a_place_bound_row_needs_no_firing_to_be_proven(self, root):
        fb.file_finding("the gate is advisory", place="src/divineos/core", root=root)
        assert fb.binding_report(root=root) == []


class TestClosingNeedsAnObservedFailure:
    def test_a_single_run_does_not_close(self, root):
        row = fb.file_finding("x", place="src/a.py", root=root)
        with pytest.raises(ValueError):
            fb.close_finding(row, red_run="1 failed", green_run="", root=root)

    def test_two_identical_runs_do_not_close(self, root):
        """If nothing changed between the runs, nothing was observed."""
        row = fb.file_finding("x", place="src/a.py", root=root)
        with pytest.raises(ValueError):
            fb.close_finding(row, red_run="7 passed", green_run="7 passed", root=root)

    def test_a_red_then_green_pair_closes_it(self, root):
        row = fb.file_finding("x", place="src/a.py", root=root)
        assert fb.close_finding(row, "1 failed, 6 passed", "7 passed", root=root) is True
        assert fb.open_count(root=root) == 0

    def test_a_closed_row_stops_blocking_its_place(self, root):
        row = fb.file_finding("x", place="src/a.py", root=root)
        assert fb.blocking_for_place("src/a.py", root=root) != []
        fb.close_finding(row, "1 failed", "7 passed", root=root)
        assert fb.blocking_for_place("src/a.py", root=root) == []


class TestSupersessionIsHisWordNotOurs:
    def test_our_judgement_alone_cannot_retire_a_row(self, root):
        row = fb.file_finding("x", place="src/a.py", root=root)
        with pytest.raises(ValueError):
            fb.supersede(row, "", root=root)

    def test_naming_a_later_thing_he_said_retires_it(self, root):
        row = fb.file_finding("always run the full suite", place="src/a.py", root=root)
        assert fb.supersede(row, "run targeted tests during work", root=root) is True
        assert fb.open_count(root=root) == 0

    def test_there_is_no_age_path(self, root):
        """No function retires a row for being old, and this fails if one
        appears. Age is not evidence; that is the whole rule."""
        for name in dir(fb):
            assert "stale" not in name.lower()
            assert "expire" not in name.lower()


class TestScopingByParentPathIsNotAnEscape:
    def test_a_directory_finding_holds_for_files_inside_it(self, root):
        fb.file_finding("the hooks are advisory", place="src/divineos/core", root=root)
        standing = fb.blocking_for_place("src/divineos/core/hook_surfaces.py", root=root)
        assert len(standing) == 1
