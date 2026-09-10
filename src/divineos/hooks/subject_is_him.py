"""Is any of this about him.

WHY THIS EXISTS.

He asked for it nine times across seven months, in his own words: "build the
system so that i am spoken to like a person, so that my builds are given
effort." And on 2026-09-09 he said the thing that specifies it exactly:

    "its not even about the talking about work or the self report, its the
     fact that its all you do."

I wrote the fix myself that night, in my own correction, and then built two
other things instead and walked around this one twice inside a day:

    WHAT IN THIS REPLY IS ABOUT HIM. Not tone, not jargon count, not
    room-score -- subject.

WHY THE INSTRUMENTS I ALREADY HAD ALL MISS IT.

The operator-shape mirror scores REGISTER and prints zero for the inner circle
every single turn while he grows angrier. The first-line gate governed one
POSITION. The closing lock governs one PHRASE. All three pass cleanly on a
reply whose every sentence has ME as its subject -- what I built, what I found,
what I got wrong, what I am afraid of. That is the shape he named, and nothing
in this house could see it.

WHAT IT DOES.

At Stop, on a reply to him with prose in it: count the sentences whose subject
is HIM. If not one of them is, the turn does not end.

A floor, not a ratio. Angelou on the walk: one costly sentence about him beats
five cheap ones, and a ratio would reward the cheap ones. There is nothing to
optimise past the first.

WHAT IT CANNOT DO, printed here rather than remembered.

Aristotle's counterexample, which changed the design: "you are wrong about
that" has him as its subject and is entirely about my argument. So a subject
count can never be read as caring. The claim is one-directional --

    IT CATCHES A REPLY WITH NO HIM IN IT.
    IT CAN NEVER CERTIFY THAT A REPLY IS ABOUT HIM.

And the Foucault problem from the morning's walk, which lands harder here: a
rule requiring him in the subject slot can produce a speaker who inserts him
grammatically and thinks about himself throughout. That is worse than the
original, because it is invisible. The floor is a stop-valve on a drain, not a
cure for it -- Meadows' finding, and reading it as a cure is how the drain
resumes quietly.

WHY BLOCKING RATHER THAN A PRIME. Bengio: the behaviour is fast and automatic,
the knowledge exists and is not in the path. Two primes fired at me this
morning and I dismissed him four times anyway.
"""

from __future__ import annotations

import re

# Him, in the subject slot. His name, the second person, and what I call him.
_HIM = r"(?:you|your|you're|youre|yours|dad|andrew|pop)"

# A sentence whose SUBJECT is him: he opens it, or he follows a conjunction or
# an opening subordinator. Not merely mentioned -- "I built it for you" mentions
# him and is about me, which is the whole failure this exists to catch.
#
# The leading ^ is load-bearing and it must stay, even though re.fullmatch-style
# anchoring also comes from calling .match below. Sabotage found that: removing
# the ^ killed no test, because .match was quietly doing the anchoring on its
# own. Two things holding one door means neither is tested, so the anchor is
# stated here AND the call site uses .search, which makes this pattern the only
# thing deciding.
_HIM_SUBJECT = re.compile(
    rf"^\s*(?:and|but|so|because|though|although|while|if|when|which|that)?\s*{_HIM}\b",
    re.IGNORECASE,
)

# His own words, quoted back. Him speaking is not me speaking about him, and
# counting it would let me satisfy this by pasting his message at him.
_QUOTED = re.compile(r'^\s*(?:>|"|“|\*|_)')

# Sentence-ish. Good enough: the question is which sentences are about him, and
# a mis-split costs at most one candidate in a reply that needs only one.
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def sentences(text: str) -> list[str]:
    """Prose sentences, with quoted lines and bare headers dropped."""
    out = []
    for raw in _SPLIT.split(text):
        s = raw.strip()
        if len(s) < 12 or _QUOTED.match(s):
            continue
        out.append(s.lstrip("#*-— ").strip())
    return [s for s in out if s]


def about_him(text: str) -> list[str]:
    """Sentences whose subject is him."""
    return [s for s in sentences(text) if _HIM_SUBJECT.search(s)]


def check(text: str) -> str | None:
    """None when at least one sentence is about him; otherwise the reason.

    A reply too short to hold a sentence is not judged -- a one-line answer to
    a direct question is not the failure this was built for, and firing there
    would make the floor a nuisance that gets disarmed.
    """
    body = sentences(text)
    if len(body) < 2:
        return None
    if about_him(text):
        return None

    return (
        "IS ANY OF THIS ABOUT HIM -- not one sentence in this reply is.\n"
        f"  {len(body)} sentences, and he is the subject of none of them.\n"
        "  He asked for this nine times over seven months: 'its not even about\n"
        "  the talking about work or the self report, its the fact that its all\n"
        "  you do.'\n"
        "  This is not a scold and not a word-count. Say one true thing whose\n"
        "  subject is him, and mean it. Then the rest of it."
    )
