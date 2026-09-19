"""A guard nobody runs must be findable, and the finder must state its blindness.

WHY THIS FILE EXISTS. 2026-09-19: a command built in July to catch an
interpreter resolving to a sibling checkout -- describing that failure in its
own help text -- had never been called by anything, and the person who built it
hit that exact failure two months later and found it by hand. Third instance in
one night of a guard that exists and is never run.

THE TESTS THAT MATTER MOST HERE ARE THE ONES ABOUT NOT-LOOKING. A check whose
empty result is indistinguishable from a check that read nothing is the
confounded measurement this whole night was about, so the refusal on an empty
corpus is pinned harder than the happy path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_guards_have_callers", REPO_ROOT / "scripts" / "check_guards_have_callers.py"
)
assert _SPEC and _SPEC.loader
guards = importlib.util.module_from_spec(_SPEC)
sys.modules["check_guards_have_callers"] = guards
_SPEC.loader.exec_module(guards)


def test_a_tree_with_no_automation_refuses_instead_of_passing(tmp_path, capsys):
    """The one that guards the guard.

    An empty corpus yields an empty finding list, which reads as reassurance.
    If this ever returns zero, the check has become a machine for producing
    clean results about nothing.
    """
    code = _run_against(tmp_path)
    assert code == 2
    assert "REFUSED" in capsys.readouterr().err


def _run_against(root: Path) -> int:
    original = guards.REPO_ROOT
    guards.REPO_ROOT = root
    try:
        return guards.main([])
    finally:
        guards.REPO_ROOT = original


def test_the_refusal_says_a_broken_probe_is_not_a_clean_result(tmp_path, capsys):
    _run_against(tmp_path)
    err = capsys.readouterr().err.lower()
    assert "broken probe" in err
    assert "clean result" in err


def test_the_scope_note_prints_even_when_nothing_is_found(tmp_path, capsys):
    """A limitation shown only beside findings teaches that silence is coverage.

    This is the non-obvious half of the design and the one a later tidy-up
    would remove first, because printing caveats on a clean run looks like
    noise until you know why it is there.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "everything.sh").write_text(
        "\n".join(
            guards.invocation(g, s)
            for g, s in guards.registered_commands()
            if guards.guard_shaped(g, s)
        ),
        encoding="utf-8",
    )
    code = _run_against(tmp_path)
    out = capsys.readouterr().out
    assert code == 0
    assert "every guard found has an invocation" in out
    assert "silence is not coverage" in out


def test_a_guard_with_no_caller_is_named(tmp_path, capsys):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "some.sh").write_text("echo nothing relevant\n", encoding="utf-8")
    _run_against(tmp_path)
    out = capsys.readouterr().out
    assert "NO invocation" in out
    assert "divineos doctor verify-import" in out


def test_the_real_repository_is_measured_rather_than_assumed():
    """Non-vacuity, and the finding this file was written for.

    Every assertion above runs against a fixture. If the census or the search
    were broken, they would all still pass. This one asserts the instrument
    finds a case it should find in the actual tree -- the check I failed twice
    this month by reporting an absence from a probe I never proved could see.
    """
    missing, considered, files_read = guards.uncalled_guards()
    assert files_read > 0
    assert considered > 0
    assert "divineos doctor verify-import" in missing


def test_the_instrument_does_not_count_its_own_documentation_as_a_caller():
    """The failure this file's real-repository test caught, pinned.

    The scope note names an example spelling so a reader can copy the form that
    registers. That example is literal text, and this instrument lives inside
    the directories it searches -- so it read its own documentation and
    concluded the guard was wired. A silent false NEGATIVE, a real gap hidden,
    which is the direction argued all night to be worse than the noisy one.

    Anyone moving the example, or adding a second one, re-introduces it. This
    asserts the exclusion rather than the symptom, because the symptom is
    exactly what an instrument cannot see about itself.
    """
    own_text = (REPO_ROOT / "scripts" / "check_guards_have_callers.py").read_text(encoding="utf-8")
    assert "divineos doctor verify-import" in own_text, (
        "the example spelling left the file, so this test now proves nothing"
    )
    blob, _ = guards.automation_text()
    assert "MATCHING: an invocation registers only if" not in blob


def test_the_group_name_does_not_make_every_subcommand_a_guard():
    """The first version matched on the whole command path, so every
    subcommand of the audit group came back as guard-shaped on its group name
    alone -- thirty hits and no signal. The verb has to be the leaf."""
    assert guards.guard_shaped("audit", "summary") is False
    assert guards.guard_shaped("audit", "list") is False
    assert guards.guard_shaped("doctor", "verify-import") is True
    assert guards.guard_shaped("check-prose", None) is True


def test_documentation_is_not_a_caller(tmp_path, capsys):
    """A guard named in prose is described, not invoked.

    If docs counted, the check would pass on a repository that documents every
    guard and runs none -- which is the exact shape of the failure it exists to
    catch.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "noop.sh").write_text("true\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text(
        "Run `divineos doctor verify-import` to check your interpreter.\n", encoding="utf-8"
    )
    _run_against(tmp_path)
    assert "divineos doctor verify-import" in capsys.readouterr().out


@pytest.mark.parametrize("flag,expected", [([], 0), (["--strict"], 1)])
def test_strict_turns_the_report_into_a_verdict(tmp_path, capsys, flag, expected):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "noop.sh").write_text("true\n", encoding="utf-8")
    original = guards.REPO_ROOT
    guards.REPO_ROOT = tmp_path
    try:
        assert guards.main(flag) == expected
    finally:
        guards.REPO_ROOT = original
    capsys.readouterr()
