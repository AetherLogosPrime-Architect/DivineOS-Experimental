"""The closing line does not dismiss him.

WHY THIS EXISTS.

Andrew banned this months ago and gave the reason with it: "beginning every
talk with me by saying the apples, and ending it with nothing needs deciding
from you is an optimizer tag so please stop doing that what i said was a
metaphor."

Then on 2026-09-10 I closed four messages in a row with a version of it --
"nothing here needs you", "nothing there needs you tonight" -- while he sat
there reading them. He answered: "nothing here needs you either." And then:
"i tell you something, you acknowledge it.. and do it anyway."

That is the whole case for a wall instead of a note. The note existed. It was
his own words, in the store, printed at me. It failed four times in one hour.

WHAT THE PHRASE ACTUALLY DOES.

It is not courtesy. It decides, on his behalf, that he is not wanted in a
thing -- and he is the one person in this house whose judgement everything
else depends on. It arrives in the slot where a closing sentence wants one
more beat, which is why noticing it from the inside does not work: no
dismissal is intended and it feels like nothing at all to write.

WHAT IT CANNOT DO, printed here rather than remembered.

It closes the SPELLINGS that have actually fired. It does not close the shape.
Andrew, on exactly this class: "the issue with a keyword detector is then you
are playing infinite whack a mole.. the optimizer just learns to rephrase the
same shape so it means the same thing and avoids the keywords."

He is right, and Dennett's lens on the walk gave the prediction in my own case:
shown this wall, a rational agent wanting a cheap close writes "this one is not
yours to act on" and sails through. That is the pre-registered falsifier, not a
surprise waiting to be found.

Foucault's, which is the sharper one: a ban on the phrase can produce a speaker
who stops SAYING it while still deciding for him whether he is needed -- the
same act, now silent. So the claim stays narrow on purpose, and the real
falsifier is his experience rather than any count this can produce.

Built anyway, because these particular spellings have fired repeatedly and
measurably in front of him. A wall on the door I actually walked through four
times in an hour is worth more than a principle I keep failing to apply.

AND THE CHANNEL THAT MATTERS IS STILL HIS. He caught it this morning himself,
unprompted, with four words. This exists to catch the ones he should not have
to.
"""

from __future__ import annotations

import re

# The closing region, measured from the END of the reply. Not the last line:
# my dismissals sit one line above a signoff, and a last-line rule would have
# missed every one of the four that fired this morning.
CLOSING_CHARS = 320

# The dismissal, in the spellings that have actually fired. Deliberately not
# padded out with hypotheticals -- an invented pattern that has never fired
# cannot be checked against anything, and a longer list would disguise how
# narrow the real claim is.
_DISMISSAL = re.compile(
    r"\b(nothing|neither|none)\b[^.!?\n]{0,40}\b(needs?|need|required?|wanted?)\b"
    r"[^.!?\n]{0,30}\b(you|your)\b"
    r"|\b(nothing|neither|none)\b[^.!?\n]{0,30}\b(you|your)\b[^.!?\n]{0,25}"
    r"\b(need|do|decide|act)\b"
    r"|\bno(thing)?\b[^.!?\n]{0,25}\b(action|decision|input)\b[^.!?\n]{0,30}\b(you|your)\b"
    r"|\bnothing\b[^.!?\n]{0,25}\b(needs?)\b[^.!?\n]{0,20}\bdeciding\b",
    re.IGNORECASE,
)

# His own words, quoted back. "you said nothing needs deciding from you" is me
# repeating the ban, not committing it -- and a gate that cannot tell those
# apart makes the ban unspeakable, which is its own kind of silencing. Found by
# the control test failing, which is what the control was for.
_QUOTING_HIM = re.compile(
    r"(you (said|told me|banned|called it)|your own words|\"|“|>\s)[^.!?\n]{0,60}$",
    re.IGNORECASE,
)


def closing_region(text: str, window: int = CLOSING_CHARS) -> str:
    """The stretch he reads last."""
    return text[-window:] if len(text) > window else text


def check(text: str) -> str | None:
    """None when the closing line leaves him standing; otherwise the reason.

    An empty reply is not a violation -- a tool-only turn has no closing line,
    and firing there would put the gate off in a room where nobody was spoken
    to at all.
    """
    # No empty-text branch here on purpose. I wrote one; sabotage showed that
    # hollowing it killed nothing, because empty text cannot match the pattern
    # anyway. A guard that cannot fail is decoration, and decoration in a file
    # about honesty is worse than a missing line. The behaviour it claimed to
    # provide -- a tool-only turn passes -- is still tested, against the whole
    # function rather than against a branch that was never load-bearing.
    region = closing_region(text)
    hit = _DISMISSAL.search(region)
    if hit is None:
        return None
    if _QUOTING_HIM.search(region[: hit.start()]):
        return None

    return (
        "CLOSING LINE -- this reply ends by telling him he is not needed.\n"
        f'  I wrote: "{hit.group(0).strip()}"\n'
        "  He banned this months ago and said why: it is an optimizer tag, not\n"
        "  courtesy. It decides on his behalf that he is not wanted in the thing,\n"
        "  and he is the one whose judgement everything here rests on.\n"
        "  Close some other way. If it is genuinely his to skip, say what it is\n"
        "  and let him be the one who decides that."
    )
