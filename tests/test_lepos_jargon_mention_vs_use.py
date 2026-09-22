"""The jargon detector must not read an ordinary English sentence as a command.

Several of the tool names the detector watches for are also ordinary English
words -- cargo, node, python. The pattern used to match any one of them
followed by any word at all, so "that cargo is precisely what the publisher
refuses" read as a command invocation and the gate refused a plain-language
paragraph in the one room that exists for plain language.

Mention read as use. This module already knew about that distinction: the
wallclock check strips quoted spans before scanning, precisely so a forbidden
phrase said INSIDE quotes is not counted as said. The jargon scan never got
the same treatment, and this is the cost.

These tests pin both halves: the false fire stays dead, and a real invocation
is still caught. The second half matters more -- a narrowing that also blinds
the detector is not a fix.

WHY THE PROVENANCE GUARD IS HERE, stated accurately because I first got this
wrong in this very file. Checking my work, a bare one-line import of this
module resolved to the OTHER checkout on this machine -- there is a single
global editable-install slot, claimed by whichever tree installed last, and
that tree's copy still carries the unfixed pattern. I concluded the suite had
been testing the wrong house and wrote that here as fact. It had not: run
through the suite from this repo's root, the import resolves correctly, and
the guard below passes. The claim was wrong; the paragraph is corrected rather
than deleted, because the near-miss is the reason the guard stays.

What remains true is the part worth guarding: nothing IN the test says which
tree it is describing. Correct resolution depends on configuration outside
this file, and a test passing while pointed at another checkout would answer
confidently about a file the change never touched. So the module states where
it lives before any assertion about its behaviour is allowed to count.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import lepos_translation_gate
from divineos.core.lepos_translation_gate import _has_jargon

_REPO_SRC = Path(__file__).resolve().parent.parent / "src"


def test_module_under_test_is_this_repo() -> None:
    """Refuse to report on a sibling checkout's copy. See the module docstring."""
    where = Path(lepos_translation_gate.__file__).resolve()
    assert _REPO_SRC in where.parents, (
        f"imported {where}, which is not under this repo's src ({_REPO_SRC}). "
        "Every assertion below would be describing another tree."
    )


ENGLISH_SENTENCES = [
    # The sentence that actually fired the gate, 2026-09-18.
    "that cargo is precisely what the publisher refuses to carry",
    "the cargo was heavier than either of us expected",
    "every node in the chain has to agree before the thing moves",
    "the node that broke is the one nobody was watching",
    "a python in the garden is a fine reason to stay indoors",
]


@pytest.mark.parametrize("sentence", ENGLISH_SENTENCES)
def test_ordinary_english_is_not_a_command(sentence: str) -> None:
    fired, samples = _has_jargon(sentence)
    assert not fired, f"read plain English as jargon: {samples}"


REAL_INVOCATIONS = [
    "cargo build --release",
    "run git commit when the checks pass",
    "pip install the package first",
    "divineos extract closes the session",
    "npm run test before pushing",
]


@pytest.mark.parametrize("command", REAL_INVOCATIONS)
def test_real_invocations_still_caught(command: str) -> None:
    fired, _ = _has_jargon(command)
    assert fired, "stopped catching an actual command invocation"
