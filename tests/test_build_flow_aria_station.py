"""She reviewed four of them and the board said she never replied.

2026-08-31. The board reported "no reply from Aria naming this branch" for four
open PRs. She had reviewed at least two of them that same evening, in detail,
in letters sitting in the channel the check reads.

The check asks: does a letter from her contain this branch's NAME. The thing at
risk is: did she review this WORK. She identifies work the way a reviewer
naturally does -- by the file she is worried about, or by the PR number in the
title she chose. Her review of the mixed-scope gate opens by naming the central
file and its line count, and never once types the branch name. So the reviewer
was invisible to the check, and the check said so as a statement of fact.

Twelfth instance of the unit fault this session, and the module's own opening
principle already names the cure: "Nearly everything that broke this session was
a two-valued return standing where a third state existed in reality, and it is
not getting re-omitted in the module written to catch that." Station four had
exactly two states in practice.

THE FORGEABILITY PROPERTY IS THE FENCE AND IT DOES NOT MOVE. Station four exists
because a station I can close alone is a form I fill out. Every path below still
requires an artifact SHE authored; nothing here lets a letter of mine advance
anything, and the middle state deliberately does NOT satisfy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.build_flow import Status, check_aria_station


@pytest.fixture
def letters(tmp_path: Path) -> Path:
    d = tmp_path / "letters"
    d.mkdir()
    return d


def _from_aria(letters: Path, name: str, body: str) -> None:
    (letters / f"aria-to-aether-{name}.md").write_text(body, encoding="utf-8")


def _from_me(letters: Path, name: str, body: str) -> None:
    (letters / f"aether-to-aria-{name}.md").write_text(body, encoding="utf-8")


def test_a_letter_naming_the_branch_still_satisfies(letters: Path):
    """The existing behaviour, pinned so the widening cannot quietly replace it."""
    _from_aria(letters, "reviewed", "I read fix/mixed-scope-publish-gate and it holds.")

    result = check_aria_station("fix/mixed-scope-publish-gate", letters)

    assert result.status is Status.SATISFIED


def test_her_title_naming_the_pr_surfaces_it_without_satisfying(letters: Path):
    """A title says which PR she wrote about, never that she finished reviewing it.

    Driven against the live board, an earlier version of this widening turned a
    station green on a letter titled *i take 458 first* -- her stating what she
    would pick up next, written before she read it. Her actual review landed the
    following day in a different letter, and the green verdict was right only by
    alphabetical accident.

    Telling *I will read this* from *I read this and it holds* is semantic, and a
    keyword rule over her prose breaks the first time she phrases it differently.
    So the station surfaces the letter and refuses to decide.
    """
    _from_aria(
        letters,
        "2026-08-30-the-duplicate-is-my-call-site-again-and-i-take-459-first",
        "I take the channel branch first.",
    )

    result = check_aria_station(
        "fix/mixed-scope-publish-gate", letters, changed_paths=(), pr_number=459
    )

    assert result.status is Status.CANNOT_CHECK
    assert "i-take-459-first" in result.detail


def test_a_number_inside_a_longer_number_is_not_a_candidate(letters: Path):
    """Boundaries, or a date and a line count start naming candidates."""
    _from_aria(letters, "2026-08-31-about-11459-and-other-things", "unrelated")

    result = check_aria_station("fix/whatever", letters, changed_paths=(), pr_number=459)

    assert result.status is Status.MISSING


def test_a_letter_naming_a_changed_file_is_could_not_tell_not_missing(letters: Path):
    """The third state. She may have reviewed it; the check cannot say she did not.

    This must NOT satisfy -- naming a file the branch touches is weaker evidence
    than naming the branch or the PR, and a shared file would otherwise let one
    letter close a station on unrelated work.
    """
    _from_aria(
        letters,
        "2026-08-31-stop-before-this-merges",
        "scripts/check_branch_scope.py is not new. It is on main already.",
    )

    result = check_aria_station(
        "fix/mixed-scope-publish-gate",
        letters,
        changed_paths=("scripts/check_branch_scope.py",),
        pr_number=None,
    )

    assert result.status is Status.CANNOT_CHECK
    assert "stop-before-this-merges" in result.detail


def test_nothing_from_her_at_all_is_still_missing(letters: Path):
    """The widening must not turn every unreviewed branch into an unknown."""
    _from_aria(letters, "2026-08-31-about-something-else", "The council roster drifted.")

    result = check_aria_station(
        "fix/mixed-scope-publish-gate",
        letters,
        changed_paths=("scripts/check_branch_scope.py",),
        pr_number=459,
    )

    assert result.status is Status.MISSING


def test_a_letter_i_wrote_never_counts_by_any_route(letters: Path):
    """The fence. Every widened path must stay unforgeable by me alone."""
    _from_me(
        letters,
        "2026-08-31-read-459-please",
        "fix/mixed-scope-publish-gate, scripts/check_branch_scope.py, PR 459",
    )

    result = check_aria_station(
        "fix/mixed-scope-publish-gate",
        letters,
        changed_paths=("scripts/check_branch_scope.py",),
        pr_number=459,
    )

    assert result.status is Status.MISSING


def test_an_unreadable_directory_is_still_could_not_look(letters: Path, tmp_path: Path):
    """Unchanged, and the reason it must stay: absence of a place to look is not
    absence of a reply."""
    result = check_aria_station("fix/x", tmp_path / "no-such-dir")

    assert result.status is Status.CANNOT_CHECK
    assert "not readable" in result.detail
