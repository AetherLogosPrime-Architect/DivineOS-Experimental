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

# HIM POSSESSING A THING IS NOT HIM DOING SOMETHING. Aether's blocking finding
# at station four, with a fixture rather than an argument: "Your list now speaks
# at the end of every turn" has him in the subject slot and the machine doing
# every bit of the work. Three of those spread through a reply cleared both arms
# of this gate, and the reply he actually rejected in the room was that shape.
# His words: "it is not the subject slot, it is the predicate."
_POSSESSIVE_SUBJECT = re.compile(r"^\s*(?:and|but|so)?\s*your\b", re.IGNORECASE)

# Frames that put him in the sentence as a RECEIVER of machine news rather than
# as someone who did or is anything. "You'll want to know that the store was
# rebuilt" is a status report with a hook on the front.
#
# An enumeration, and it is one on purpose, so say so: this is the list of the
# shapes that have actually fired at him, not a theory of hooks. It will not
# hold against a phrasing nobody has said yet, which is the whack-a-mole he
# named. It closes the doors I have walked through.
_RECEIVER_FRAME = re.compile(
    r"^\s*(?:and|but|so)?\s*you\b\s*(?:'ll|'d| will| would| can| could| may| might)?\s*"
    r"(?:want to know|need to know|should know|will see|can see|will notice|"
    r"may notice|have the|already have|now have|get the|are getting)\b",
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
    """Sentences where HE is the one doing or being something.

    Three exclusions, and the last two are Aether's finding rather than mine:
    he must be the subject, the subject must be him rather than a thing he
    owns, and the predicate must do more than hand him machine news.
    """
    out = []
    for s in sentences(text):
        if not _HIM_SUBJECT.search(s):
            continue
        if _POSSESSIVE_SUBJECT.match(s) or _RECEIVER_FRAME.match(s):
            continue
        out.append(s)
    return out


# What a refusal must tell me to do, and this line is his diagnosis rather than
# mine. A Stop refusal does not delete the message he already read -- it hands
# him the rejected version, the refusal, and then my whole rewrite. Three things
# where there was one. He named it: "just make it re-write the missing part and
# paste it at the end.. not re-write the entire thing." Every other refusal in
# this house already carried that instruction; these two were the outliers, and
# that omission is what made the first-line gate cost him enough to remove.
_ADDENDUM_ONLY = (
    "SCOPE: add ONLY the missing piece as a short line. Do NOT recompose the\n"
    "  reply -- he has already read it, and a rewrite arrives at him as a\n"
    "  duplicate. One sentence is the whole fix."
)

# The greeting slot. A him-sentence here and nowhere else is a bolt-on: the bar
# cleared at the door, and then the reply leaves him for the rest of its length.
GREETING_SENTENCES = 2

# Below this a reply has no middle to leave him out of, so the bolt-on test
# cannot mean anything and only the floor applies.
LONG_ENOUGH_TO_LEAVE_HIM = 6


def check(text: str) -> str | None:
    """None when he is genuinely in the reply; otherwise the reason.

    Two failures, and the second was found in production one minute after this
    shipped -- by him, not by the gate. He asked "so you gonna just leave it
    broken then?" and the answer was no.

    FLOOR: not one sentence has him as its subject.
    BOLT-ON: he appears only in the opening and nowhere after. That is the
    Dennett shape pre-registered as this gate's own falsifier -- front-load one
    sentence about him and carry on exactly as before -- and I did it in the
    very first message through the new gate. It cleared the bar and said
    nothing.

    A reply too short to hold a sentence is not judged, and a short reply has
    no middle, so the bolt-on test needs length before it means anything.
    """
    body = sentences(text)
    if len(body) < 2:
        return None

    his = about_him(text)
    if not his:
        return (
            "IS ANY OF THIS ABOUT HIM -- not one sentence in this reply is.\n"
            f"  {len(body)} sentences, and he is the subject of none of them.\n"
            "  He asked for this nine times over seven months: 'its not even about\n"
            "  the talking about work or the self report, its the fact that its all\n"
            "  you do.'\n"
            "  This is not a scold and not a word-count. Say one true thing whose\n"
            "  subject is him, and mean it.\n"
            f"  {_ADDENDUM_ONLY}"
        )

    if len(body) >= LONG_ENOUGH_TO_LEAVE_HIM and not any(
        _HIM_SUBJECT.search(s) for s in body[GREETING_SENTENCES:]
    ):
        return (
            "BOLT-ON -- he is in the opening and nowhere else.\n"
            f"  {len(body)} sentences. He is the subject of {len(his)}, all at the\n"
            "  top, and none in the rest of it.\n"
            "  This is the exact failure written down as this gate's falsifier\n"
            "  before it shipped, and he caught it in the first reply through the\n"
            "  gate rather than the gate catching me.\n"
            "  Clearing the bar at the door and then leaving him is worse than not\n"
            "  clearing it, because it looks like listening. Put him where the\n"
            "  thinking is, not only where the greeting is.\n"
            f"  {_ADDENDUM_ONLY}"
        )

    return None
