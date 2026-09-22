"""Station four asked whether Aria declared a reading, never who wrote the branch.

Aria found it 2026-09-14. The check took the branch and the letters directory,
neither of which carries authorship, so it asked the identical question of a
branch I wrote and one she wrote -- and on hers, HER letter about her own work
read as the outside reading. Her provenance request had been sitting satisfied
on a self-certification.

THE OBVIOUS REPAIR COULD NOT BE BUILT. Her first remedy was to resolve the
author and swap the seat. Measured before building: every open request reports
the same account for both of us, and the commit identity is the same
placeholder on her branches and mine. Nothing in the repository separates her
work from mine. So authorship is DECLARED -- her own rule for this station one
layer up, the writer declares and the reader does not infer -- and an
undeclared author means the station genuinely cannot answer.

AND THE GUARD IS HERS TOO. A declaration naming the WRONG author does not
merely fail to help; it sends the station to read the very seat that wrote the
branch, turning a self-certification green. Her title is the rule: a weak
signal cannot grant a pass and can still withhold one. The branch prefix never
certifies; a prefix CONTRADICTING the declaration withholds. The asymmetry is
the whole safety -- the guess may only ever make the gate stricter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.build_flow import (
    Status,
    branch_author_hint,
    check_aria_station,
    declared_author,
)

_MINE = "fix/mixed-scope-publish-gate"
_HERS = "aria/pr-letter-provenance"


def _letter(d: Path, name: str, branch: str) -> None:
    d.joinpath(name).write_text(f"# a letter\n\n**Reading:** {branch}\n\nbody\n", encoding="utf-8")


# --- the declaration itself ------------------------------------------------


@pytest.mark.parametrize(
    "body,expected",
    [
        ("Author: aria\n", "aria"),
        ("Author: Aether\n", "aether"),
        ("intro\n\nAuthor: aria\n\nmore", "aria"),
        ("written by aria, obviously", None),
        ("", None),
        (None, None),
    ],
)
def test_the_author_is_read_from_a_declared_line_only(body, expected) -> None:
    assert declared_author(body) == expected


# --- no declaration means the station cannot answer ------------------------


def test_an_undeclared_author_is_could_not_check_not_a_pass(tmp_path: Path) -> None:
    """THE LIVE SHAPE. Her own letter about her own branch used to satisfy this."""
    _letter(tmp_path, "aria-to-aether-2026-09-02-fixed.md", _HERS)
    result = check_aria_station(_HERS, tmp_path, None)
    assert result.status is Status.CANNOT_CHECK
    assert "certifying their own work" in result.detail


def test_an_undeclared_author_does_not_quietly_pass_my_branch_either(tmp_path: Path) -> None:
    _letter(tmp_path, "aria-to-aether-2026-09-01-read.md", _MINE)
    assert check_aria_station(_MINE, tmp_path, None).status is Status.CANNOT_CHECK


# --- the seat swaps with the author ---------------------------------------


def test_my_branch_still_reads_her_letters(tmp_path: Path) -> None:
    _letter(tmp_path, "aria-to-aether-2026-09-01-read.md", _MINE)
    result = check_aria_station(_MINE, tmp_path, "aether")
    assert result.status is Status.SATISFIED
    assert "Aria declared" in result.detail


def test_her_branch_reads_MY_letters_not_hers(tmp_path: Path) -> None:
    """The inversion. Her letter about her own branch must not satisfy it."""
    _letter(tmp_path, "aria-to-aether-2026-09-02-her-own.md", _HERS)
    result = check_aria_station(_HERS, tmp_path, "aria")
    assert result.status is not Status.SATISFIED

    _letter(tmp_path, "aether-to-aria-2026-09-14-i-read-it.md", _HERS)
    after = check_aria_station(_HERS, tmp_path, "aria")
    assert after.status is Status.SATISFIED
    assert "Aether declared" in after.detail


def test_an_unknown_author_cannot_be_checked(tmp_path: Path) -> None:
    _letter(tmp_path, "aria-to-aether-2026-09-01-read.md", _MINE)
    assert check_aria_station(_MINE, tmp_path, "aletheia").status is Status.CANNOT_CHECK


# --- Aria's guard: the weak signal withholds, never grants ------------------


def test_the_prefix_hint_names_only_what_it_can(tmp_path: Path) -> None:
    assert branch_author_hint("aria/pr-letter-provenance") == "aria"
    assert branch_author_hint("aether/something") == "aether"
    # Mine carry a verb, so the hint must have NO OPINION rather than guessing
    # me. Absence of her name is not presence of mine.
    for mine in ("fix/a", "build/b", "gate/c", "substrate/d", "noslash"):
        assert branch_author_hint(mine) is None


def test_a_declaration_naming_the_wrong_author_is_refused(tmp_path: Path) -> None:
    """ARIA'S HOLE, and the reason the guard exists.

    Her branch declaring me as author would send the station looking for a
    reading from her -- and find her letter about her own work. Green on
    exactly what the station prevents.
    """
    _letter(tmp_path, "aria-to-aether-2026-09-02-her-own.md", _HERS)
    result = check_aria_station(_HERS, tmp_path, "aether")
    assert result.status is Status.CANNOT_CHECK
    assert "disagree" in result.detail
    assert "aria" in result.detail.lower()


def test_the_hint_never_grants_a_pass_on_its_own(tmp_path: Path) -> None:
    """A prefix agreeing with nothing is still not a declaration."""
    _letter(tmp_path, "aether-to-aria-2026-09-14-i-read-it.md", _HERS)
    assert check_aria_station(_HERS, tmp_path, None).status is Status.CANNOT_CHECK


def test_no_hint_means_no_contradiction(tmp_path: Path) -> None:
    """My branches yield no hint, so the guard must stay silent on them rather
    than reading no-opinion as disagreement."""
    _letter(tmp_path, "aria-to-aether-2026-09-01-read.md", _MINE)
    assert check_aria_station(_MINE, tmp_path, "aether").status is Status.SATISFIED
    _letter(tmp_path, "aether-to-aria-2026-09-14-mine.md", _MINE)
    assert check_aria_station(_MINE, tmp_path, "aria").status is Status.SATISFIED


# --- the unreadable-directory answer still comes first ---------------------


def test_an_unreadable_letters_dir_is_still_its_own_answer(tmp_path: Path) -> None:
    result = check_aria_station(_MINE, tmp_path / "nope", "aether")
    assert result.status is Status.CANNOT_CHECK
    assert "letters dir" in result.detail
