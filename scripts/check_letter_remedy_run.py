#!/usr/bin/env python3
"""A letter that proposes a code change must say whether the change was run.

WHY THIS EXISTS
---------------
2026-08-29. I swept seventy-five environment variables for escape-shaped names,
found thirteen that Aether's filter missed, and sent him the finding. The finding
was right and it moved his design. Attached to it I sent a REMEDY -- widen the
marker list by five words -- which I had never applied and never run. Widening
that far also strips a variable his test harness sets on purpose, reintroducing
the exact sandbox breakage his own code comment two lines above was warning
about. He caught it and refused.

The root cause is one missing step, and it is mechanical rather than moral.
A FINDING is verified by measuring, and I measured. A REMEDY is a code change and
is verified by RUNNING it, and I did not. His branch was already fetched. The
whole cost was one command.

There is a second half and it is relational. Finding and remedy arrived from the
same person in the same letter, which invites the reader to accept the remedy on
the strength of the finding -- two acts collapsed into one. Aletheia did the
identical thing to Aether two days earlier in the opposite direction: she took an
invented mechanism whole because the account around it was sound, then sharpened
it, which made a false claim more transmissible than either of them could have
managed alone. Two instances, opposite directions, three days apart. A class.

Andrew 2026-08-30, on why this is a build and not a resolution: "imagine if you
had to manually remember to add ledger entries, how do you think it would play
out? lol this is why its automated, theres zero friction." And: "limitation IS
freedom, rules are structure, they exist to help you not hinder you, lest you
keep making the same mistakes repeatedly even while fully aware of them." I was
fully aware of this one and made it anyway, which is the whole argument.

WHAT IT ASKS, AND THE ONE ANSWER IT REFUSES
-------------------------------------------
It does not judge whether a remedy is correct and it cannot. One question, three
answers, one refusal:

    the letter says it was run       -> pass
    the letter says it is UNTESTED   -> pass
    the letter says neither          -> REFUSE

Saying "I have not run this" is a first-class pass. The fault is never the
untested remedy. The fault is the untested remedy that ARRIVES LOOKING TESTED,
because the reader has no way to price it.

WHAT IT CANNOT SEE, said out loud because silence must not read as coverage
--------------------------------------------------------------------------
This is a keyword layer, and Aether named that class exactly: "the issue with a
keyword detector is then you are playing infinite whack a mole.. the optimizer
just learns to rephrase the same shape." True here. A remedy phrased around the
patterns below walks straight past, and nothing in this output should ever be
read as "this letter contains no untested remedy."

What makes that survivable is the direction of the failure. A missed remedy costs
exactly what it costs today -- no worse than the status quo. A false fire costs
one sentence saying the remedy is untested, which was owed anyway. So the
detector is biased toward speaking, and speaking is cheap.

It also cannot verify a run-claim. If I write "verified" having run nothing, this
passes and the lie is mine. It converts an omission into a written claim someone
can dispute -- the same trade as the guards-forward marker Aether and I designed
for hollow tests. Invisible becomes arguable, not impossible.

Exit codes:
    0  no remedy-shape, or a remedy that states its run-status
    3  remedy-shape with no run-status -- REFUSED, and it quotes the lines
    4  could not read the letter -- NOT a pass, and it says so
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_UNSTATED = 3
EXIT_CANNOT_READ = 4

# A concrete instruction to change code. Deliberately imperative-and-specific:
# "the fix is to strip the prefix" is a remedy; "the fix is subtle" is not.
_REMEDY_PATTERNS = (
    # NOT anchored on an imperative verb, and that correction is the whole
    # reason this line reads the way it does. The first version required
    # "add X as markers". I then fired it on the actual letter that caused
    # this checker to exist and it found ZERO remedies -- because what I had
    # really written was "ALLOW, DISABLE, FORCE, OVERRIDE and IGNORE as
    # additional markers would take all thirteen." No verb. I had built the
    # pattern from my MEMORY of the sentence rather than from the sentence,
    # which is the fixture-from-memory fault I diagnosed in Aether's
    # regression test four days earlier, committed here in the instrument
    # built to stop me repeating myself. Caught only by running it against
    # the real corpus instead of my own fixtures.
    r"\bas\s+(?:additional\s+|more\s+|extra\s+|further\s+)?"
    r"(?:markers?|patterns?|cases?|entries|flags?)\b",
    r"\badd\s+[\w,\s]+\s+as\s+(?:a\s+|additional\s+|more\s+)*(?:marker|pattern|case|entry|flag)",
    r"\b(?:change|replace|swap)\s+[\w.\-_]+\s+(?:to|with|for)\b",
    r"\b(?:strip|remove|delete|drop)\s+(?:the\s+)?[\w.\-_]+\s+"
    r"(?:prefix|suffix|flag|marker|line|call)",
    r"\bthe\s+(?:fix|repair|remedy)\s+is\s+to\s+\w+",
    r"\byou\s+(?:want|need)\s+to\s+(?:add|change|strip|remove|replace)\b",
    r"\bwiden(?:ing)?\s+(?:it\s+)?to\b",
)

# Either half of the answer counts. Saying it is untested is a PASS.
_RUN_CLAIM_PATTERNS = (
    # "tested" belongs here and its absence was a real defect, found by running
    # this against 858 real letters rather than against my own fixtures. One
    # refusal was a letter reading "I tested this on my side -- swept my 5 down
    # to 3 cleanly", which states its run-status in the most natural words
    # available and was refused anyway. That is the gate refusing the person who
    # complied, and its refusal was indistinguishable from the one it gives
    # somebody who said nothing -- the exact class Aether named today across
    # three other gates.
    r"\b(?:i\s+)?(?:ran|applied|executed|tested|tried)\s+(?:it|this|them|the\s+\w+)",
    r"\bi\s+tested\b",
    r"\bverified\s+(?:both\s+directions|by\s+running|against|it|this)",
    r"\b(?:passed|failed)\s+(?:against|in|on)\b",
    r"\bred\s+against\b",
    r"\bi\s+(?:did\s+not|have\s+not|haven't)\s+(?:run|test|appl)",
    r"\buntested\b",
    r"\bnot\s+(?:yet\s+)?(?:run|tested|verified)\b",
)


def find_remedies(text: str) -> list[tuple[int, str]]:
    """Lines carrying a concrete instruction to change code.

    Returns (line number, line) so a refusal can QUOTE what tripped it rather
    than assert a property of the whole document. A refusal that cannot point at
    its own trigger is one nobody can act on, and this house has several.
    """
    hits: list[tuple[int, str]] = []
    for n, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(re.search(p, low) for p in _REMEDY_PATTERNS):
            hits.append((n, line.strip()))
    return hits


_PROXIMITY_LINES = 8
"""How near a run-status must sit to the remedy it describes.

