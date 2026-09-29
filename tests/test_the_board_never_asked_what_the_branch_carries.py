"""A gate repair wearing a hundred and sixty-one letters read READY for four days.

2026-09-14. I handed Aletheia four branches as finished. One of them adds a
hundred and eighty-one files over main and a hundred and sixty-one of those are
letters and archive exports, dropped there by an automatic checkpoint on the
tenth. It had read READY on this board ever since, and I quoted that word onward
without re-deriving what it covers.

THE QUESTION WAS ASKED ONLY AT THE DOOR. The push gate asks exactly this and
refuses a mixed branch -- but it fires at PUBLISH time, so a branch polluted by
a local checkpoint and never pushed again is never asked. Four stations answered
honestly and none of them was the question.

A publish-time check cannot protect a branch nobody publishes. So the board asks
it too, every time it is read.

THE REMEDY SENTENCE IS LOAD-BEARING AND CARRIES A SCAR. Its sibling
(test_branch_scope_only_here) records 2026-08-31: the push gate's advice to
rebuild against main was correct for eleven regenerable archive mirrors and
FATAL for five dreams and a letter that existed on that branch and no other ref
anywhere. The five survived only because the refusal got read instead of obeyed.
So this station never says rebuild without saying verify-by-name first, and one
test below pins that ordering in the text.
"""

from __future__ import annotations

import pytest

from divineos.core.build_flow import Status, check_scope_station

_CODE = ("src/divineos/core/a.py", "tests/test_a.py", "scripts/b.sh")
_WRITING = (
    "family/letters/aria-to-aether-2026-09-10-x.md",
    "exploration/aether/99_y.md",
    "dreams/aether/03_z.md",
    "docs/archives/decisions.md",
)


def test_a_code_only_branch_passes() -> None:
    result = check_scope_station(_CODE, "fix/a")
    assert result.status is Status.SATISFIED
    assert "no writing" in result.detail


def test_the_live_shape_is_refused() -> None:
    """THE ONE I SENT TO ALETHEIA AS READY."""
    paths = tuple(f"family/letters/l{i}.md" for i in range(161)) + _CODE
    result = check_scope_station(paths, "fix/a-refusal-must-say-what-did-not-run")
    assert result.status is Status.MISSING
    assert "161" in result.detail
    assert "skims" in result.detail


def test_the_refusal_says_verify_by_name_before_it_says_rebuild() -> None:
    """The 2026-08-31 scar. Rebuild-first advice nearly destroyed five files
    that lived on one ref; the verify clause must precede the rebuild clause in
    the sentence a reader acts on, not merely appear somewhere in it."""
    paths = (*_CODE, *_WRITING)
    detail = check_scope_station(paths, "fix/a").detail
    assert "by name" in detail
    assert "Rebuild" in detail
    assert detail.index("Rebuild") < detail.index("by name"), (
        "the rebuild instruction must be qualified by the verification that "
        "follows it in the same sentence"
    )


def test_one_stray_letter_is_still_mixed() -> None:
    """The fault is the mixture, so there is no tolerated dose of it."""
    result = check_scope_station((*_CODE, _WRITING[0]), "fix/a")
    assert result.status is Status.MISSING


@pytest.mark.parametrize("stray", _WRITING)
def test_every_writing_prefix_is_seen(stray: str) -> None:
    """All four kinds, not only letters -- archives are what rode in here."""
    assert check_scope_station((*_CODE, stray), "fix/a").status is Status.MISSING


def test_an_all_writing_branch_is_not_mixed() -> None:
    """Writing belongs on a writing branch. This station names the MIXTURE, and
    a branch that is only prose is exactly where the prose should be."""
    result = check_scope_station(_WRITING, "substrate/letters")
    assert result.status is Status.SATISFIED
    assert "not mixed" in result.detail


def test_an_unreadable_file_set_is_not_clean() -> None:
    """An outage must not upgrade a mixed branch to a tidy one -- the same
    absence-becomes-value collapse the council station was repaired for."""
    result = check_scope_station(None, "fix/a")
    assert result.status is Status.CANNOT_CHECK
    assert "not clean" in result.detail


def test_an_empty_diff_is_not_a_mixture() -> None:
    assert check_scope_station((), "fix/a").status is Status.SATISFIED


def test_the_prefixes_are_the_lens_requirement_s_own_list() -> None:
    """One list, not two. Two definitions of substrate would drift, which is the
    defect the sweep repair exists to end."""
    from divineos.core import build_flow

    for prefix in build_flow._UNGRIPPABLE_PREFIXES:
        assert check_scope_station((f"{prefix}x.md", *_CODE), "fix/a").status is Status.MISSING
