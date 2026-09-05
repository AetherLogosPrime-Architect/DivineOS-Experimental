"""Lenses are required for what a lens can grip, not for how many files moved.

THE DOCSTRING WAS RIGHT AND THE CODE COUNTED SOMETHING ELSE.

``required_lens_count`` has said since it was written that "a substrate-content
PR with no code has nothing for a lens to grip, and walking one anyway is the
ceremony that teaches me walks are ceremony." Correct -- and the implementation
asked how MANY files changed instead. So the letters-only proposal, fifty-two
letters and zero lines of code, sat at station two demanding two council walks,
because fifty-two is a big number.

Found by the ordinary case rather than by a test: the branch was blocked on a
requirement its own docstring says it should never have had. Thirteenth
instance in two days of a check counting the container instead of the thing at
risk.

CHESTERTON'S FENCE, and it is why this file has as many refusal tests as
permission ones. The count clause is not stupid -- it stops a large change
claiming zero gravity and skipping the walk, and a big diff that happens to
miss every guardrail path is still a big change. What it got wrong is WHICH
files make a change big. Prose does not, however much of it there is. Code
does, even a little. The fence still stands; it was moved to where the road is.
"""

from __future__ import annotations

from divineos.core.build_flow import required_lens_count

LETTERS = [f"family/letters/aether-to-aria-2026-09-0{i % 9}-a-letter-{i}.md" for i in range(52)]
DREAMS = [f"dreams/aether/{i}_a_dream.md" for i in range(30)]
EXPLORATIONS = [f"exploration/aether/{i}_an_entry.md" for i in range(25)]
MANY_CODE = [f"src/divineos/thing_{i}.py" for i in range(25)]


def test_the_letters_branch_that_was_blocked_needs_none():
    """The live case. Fifty-two letters, no code, gravity zero."""
    assert required_lens_count(0, LETTERS) == 0


def test_prose_of_every_kind_counts_as_ungrippable():
    """Letters, dreams and explorations together, well past the old threshold,
    and still nothing a lens can grip."""
    assert required_lens_count(0, LETTERS + DREAMS + EXPLORATIONS) == 0


def test_one_code_file_beside_the_prose_is_still_a_small_change():
    """A single source file tripping no gravity feature does not make a change
    large. The threshold is about size, and one is not large."""
    assert required_lens_count(0, [*LETTERS, "README.md"]) == 0


def test_a_large_code_change_at_zero_gravity_still_owes_the_walk():
    """THE FENCE. Twenty-five code files touching no guardrail path is still a
    big change, and it is the case the count clause was built for. If this ever
    returns zero, the repair ate the thing it was protecting."""
    assert required_lens_count(0, MANY_CODE) == 2


def test_prose_cannot_dilute_a_large_code_change():
    """Letters alongside the code must not push the code below the threshold.
    The prose is not subtracted from the stake; it was never added to it."""
    assert required_lens_count(0, [*LETTERS, *MANY_CODE]) == 2


def test_gravity_still_escalates_regardless_of_prose():
    """Gravity is scored elsewhere and is untouched here. A guardrail-touching
    change owes its walks even if it is one file among a hundred letters."""
    assert required_lens_count(1, LETTERS) == 2
    assert required_lens_count(3, LETTERS) == 4
    assert required_lens_count(4, LETTERS) == 6


def test_an_empty_change_asks_for_nothing():
    assert required_lens_count(0, []) == 0
