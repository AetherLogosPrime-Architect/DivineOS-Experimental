"""The population must be measured, and the question must not be changeable after the fact.

Two properties carry this module, and both are gaming vectors rather than
correctness details — so they are asserted, not trusted:

1. A caller cannot ASSERT a population. The number comes from running a search.
   Foucault's constraint from the walk: if the count can be composed, the
   discipline produces someone fluent at composing counts.

2. Verification re-runs the STORED pattern. If a fresh pattern could be handed
   in at verify time, any class could be closed by narrowing the question after
   the answer is known.

The third property is Dijkstra's control: a pattern matching nothing is a fact
about the instrument, not about the tree, and must be its own state.
"""

from __future__ import annotations

import pytest

from divineos.core import class_fix as cf


@pytest.fixture
def tree(tmp_path):
    """A small tree with three sites of one class and one near-miss."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        "home = Path.home() / f'.thing-{name}'\n", encoding="utf-8"
    )
    (tmp_path / "pkg" / "b.py").write_text(
        "x = 1\nhome = Path.home() / f'.thing-{who}'\n", encoding="utf-8"
    )
    (tmp_path / "c.py").write_text("home = Path.home() / f'.thing-{m}'\n", encoding="utf-8")
    (tmp_path / "unrelated.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("Path.home() / f'.thing-{name}'\n", encoding="utf-8")
    skip = tmp_path / ".venv" / "lib"
    skip.mkdir(parents=True)
    (skip / "vendored.py").write_text("home = Path.home() / f'.thing-{v}'\n", encoding="utf-8")
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "_store_path", lambda: tmp_path / "store" / "class_fixes.json")


PATTERN = r"Path\.home\(\)\s*/\s*f?['\"]\.thing-"


class TestTheSearchItself:
    def test_it_finds_every_site_of_the_class(self, tree):
        sites = cf.search(PATTERN, tree)
        assert len(sites) == 3
        assert {s.path for s in sites} == {"pkg/a.py", "pkg/b.py", "c.py"}

    def test_it_records_the_line_number_not_just_the_file(self, tree):
        sites = {s.path: s.line for s in cf.search(PATTERN, tree)}
        assert sites["pkg/b.py"] == 2, "a site on line 2 must not be reported as line 1"

    def test_vendored_trees_are_not_counted(self, tree):
        """A population inflated by code nobody here wrote is a number nobody
        can act on, which is worse than no number."""
        assert all(".venv" not in s.path for s in cf.search(PATTERN, tree))

    def test_the_glob_decides_what_is_searched(self, tree):
        """Control for the test above: the markdown file DOES match the pattern,
        so its absence from the default sweep is the filter working rather than
        the pattern failing."""
        assert cf.search(PATTERN, tree, globs=("*.md",))[0].path == "notes.md"


class TestDeclaring:
    def test_the_population_is_measured_not_supplied(self, tree):
        """The signature is the assertion: there is no count parameter, so no
        caller can state a population it did not run."""
        import inspect

        params = inspect.signature(cf.declare).parameters
        assert "before" not in params and "count" not in params
        assert cf.declare("thing home", PATTERN, tree).before == 3

    def test_the_sites_are_kept_so_which_ones_is_answerable(self, tree):
        fix = cf.declare("thing home", PATTERN, tree)
        assert len(fix.before_sites) == 3

    def test_a_pattern_matching_nothing_is_a_broken_probe_not_a_clean_tree(self, tree):
        """Dijkstra's control. Three measurements on 2026-09-07 reported zero
        from broken probes and every zero was read as a finding about the world."""
        fix = cf.declare("nothing", r"ZZZ_NEVER_APPEARS_ZZZ", tree)
        assert fix.state() == cf.PROBE_BROKEN
        assert fix.state() != cf.CLOSED

    def test_a_population_of_one_is_flagged_rather_than_smoothed_away(self, tree):
        """This mechanism's own falsifier, made visible: a pattern narrowed to
        the site already being edited closes trivially."""
        fix = cf.declare("just c", r"\.thing-\{m\}", tree)
        assert fix.before == 1
        assert fix.single_site is True

    def test_an_ordinary_population_is_not_flagged(self, tree):
        """Control: if single_site were always true the flag would say nothing."""
        assert cf.declare("thing home", PATTERN, tree).single_site is False


class TestExcluding:
    """The escape hatch, and the place this could rot into a stamp.

    Most classes of this shape are defined negatively — the convention rebuilt
    by hand ANYWHERE BUT the module that owns it — so without exclusion the
    canonical implementation counts as a member of the class it defines and the
    population can never reach zero. It is also the obvious cheat, which is why
    it is stored, reused verbatim, and printed.
    """

    def test_an_excluded_path_leaves_the_population(self, tree):
        fix = cf.declare("thing home", PATTERN, tree, exclude=("pkg/",))
        assert fix.before == 1
        assert fix.before_sites[0].path == "c.py"

    def test_the_exclusion_survives_into_verification(self, tree):
        """If verify swept without the stored exclusions, a class could never
        close and the mechanism would report failure forever."""
        fix = cf.declare("thing home", PATTERN, tree, exclude=("pkg/",))
        (tree / "c.py").write_text("home = member_home(m)\n", encoding="utf-8")
        after = cf.verify(fix.fix_id)
        assert after.state() == cf.CLOSED

    def test_the_exclusion_is_visible_in_the_report(self, tree):
        """An invisible exclusion is an unexaminable one."""
        fix = cf.declare("thing home", PATTERN, tree, exclude=("pkg/",))
        assert "excluded: pkg/" in cf.format_fix(fix)

    def test_no_exclusion_means_no_exclusion_line(self, tree):
        """Control: the line above must be reporting something real."""
        assert "excluded:" not in cf.format_fix(cf.declare("t", PATTERN, tree))


class TestAriasGameWalk:
    """Her findings, 2026-09-08, asserted rather than agreed with.

    She took the game-walk station because it cannot be mine — I am not
    reliably adversarial toward my own build, and no resolve fixes that, it is
    the same seat. Two of her six routes are closable from code and these are
    they.
    """

    def test_the_clock_records_how_long_the_class_stayed_open(self, tree):
        """Her first route and the one she would actually take: fix the sites
        in front of me, THEN declare. Every field true, nothing composed, and
        the instrument does no work — because its whole value is the site I did
        not know about. The record cannot catch it, since the record is honest.
        The clock can."""
        fix = cf.declare("thing home", PATTERN, tree)
        for name in ("pkg/a.py", "pkg/b.py", "c.py"):
            (tree / name).write_text("ok\n", encoding="utf-8")
        after = cf.verify(fix.fix_id)
        assert after.seconds_to_close is not None
        assert after.receipt_shaped is True

    def test_an_unverified_class_has_no_gap_rather_than_a_zero(self, tree):
        """Could-not-look again: never verified must not read as closed in no
        time at all."""
        fix = cf.declare("thing home", PATTERN, tree)
        assert fix.seconds_to_close is None
        assert fix.receipt_shaped is False

    def test_a_class_still_carrying_sites_is_not_receipt_shaped(self, tree):
        """Control: the flag is about closing fast, not about being young."""
        fix = cf.declare("thing home", PATTERN, tree)
        assert cf.verify(fix.fix_id).receipt_shaped is False

    def test_the_exclusions_are_counted_not_merely_listed(self, tree):
        """Her second route. Storing and printing the exclusions guards nothing
        because it relies on a reader, and his corrections have printed at the
        top of every turn all day unread. So the hatch gets the same instrument
        the class gets."""
        fix = cf.declare("thing home", PATTERN, tree, exclude=("pkg/",))
        assert fix.before == 1
        assert fix.excluded_count == 2

    def test_a_hatch_wider_than_the_class_is_a_finding(self, tree):
        fix = cf.declare("thing home", PATTERN, tree, exclude=("pkg/",))
        assert fix.exclusions_outweigh_findings is True
        assert "HATCH IS WIDER" in cf.format_fix(fix)

    def test_a_narrow_hatch_is_not_flagged(self, tree):
        """Control: excluding one site of three must not raise the alarm, or
        the alarm says nothing."""
        fix = cf.declare("thing home", PATTERN, tree, exclude=("c.py",))
        assert fix.excluded_count == 1
        assert fix.exclusions_outweigh_findings is False
        assert "HATCH IS WIDER" not in cf.format_fix(fix)

    def test_no_exclusions_means_nothing_was_hidden(self, tree):
        assert cf.declare("t", PATTERN, tree).excluded_count == 0


class TestVerifying:
    def test_removing_every_site_closes_the_class(self, tree):
        fix = cf.declare("thing home", PATTERN, tree)
        for name in ("pkg/a.py", "pkg/b.py", "c.py"):
            (tree / name).write_text("home = member_home(name)\n", encoding="utf-8")
        after = cf.verify(fix.fix_id)
        assert after.after == 0
        assert after.state() == cf.CLOSED

    def test_removing_some_sites_reports_reduced_and_names_the_survivors(self, tree):
        """The state that did not exist before, and the one that matters: a
        partial repair used to be recorded identically to a complete one."""
        fix = cf.declare("thing home", PATTERN, tree)
        (tree / "c.py").write_text("home = member_home(m)\n", encoding="utf-8")
        after = cf.verify(fix.fix_id)
        assert after.state() == cf.REDUCED
        assert after.after == 2
        assert {s.path for s in after.after_sites} == {"pkg/a.py", "pkg/b.py"}

    def test_changing_nothing_leaves_it_open(self, tree):
        fix = cf.declare("thing home", PATTERN, tree)
        assert cf.verify(fix.fix_id).state() == cf.OPEN

    def test_the_question_cannot_be_narrowed_after_the_answer_is_known(self, tree):
        """The main gaming vector. Verification takes an id and nothing else,
        so the only thing it can change is the answer."""
        import inspect

        params = inspect.signature(cf.verify).parameters
        assert list(params) == ["fix_id"]

    def test_verifying_an_unknown_id_raises_rather_than_reporting_clean(self, tree):
        with pytest.raises(KeyError):
            cf.verify("cfix-does-not-exist")


class TestTheBacklog:
    def test_open_and_reduced_classes_stay_on_the_list(self, tree):
        cf.declare("thing home", PATTERN, tree)
        assert len(cf.open_fixes()) == 1

    def test_a_closed_class_leaves_the_list(self, tree):
        fix = cf.declare("thing home", PATTERN, tree)
        for name in ("pkg/a.py", "pkg/b.py", "c.py"):
            (tree / name).write_text("ok\n", encoding="utf-8")
        cf.verify(fix.fix_id)
        assert cf.open_fixes() == []

    def test_a_broken_probe_is_not_quietly_parked_in_the_backlog(self, tree):
        """It needs a new pattern, not patience. Leaving it among the open
        classes would let a broken instrument look like pending work."""
        cf.declare("nothing", r"ZZZ_NEVER_APPEARS_ZZZ", tree)
        assert cf.open_fixes() == []


class TestWhatItSays:
    def test_a_broken_probe_says_so_in_words(self, tree):
        fix = cf.declare("nothing", r"ZZZ_NEVER_APPEARS_ZZZ", tree)
        assert "PROBE FOUND NOTHING" in cf.format_fix(fix)

    def test_survivors_are_named_in_the_report(self, tree):
        fix = cf.declare("thing home", PATTERN, tree)
        (tree / "c.py").write_text("ok\n", encoding="utf-8")
        assert "still: pkg/a.py" in cf.format_fix(cf.verify(fix.fix_id))