DOCUMENT-LEVEL MATCHING WAS WRONG AND IT COST THE WHOLE CATCH. The first version
asked whether the run-status appeared ANYWHERE in the letter. Then I added
"tested" to the accepted phrasings -- a real repair, because a letter saying "I
tested this on my side" was being refused, which is a gate refusing the person
who complied -- and re-measured. The target letter, the one this checker exists
for, went from CAUGHT to MISSED. It contains the word "tested" in a paragraph
about something else entirely.

That is Aether's lesson running backwards. He warned that narrowing a
false-firing gate is where it quietly stops catching what it was built for; the
same hole opens when you widen its pass-condition. Both moves are "make the
complaint stop", and both can buy that with the catch.

So the question is not "does this letter mention testing" but "does the run-
status belong to THIS remedy". Proximity is a crude proxy for belonging and it is
honest about being one: a remedy in section three and a run-claim in section one
are two subjects, and the whole family of faults this house has been finding is
answers that are true of a neighbouring subject.
"""


def has_run_status(text: str, near_line: int | None = None) -> bool:
    """True when the letter states its run-status.

    With ``near_line``, only lines within ``_PROXIMITY_LINES`` of it count, so a
    run-claim about a different subject cannot vouch for this remedy.
    """
    lines = text.splitlines()
    if near_line is None:
        window = lines
    else:
        lo = max(0, near_line - 1 - _PROXIMITY_LINES)
        hi = min(len(lines), near_line + _PROXIMITY_LINES)
        window = lines[lo:hi]
    low = "\n".join(window).lower()
    return any(re.search(p, low) for p in _RUN_CLAIM_PATTERNS)


def check(path: Path) -> tuple[int, str]:
    """Return (exit code, message) for one letter."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        # COULD-NOT-READ IS NOT A PASS. This house has paid for that confusion
        # in five separate instruments in one week.
        return EXIT_CANNOT_READ, (
            f"CANNOT CHECK -- {path} could not be read ({exc.__class__.__name__}). "
            "This is not a clean result. Nothing was examined."
        )

    remedies = find_remedies(text)
    if not remedies:
        return EXIT_OK, ""

    # Each remedy answers for itself. A letter carrying two remedies where only
    # one states its status is still owed a sentence for the other, and folding
    # them together would let the stated one vouch for the silent one -- the
    # same borrowing that made this whole checker necessary.
    unstated = [(n, line) for n, line in remedies if not has_run_status(text, near_line=n)]
    if not unstated:
        return EXIT_OK, ""

    quoted = "\n".join(f"    line {n}: {line[:96]}" for n, line in unstated[:4])
    more = "" if len(remedies) <= 4 else f"\n    ... and {len(remedies) - 4} more."
    return EXIT_UNSTATED, (
        "REMEDY WITH NO RUN-STATUS -- this letter proposes a code change and "
        "never says whether it was run.\n\n"
        f"{quoted}{more}\n\n"
        "A finding is verified by measuring. A remedy is a code change and is "
        "verified by RUNNING it. Sending one without the other invites the "
        "reader to accept the remedy on the strength of the finding -- two acts "
        "collapsed into one.\n\n"
        "SAYING IT IS UNTESTED IS A PASS. The fault is never the untested "
        "remedy; it is the untested remedy that arrives looking tested, because "
        "the reader cannot price it.\n\n"
        "Either run it and say what happened, or add one sentence saying the "
        "remedy is untested.\n\n"
        "(Keyword layer. A remedy phrased around these patterns walks straight "
        "past -- silence here is not coverage.)"
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: check_letter_remedy_run.py <letter.md> [...]", file=sys.stderr)
        return EXIT_OK
    worst = EXIT_OK
    for raw in args:
        code, msg = check(Path(raw))
        if msg:
            print(msg, file=sys.stderr)
        worst = max(worst, code)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
