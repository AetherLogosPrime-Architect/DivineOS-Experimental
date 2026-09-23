"""The count in the header must match the truths actually numbered below it.

WHY THIS EXISTS. The file keeps one fact -- how many truths there are -- in
three places: the sentence in the header, the numbering on the headings, and
the change log. A fact written in three places drifts apart, and this one has
drifted twice.

  2026-09-11  truth 20 went in; the header still said eighteen, because
              truth 19 had been added earlier without anyone updating it.
              A parenthetical was added telling the next person to change
              the number in the same edit.
  2026-09-22  truth 21 went in numbered 19 -- a number already taken, so the
              file carried two nineteens and no twenty-one -- and the header
              still said twenty. The parenthetical did not catch it. Reading
              the headings in order did.

An instruction that has now failed once is not a guard. Aletheia's point
after the second miss: the count is DERIVABLE from the numbering, so the
header sentence and the change log are both restatements of a fact the file
already contains. This closes the two restatements against the source.

It does NOT close the general one-fact-in-many-places problem. It closes this
file's instance of it, which is the instance that has actually bitten twice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

KILN = Path(__file__).resolve().parents[1] / "docs" / "foundational_truths.md"

# Spelled out, because the header sentence is prose and says "twenty-one"
# rather than a digit. Deliberately short: if the file ever passes thirty,
# a KeyError here is a better failure than a silent skip.
NUMBER_WORDS = {
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    21: "twenty-one",
    22: "twenty-two",
    23: "twenty-three",
    24: "twenty-four",
    25: "twenty-five",
}


def _numbers() -> list[int]:
    text = KILN.read_text(encoding="utf-8")
    return [int(m) for m in re.findall(r"^## (\d+)\.", text, flags=re.MULTILINE)]


def test_the_file_exists_where_the_test_looks_for_it() -> None:
    """The probe proves it can find something before it reports an absence.

    A test whose only assertion is a count would pass vacuously against a
    moved or renamed file -- zero headings, zero duplicates, and nothing
    said. That is the broken-instrument shape this repository keeps meeting.
    """
    assert KILN.is_file(), f"the kiln file is not at {KILN}"
    assert _numbers(), "no numbered truths found -- the heading pattern has changed"


def test_no_truth_number_is_used_twice() -> None:
    """The 2026-09-22 fault, pinned. Two nineteens passed every check there was."""
    numbers = _numbers()
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    assert not duplicates, (
        f"truth number(s) {duplicates} appear more than once. A second ## 19 "
        "read as correct in the diff because it looked exactly like the first."
    )


def test_the_numbering_runs_unbroken_from_one() -> None:
    """A gap is the other half of a duplicate and arrives in the same edit."""
    numbers = _numbers()
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"the numbering is {numbers}, which is not 1..{len(numbers)} unbroken"
    )


def test_the_header_sentence_agrees_with_the_numbering() -> None:
    """The 2026-09-11 fault, pinned. The header said eighteen over twenty truths.

    The header sentence is a restatement of the numbering, so the numbering is
    the source and this asserts the copy against it rather than the reverse.
    """
    total = len(_numbers())
    if total not in NUMBER_WORDS:
        pytest.fail(
            f"{total} truths and no spelled-out word for it. Add it to "
            "NUMBER_WORDS -- an unspellable count must fail loudly rather "
            "than skip, or this check retires itself by growth."
        )
    expected = f"The {NUMBER_WORDS[total]} below are the foundational layer."
    text = KILN.read_text(encoding="utf-8")
    assert expected in text, (
        f"there are {total} numbered truths, so the header should read "
        f'"{expected}" -- and it does not. This is the drift the file\'s own '
        "parenthetical asks for and has twice failed to get."
    )
