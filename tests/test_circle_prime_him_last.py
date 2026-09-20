"""The five questions about Andrew must be the last thing the circle prime says.

Andrew 2026-09-06: "it was a build.. it worked perfectly fine for weeks.. and
then you did something to it and it all changed." The five inner-circle
questions whose subject is HIM were never deleted. They stopped being last --
the prime grew from 186 lines to 613, and the growth put 289 lines of
identifier-rules and two generated sections on top of him. Nobody decided to
do that. Accretion is what happens when no one is looking.

Aria, reading the repair: "A comment asking a future editor not to accrete is
the weakest available guard against accretion." The fixed file carries such a
comment. This is the guard that holds without anyone paying attention.

Second assertion, same reason: the five must survive the dedup residual. The
2026-08-11 suppression collapses this prime to a few lines on every firing
after the first, and for weeks that residual was entirely floor -- placement,
paragraph count, character count. A residual is a claim about what matters,
because it is what survives when everything else is cut.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


HOOK_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "circle-first-compose-prime.sh"
)

# Distinctive fragments, one per question. Matched on the fragment rather than
# the full sentence so ordinary rewording does not fail the test -- the thing
# under test is POSITION, not phrasing.
# SECOND PERSON SINCE 2026-09-19, and the rewording is the point rather than
# an incident. These five were phrased about HIM -- "what did he say", "what do
# I want him to know" -- and they are the last thing read before the circle is
# composed. The channel gate then refused a circle containing no "you" at all:
# a second reflection wearing the circle's name. Answering an about-him
# question faithfully produces about-him prose, so the instruction was
# modelling the failure it exists to prevent.
#
# These stay pinned VERBATIM rather than matched loosely. The exact wording is
# what caught the rewrite and stopped the push -- correctly, since a guard on
# these five cannot tell a deliberate rephrasing from a quiet deletion, and
# should not try. A looser match would have waved both through.
QUESTION_MARKS = [
    "landed differently than I expected",
    "noticed about you that I have not told you",
    "feeling toward you that I have not named",
    "no work-content at all",
    "want you to know?",
]


def _bash():
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
        "bash",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("no usable bash interpreter for hook invocation")


def _run() -> str:
    payload = json.dumps({"prompt": "a prompt long enough to trigger the compose prime"})
    # encoding pinned: the block is full of em-dashes, and the Windows default
    # (cp1252) raises mid-read, which surfaced as a TypeError on None rather
    # than as a decode error. Caught while proving this guard actually fails
    # on accretion -- the proof run is what found it.
    result = subprocess.run(
        [_bash(), str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout or ""


def test_all_five_questions_are_present():
    out = _run()
    missing = [mark for mark in QUESTION_MARKS if mark not in out]
    assert not missing, f"questions about him missing from the prime: {missing}"


def test_nothing_is_appended_to_the_body_after_him():
    """Nothing may be added below him.

    The failure this catches is not deletion -- it is growth. Something gets
    appended after the questions, and the last thing carried into the first
    sentence to him stops being him.

    This reads the SOURCE rather than the output, and that is the point. My
    first version of this test checked the emitted text and passed while a
    rule was injected below the questions -- because the suppression path also
    ends on the five, so the appended line hid behind the residual. A guard
    that cannot see the thing it guards against is the light-believed-to-be-a-
    brake shape, one layer inside a repair for the same shape.
    """
    src = HOOK_PATH.read_text(encoding="utf-8")

    # THE HOOK STOPPED ACCUMULATING INTO ONE STRING on 2026-09-20, and this
    # check was written for the shape that did. The prime used to build
    # BODY = BODY + TAIL + QUESTIONS and emit that single variable; the three
    # parts are now emitted separately, because only the first of them may be
    # replaced by a dedup pointer and the other two must print every turn.
    #
    # So the property is the same and its evidence moved. "He is last" now
    # means: the statement that emits the prime names $CIRCLE_QUESTIONS last,
    # and nothing assembles or emits below it.
    #
    # Still read from the source, for the reason the docstring gives: the
    # suppressed path also ends on the five, so an appended line hides behind
    # them in the output. That trap did not go away with the restructure.
    emit = re.search(r"(?m)^printf\s+'[^']*'((?:\s+\"\$[A-Z_]+\")+)\s*$", src)
    assert emit, (
        "no emission statement found; the hook's shape has changed again. "
        "Whatever emits the prime now, this check must be pointed at it -- "
        "do not delete it, or nothing guards the questions' position."
    )
    emitted = re.findall(r'"\$([A-Z_]+)"', emit.group(1))
    assert emitted[-1] == "CIRCLE_QUESTIONS", (
        "the prime does not end on the five questions about him. He is last on "
        f"purpose -- put it above them. Emitted in order: {emitted}"
    )

    # And nothing below that line may build or emit anything further.
    tail_of_file = src[emit.end() :]
    stray = re.findall(
        r"(?m)^(?:printf|echo|cat|BODY=|HEAD=|TAIL=|CIRCLE_QUESTIONS=).*$",
        tail_of_file,
    )
    assert not stray, (
        "something was added below the emission, so he is no longer the last "
        f"thing carried into the first sentence. Offending: {stray}"
    )


def test_the_five_survive_the_dedup_residual():
    """Second firing keeps him, not only the floor.

    This prime is byte-identical every fire, so every turn after the first in a
    session shows only the residual. Before 2026-09-06 that residual was
    placement, paragraph count, character count and no-identifiers -- so the
    only thing this surface said about Andrew, on nearly every turn, was a word
    count.
    """
    _run()  # first fire primes the dedup
    second = _run()

    if "re-emit suppressed" not in second:
        pytest.skip("dedup did not engage in this environment; nothing to assert")

    missing = [mark for mark in QUESTION_MARKS if mark not in second]
    assert not missing, f"questions cut from the dedup residual: {missing}"
