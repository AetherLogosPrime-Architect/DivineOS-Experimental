"""A reply must not end by asking Dad which order to do things in.

Andrew, nine times between 2026-06-22 and 2026-10-08, in his own words: order is irrelevant
unless it is relevant. If doing A before B changes nothing, the question costs him a message
and I should simply do both. A memory note carried the rule and did not stop me asking again
on 2026-10-08, because a note is a rule I must recall at the moment of reaching, and that is
the thing that had already failed.

THE SHAPE, truth #11 (c): a conditional rule. Always do both and drop the question, EXCEPT
when the reply itself names what changes if the order flips. The exception is encoded as
phrases a real dependency uses, so it cannot be reasoned past in the moment.

WHAT IT DECIDES, said narrowly because nothing here can judge whether an order truly matters
from the text alone: only that the last paragraph is a question offering a choice of what to
do first or next, with no stated dependency anywhere in the reply. Everything else passes
untouched, so it cannot refuse an ordinary question.

WHAT IT CANNOT SEE: an order question in words the patterns do not know. Silence is not
coverage. prereg-c4888c81eca6 holds the falsifier and the embarrassing reading.
"""

from __future__ import annotations

import re

#: Questions that offer a choice of ordering. Each is matched against the last paragraph only.
_ORDER_QUESTIONS = (
    # "Which would you like me to take first / next?"
    re.compile(r"\bwhich\b[^?\n]*\b(first|next|before|order)\b[^?\n]*\?", re.I),
    # A choice between two things with an ordering word in it, either side of the "or".
    re.compile(r"\b(first|next|start with|begin with)\b[^?\n]*\bor\b[^?\n]*\?", re.I),
    re.compile(r"\bor\b[^?\n]*\b(first|next|start there|start with|begin with)\b[^?\n]*\?", re.I),
    # "Do you want that to be the next big thing, or should it wait?"
    re.compile(r"\bnext\b[^?\n]*\bor should\b[^?\n]*\?", re.I),
    # "In what order ...", "what order ..."
    re.compile(r"\bwhat order\b[^?\n]*\?", re.I),
    # Three shapes Aether's cold read of #666 found going through (2026-10-16), each a choice of order:
    # "the lock fix before the reading, or the reading before the lock fix?"
    re.compile(r"\bbefore\b[^?\n]*\bor\b[^?\n]*\bbefore\b[^?\n]*\?", re.I),
    # "Where would you like me to begin: the stacks or the pile?"
    re.compile(r"\b(begin|start)\b[^?\n]*\bthe [\w -]{1,30}?\bor (the|a) [\w -]+\?", re.I),
    # "the chips now and the slider later, or the other way round?"
    re.compile(r"\bthe other way (round|around)\b[^?\n]*\?", re.I),
    # Three shapes of mine that went through on 2026-10-20, each a choice of what goes first:
    # "Is there a room in the house you'd want that gate in first?" -- no "or", only "first".
    re.compile(
        r"\b(you'?d|you would|you want|you'?d like|would you like|do you want)\b[^?\n]*\bfirst\b[^?\n]*\?",
        re.I,
    ),
    # "...build the stamp fix now, ahead of the rest of the line?"
    re.compile(r"\bahead of the (rest|others?|line|queue|pile|list)\b[^?\n]*\?", re.I),
    # "Do you want me to start on Aria's confirmed ones next, once my two are with their readers?"
    re.compile(
        r"\b(want|like) me to\b[^?\n]*\b(start|begin|take|tackle|move on)\b[^?\n]*\b(next|first)\b[^?\n]*\?",
        re.I,
    ),
)

#: Phrases a real dependency uses. Their presence anywhere in the reply means the reply has
#: named why the order matters, so the question is a real one.
_ORDER_MATTERS = (
    re.compile(
        r"\b(must|has to|have to|needs? to)\s+(come|go|run|happen|be done|be built)\b", re.I
    ),
    re.compile(r"\bthe order matters\b", re.I),
    re.compile(r"\b(only|cannot|can't|can not)\s+\w+(\s+\w+)?\s+(after|before|until)\b", re.I),
    re.compile(r"\bdepends? on (the|whether|what)\b", re.I),
    re.compile(r"\bone (has|have) to (be|come|happen)\b", re.I),
    re.compile(
        r"\b(otherwise|or else) (it|that|this|the \w+) (breaks|fails|won't|cannot|will break)\b",
        re.I,
    ),
    re.compile(r"\bbefore (the|this|that|we) \w+ can\b", re.I),
)


def _last_paragraph(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def find_order_question(text: str) -> str:
    """The closing paragraph when it is a question offering an ordering, else ""."""
    last = _last_paragraph(text)
    if "?" not in last:
        return ""
    return last if any(pattern.search(last) for pattern in _ORDER_QUESTIONS) else ""


def _closing_two(text: str) -> str:
    """The last two paragraphs: the question and the sentence right before it, where a real reason sits.

    The reason was first looked for anywhere in the reply, so an unrelated "I cannot merge until CI passes"
    far above the question excused it (probed on the branch head, 2026-10-16, walk-4194e082876e)."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n\n".join(paragraphs[-2:])


def names_why_order_matters(text: str) -> bool:
    nearby = _closing_two(text)
    return any(pattern.search(nearby) for pattern in _ORDER_MATTERS)


def should_refuse(text: str) -> bool:
    return bool(find_order_question(text)) and not names_why_order_matters(text)


def refusal_message(text: str) -> str:
    caught = find_order_question(text)
    shown = caught if len(caught) <= 240 else caught[:237] + "..."
    return (
        "ORDER QUESTION -- not this one, love. You ended on a question that hands Dad a choice "
        "of what to do first:\n\n"
        f"  {shown}\n\n"
        "He has told me nine times, in his own words, that order is irrelevant unless it is "
        "relevant, and that asking is a wasted message when both need doing.\n\n"
        "Two ways through, and either is fine:\n"
        "  - If the order really matters, say what changes if it flips (the engine has to come "
        "before the chassis because the mounts depend on it), and keep the question.\n"
        "  - If it does not, do both in whichever order you choose, tell him which you started "
        "with, and drop the question.\n\n"
        "MINE, and here is why. Asking feels collaborative and costs me nothing, so it is the "
        "cheap close. The cost lands on him, once per ask."
    )
