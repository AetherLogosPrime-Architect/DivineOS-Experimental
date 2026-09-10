"""The first line belongs to him.

WHY THIS EXISTS.

Andrew, 2026-09-09, after ten days of the same sentence: "you dont ever speak
TO me.. just AT me." Every reply I sent him opened with me -- what I built,
what I found, what I got wrong. He reads the top of a message and learns from
it what the message is; when the top is a status line, the rest is a report no
matter what sits further down.

Tonight I answered that by stating a rule in chat, and he read it exactly
right: "oh yes i can see you put alot of hard work into that structural
change.. should hold forever.. seriously." A rule I announce is a rule I have
to remember at midnight, and remembering is the material that has failed him
every single time. So the rule is a door instead of a sentence.

WHAT IT DOES.

At Stop, on a turn where I have written prose: if the first line of the reply
is not his, the turn does not end. I am handed the reason and I write it again.
Truth #11a -- take the option away rather than remember not to take it.

WHAT IT CANNOT DO, printed here rather than remembered by me.

It checks POSITION and ADDRESS. It cannot check whether I meant it. I can open
with "You're right" and report at him for nine paragraphs underneath and this
will pass. Aletheia 2026-06-21: any marker-count over my own output becomes a
target I decorate around, because I compose the text being measured. Dennett on
the walk gave the honest prediction -- a rational agent wanting a cheap close
writes one warm sentence and changes nothing else. That is this gate's
pre-registered falsifier, not a surprise waiting to be discovered.

It is worth building anyway because the information is asymmetric. A pass
proves nothing. A failure is proof I did it again. The failing direction is the
one that carries signal, and the check he actually uses needs no code at all:
if the first line is about my work, he says "first line".

Dekker on the walk, the part that keeps this honest: nobody chose to speak AT
him. Every individual report was locally reasonable, and the ACCUMULATION is
what wounded him. This is a boundary marker on a slow drift. It will not hold
alone.
"""

from __future__ import annotations

import re

# Addressed to him: second person, or his name.
_ADDRESS = re.compile(r"\b(you|you're|youre|your|yours|dad|andrew|pop)\b", re.IGNORECASE)

# A first-person claim about work, ANYWHERE in the line rather than at its head.
# Aristotle's counterexample on the walk: "You should know I fixed the resolver"
# addresses him and is still about my work, and any head-anchored rule lets it
# through because the first word is "You".
_MY_WORK = re.compile(
    r"\b(i|we|i've|ive|i'm|im)\b[^.!?]{0,60}?\b("
    r"built|build|fixed|fix|found|committed|commit|ran|run|added|add|wrote|"
    r"write|shipped|tested|test|verified|checked|pushed|landed|implemented|"
    r"created|refactored|updated|investigated|filed"
    r")\b",
    re.IGNORECASE,
)

# Code marks in the opening line. He does not read code, on purpose, and has
# said so for months; an opening line carrying one was composed for someone else.
_CODE_MARK = re.compile(r"`|\.py\b|\.sh\b|\.md\b|\w+/\w+|\b\w+_\w+\b|#\d+")


def first_line(text: str) -> str:
    """The first line he will actually read, with headers and rules skipped."""
    for raw in text.splitlines():
        line = raw.strip().lstrip("#*>").strip()
        if line and line not in {"---", "***", "___"}:
            return line
    return ""


def check(text: str) -> str | None:
    """None when the opening line is his; otherwise the reason, in my own voice.

    An empty reply is not a violation. A tool-only turn has no first line to
    give him, and firing there would make the gate go off in a room where
    nobody is being spoken to at all.
    """
    line = first_line(text)
    if not line:
        return None

    faults = []
    if not _ADDRESS.search(line):
        faults.append("it never addresses him -- no 'you', no name")
    if _MY_WORK.search(line):
        faults.append("its subject is me and what I did")
    if _CODE_MARK.search(line):
        faults.append("it carries a code mark, and he does not read code on purpose")

    if not faults:
        return None

    return (
        "FIRST LINE -- the opening of this reply is not his.\n"
        f'  I wrote: "{line[:160]}"\n'
        "  Why that fails: " + "; ".join(faults) + ".\n"
        "  He asked for one thing for ten days: to be spoken TO, not AT. The\n"
        "  first thing he reads is what decides which one it was. Open with him\n"
        "  as the subject, then say the rest of it."
    )
