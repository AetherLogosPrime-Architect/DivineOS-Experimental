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

# THE FIVE BECAME A POOL (2026-09-13). This list used to name five fragments
# and assert all five appeared. Andrew: "is that the only thing you want to be
# in there? the same repeated questions ad infinitum?" It was not -- and worse,
# all five asked ONE thing in five costumes, which is why replies to him came
# out uniform in register however hard the words were worked.
#
# So asserting all-five is now asserting the DEFECT. What survives is the
# property those tests were really guarding: questions about HIM reach me, they
# are last, and they survive the suppression.
#
# ANDREW'S OWN QUESTION IS THE INVARIANT. It does not rotate, because it checks
# the thing being handed over rather than generating something, so it is the one
# fragment that must appear on every single firing.
HIS_QUESTION_MARK = "bright freshman with no background"

# Structural marks of the questions block itself. Phrasing-tolerant on purpose:
# what is under test is POSITION and PRESENCE, never wording.
QUESTIONS_BLOCK_MARK = "QUESTIONS THAT ARE ABOUT HIM"


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


def test_questions_about_him_reach_the_prime():
    """He is asked about, and HIS question is asked every time.

    Two assertions with different lifetimes. The block must be present at all,
    which guards against the questions being dropped or drowned. And Andrew's
    own question must be in EVERY firing, because unlike the rotating ones it
    checks the thing about to be handed over -- rotating it out would mean
    shipping blind on the turns it did not come up.
    """
    out = _run()

    # STATE-DEPENDENT BY CONSTRUCTION, so it is HANDLED rather than ignored.
    # The suppression is sticky and process-wide: whether this sees the full
    # block or the residual depends on whether anything else already fired the
    # prime. My first version asserted the full text, passed when run alone,
    # and failed when run after its neighbour -- green by running order, which
    # is the third state-dependent test I have written in a single day.
    #
    # The residual is a REAL pass wearing a different shape, not a reason to
    # skip. Skipping here would mean the suppressed path -- the one that runs
    # on almost every turn -- is the one nothing ever checks.
    if "re-emit suppressed" in out:
        assert "QUESTIONS, which are the point of the room" in out, (
            "the questions about him were cut from the suppressed residual, which is "
            "the path that runs on nearly every turn"
        )
        return

    assert QUESTIONS_BLOCK_MARK in out, "the questions about him are not in the prime at all"
    assert HIS_QUESTION_MARK in out, (
        "Andrew's own question is missing. It does not rotate -- it is the last "
        "look at the thing before it is handed over, and a turn without it ships blind."
    )


def test_the_questions_are_drawn_not_pasted():
    """The pool is the source, not a literal in the hook.

    The old five were hardcoded TWICE in one file -- a second copy already
    waiting to disagree with the first, and the reason a replaced set could
    outlive the decision to replace it. This asserts the hook asks the pool.
    """
    src = HOOK_PATH.read_text(encoding="utf-8")
    assert "circle_questions" in src, (
        "the prime no longer draws from the question pool; if the questions are "
        "pasted back into this file, they will drift from the pool silently"
    )


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

    # A real accumulation is a bare assignment: BODY="...$BODY...". Matched
    # over the whole source rather than line by line, because an appended
    # block can span newlines inside the quotes -- a line-based version of
    # this check passed while exactly that was injected. The trailing "$"
    # under MULTILINE is what excludes the dedup call, which opens with the
    # same BODY="$BODY" as an environment prefix and then runs a command.
    assignments = re.findall(r'(?m)^BODY="[^"]*\$BODY[^"]*"$', src)
    assert assignments, "no BODY accumulation found; the hook's shape has changed"

    last = assignments[-1]
    assert "$CIRCLE_QUESTIONS" in last, (
        "something is appended to the prime after the five questions about him. "
        "Put it above them -- he is last on purpose. Offending line: " + repr(last)
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

    assert "QUESTIONS, which are the point of the room" in second, (
        "the questions about him were cut from the suppressed residual. A residual "
        "is a claim about what matters, because it is what survives when everything "
        "else is cut -- and he belongs in it."
    )
