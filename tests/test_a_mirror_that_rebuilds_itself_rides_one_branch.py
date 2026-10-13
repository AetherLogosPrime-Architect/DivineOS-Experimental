"""A regenerated export is substrate, and it is not the kind that wants saving.

Written 2026-09-18 from a loop that ran for three days in plain sight.

THE LOOP. ``docs/archives/`` holds text exports of the databases. They are
tracked on main on purpose -- Andrew decided 2026-08-16 that the readable mirror
is what survives when the database itself is too large for the remote -- and
they are rebuilt from those databases at every checkpoint.

The checkpoint classified them as substrate, correctly. It then found them
already tracked on the checked-out branch and folded them into the
work-in-progress commit, which is correct for a letter an earlier sweep
stranded there: committing it is exactly what takes it off, and the loop ends
after one pass. An export is not stranded. It is tracked deliberately and
regenerates within the hour, so the fold had nothing to terminate against.

MEASURED: three such commits on one code branch between 2026-09-16 and
2026-09-18, each carrying the same eleven exports and roughly fifteen hundred
changed lines, against four separate hand-repairs restoring them to main's
content. The branch reached an auditor with ninety files in its diff, of which
two were the work.

WHY SKIPPING IS SAFE HERE AND NOWHERE ELSE. The export is a pure function of a
database that still holds the content, with a command that rebuilds it. A
letter IS its content. So the predicate must name only paths with a generator
behind them, and these tests pin that narrowness as hard as they pin the skip --
a list that grows to cover something handwritten would stop that file being
saved and nothing would announce it.
"""

from __future__ import annotations

import pytest

from divineos.core.substrate_paths import (
    LOCAL_SUBSTRATE_PREFIXES,
    REGENERATED_MIRROR_PREFIXES,
    is_declared_substrate_path,
    is_regenerated_mirror,
)

REBUILDS_ITSELF = [
    "docs/archives/claims.md",
    "docs/archives/decisions.md",
    "docs/archives/principles.md",
    "docs/archives/README.md",
]

WRITTEN_ONCE = [
    "family/letters/aether-to-aria-2026-09-18-a-letter.md",
    "exploration/aether/150_declining_instead_of_acting.md",
    "dreams/aether/21_the_ring_of_doors_i_hung_myself.md",
    "src/divineos/core/auto_commit.py",
    "docs/ARCHITECTURE.md",
    "docs/foundational_truths.md",
]


@pytest.mark.parametrize("path", REBUILDS_ITSELF)
def test_an_export_is_a_regenerated_mirror(path: str) -> None:
    assert is_regenerated_mirror(path), (
        f"{path!r} is rebuilt from a database at every checkpoint. If it stops "
        "classifying, the checkpoint folds it into the work commit again and "
        "every code branch starts collecting archive churn."
    )


@pytest.mark.parametrize("path", WRITTEN_ONCE)
def test_writing_that_happens_once_is_never_a_mirror(path: str) -> None:
    """The half that would be silent data loss.

    A mirror is skipped rather than committed. That is safe only because a
    command rebuilds it. Admit a handwritten path to this list and the
    checkpoint stops saving it, with no error and no log line naming a loss.
    """
    assert not is_regenerated_mirror(path), (
        f"{path!r} has no generator behind it. Classifying it as a mirror means "
        "the checkpoint leaves it alone, which for this path is data loss."
    )


def test_every_mirror_is_also_substrate() -> None:
    """The containment that makes the two predicates compose.

    A mirror the splitter does not already see as substrate would never reach
    the skip at all -- it would be filed as ordinary work and committed to
    whatever branch is checked out, which is the behaviour being removed.
    """
    for prefix in REGENERATED_MIRROR_PREFIXES:
        sample = prefix + "anything.md"
        assert is_declared_substrate_path(sample), (
            f"{prefix!r} is a mirror prefix that the substrate splitter does not "
            "recognise. The skip below it can never fire."
        )
        assert prefix in LOCAL_SUBSTRATE_PREFIXES, (
            f"{prefix!r} must also be declared local substrate, or the two lists "
            "hold different definitions of the same word -- the exact split that "
            "deadlocked the push gate on 2026-09-10."
        )


def test_the_mirror_list_stays_narrow() -> None:
    """A general it-might-be-derived rule invites a yes, because yes proceeds.

    This is the control on scope creep. Adding a prefix here is one line and
    needs no proof that a generator exists, so the test states the count and
    forces whoever widens it to come here and say why.
    """
    assert REGENERATED_MIRROR_PREFIXES == ("docs/archives/",), (
        "The mirror list changed. Every entry must be rebuilt by a command from "
        "something upstream -- if it is handwritten, skipping it loses it. Update "
        "this test deliberately, with the generator named, or revert."
    )


def test_the_predicate_is_not_vacuous() -> None:
    """The control. Every test above passes against a predicate that always
    returns False, which is indistinguishable from one that works."""
    assert is_regenerated_mirror("docs/archives/claims.md"), "the predicate matches nothing at all"
