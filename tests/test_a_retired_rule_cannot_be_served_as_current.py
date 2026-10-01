"""The register catches a retired rule stated on a surface that teaches.

Andrew, 2026-09-21, after I repeated a rule that had been replaced two weeks
earlier and told him it was current:

    "it is from the system. the system handed you old rules... it should NOT
    be able to hand you old rules"

These tests exercise the checker's pieces directly rather than the whole repo
scan, because the repo scan's answer changes every time somebody writes a
sentence, and a test whose expectation drifts with the tree is a test nobody
can read a failure out of.

The one that matters most is the last: a checker that cannot read a file must
not report the same thing as a checker that read it and found nothing. That
collapse has now been shipped twice in this house in ten days, once inside a
detector built to hunt it.
"""

import importlib.util
from pathlib import Path

import pytest

_CHECKER = Path(__file__).resolve().parent.parent / "scripts" / "check_retired_rules_not_served.py"


def _load():
    spec = importlib.util.spec_from_file_location("retired_rules_checker", _CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def checker():
    return _load()


@pytest.fixture
def one_rule(checker, tmp_path):
    entry = tmp_path / "2020-01-01_a_rule.md"
    entry.write_text(
        "<!-- retired-rule\n"
        "id: a-rule\n"
        "retired: 2020-01-01\n"
        "retired-by: somebody\n"
        "successor: the other thing\n"
        "pattern: (?i)\\bthe old way\\b\n"
        "-->\n\n# A rule\n",
        encoding="utf-8",
    )
    monkey_dir = tmp_path
    original = checker.REGISTER_DIR
    checker.REGISTER_DIR = monkey_dir
    yield checker.load_register()
    checker.REGISTER_DIR = original


def test_a_surface_stating_the_retired_rule_is_found(checker, one_rule, tmp_path):
    surface = tmp_path / "instructions.md"
    surface.write_text("Always do it the old way.\n", encoding="utf-8")
    hits, unreadable = checker.find_hits(one_rule, [surface])
    assert len(hits) == 1
    assert hits[0].rule.rule_id == "a-rule"
    assert unreadable == []


def test_a_deliberate_mention_is_allowed(checker, one_rule, tmp_path):
    """Saying that a rule is retired must not itself count as serving it.

    Without this the archive would trip its own guard, and the only way to
    write about a retired rule would be to not write about it -- which is the
    deletion-as-archive failure the register exists to avoid.
    """
    surface = tmp_path / "instructions.md"
    surface.write_text("We no longer do it the old way.  RETIRED-RULE-OK\n", encoding="utf-8")
    hits, _ = checker.find_hits(one_rule, [surface])
    assert hits == []


def test_a_surface_saying_nothing_of_the_kind_is_clean(checker, one_rule, tmp_path):
    surface = tmp_path / "instructions.md"
    surface.write_text("Do the thing that is currently correct.\n", encoding="utf-8")
    hits, unreadable = checker.find_hits(one_rule, [surface])
    assert hits == []
    assert unreadable == []


def test_an_unreadable_file_is_reported_apart_from_a_clean_one(checker, one_rule, tmp_path):
    """Could-not-read and found-nothing are different answers.

    A file of bytes that are not text comes back on the unreadable list, not
    silently as a clean scan. The caller can then say so instead of counting
    it as coverage it never had.
    """
    unreadable_file = tmp_path / "binary.py"
    unreadable_file.write_bytes(b"\xff\xfe\x00\x01 the old way \x00\xff")
    clean_file = tmp_path / "fine.md"
    clean_file.write_text("nothing to see\n", encoding="utf-8")

    hits, unreadable = checker.find_hits(one_rule, [unreadable_file, clean_file])
    assert hits == []
    assert unreadable == [unreadable_file]


def test_an_entry_with_no_pattern_is_refused_rather_than_ignored(checker, tmp_path):
    """An entry that can never match is worse than no entry.

    It looks like coverage on the shelf and provides none, which is the exact
    shape of the failure the register was built for.
    """
    (tmp_path / "2020-01-01_toothless.md").write_text(
        "<!-- retired-rule\nid: toothless\nretired: 2020-01-01\n-->\n",
        encoding="utf-8",
    )
    original = checker.REGISTER_DIR
    checker.REGISTER_DIR = tmp_path
    try:
        with pytest.raises(checker.CheckerError, match="registers no pattern"):
            checker.load_register()
    finally:
        checker.REGISTER_DIR = original


def test_a_pattern_that_will_not_compile_is_could_not_run(checker, tmp_path):
    """Aria, station four: uncaught, re.error exited 1, the code for a real hit."""
    (tmp_path / "2020-01-01_broken.md").write_text(
        "<!-- retired-rule\nid: broken\nretired: 2020-01-01\npattern: unclosed(group\n-->\n",
        encoding="utf-8",
    )
    original = checker.REGISTER_DIR
    checker.REGISTER_DIR = tmp_path
    try:
        with pytest.raises(checker.CheckerError, match="does not compile"):
            checker.load_register()
    finally:
        checker.REGISTER_DIR = original


def test_an_unreadable_file_makes_the_run_could_not_run(checker, one_rule, tmp_path, monkeypatch):
    """Printed as UNREADABLE, the run still exited 0, and precommit read that as
    a pass over a file nobody checked."""
    unreadable_file = tmp_path / "binary.py"
    unreadable_file.write_bytes(b"\xff\xfe\x00\x01 the old way \x00\xff")
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(checker, "load_register", lambda: one_rule)
    monkeypatch.setattr(checker, "scanned_files", lambda: [unreadable_file])
    monkeypatch.setattr(checker, "load_baseline", set)
    assert checker.main() == 2


def test_an_empty_register_reports_could_not_run_not_clean(checker, tmp_path):
    original = checker.REGISTER_DIR
    checker.REGISTER_DIR = tmp_path
    try:
        with pytest.raises(checker.CheckerError, match="only ever pass"):
            checker.load_register()
    finally:
        checker.REGISTER_DIR = original


def test_the_real_register_parses_and_carries_a_successor(checker):
    """The shipped archive is loadable and each entry says what replaced it.

    An entry without a successor tells a reader the rule is dead and leaves
    them with no way to find what is alive, which sends them back to the
    retired rule as the only thing written down.
    """
    rules = checker.load_register()
    assert rules, "the shipped register is empty"
    for rule in rules:
        assert rule.successor != "<none recorded>", rule.rule_id
        assert rule.patterns
