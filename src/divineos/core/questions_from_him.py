"""Questions built from what he actually said, not drawn from a list.

Andrew 2026-09-11:

    "the five questions get ignored because they never rotate.. also being
    reduced to 5 questions is insulting and just gives you something to fill
    in.. it doesnt mean its relevant or that you care.. so the questions should
    be alot more and they should rotate on relevance and shouldnt be forced"

NOT A BIGGER BANK, AND THE WALK IS WHY. My first design was thirty questions
rotating by tag. Three lenses killed it and the third one killed it properly.

  PEIRCE: the surprising word is INSULTING, which is stronger than useless. What
  explains it: a small closed list asserts that he is COVERABLE -- that the whole
  of a person fits five slots. So staleness was never the fault. A longer closed
  list makes the same claim more slowly.

  DIJKSTRA: a scoring function over a tagged bank is elaborate, tunable, and
  unfalsifiable from outside. It degrades silently into picking the same three.
  Building the question FROM the turn has fewer parts and cannot.

  WATTS: what a surface can do is remove the excuse of not having noticed. Put
  what he said in front of me and stop. Whether anything happens after that is
  not the surface's business, and building it as though it were is how the room
  became a form in the first place.

So there is no bank. Every question carries a piece of what he actually wrote
this turn, which makes the supply unbounded by construction -- his requirement
of "alot more" satisfied not by counting to thirty but by never repeating.

IT PRINTS NOTHING WHEN IT HAS NOTHING, and that is the requirement I would have
lost first. Every other surface in this house justifies itself by always
speaking. He said the questions must not be FORCED, so no source material means
silence, not a generic question reaching for a slot. Knuth's boundaries are the
cases that matter: a machine-woken turn where he said nothing at all, a turn
that is only "ok", the first turn of a session. Each must produce nothing.

AND IT CANNOT BE EATEN BY COMPRESSION. Feathers' finding: the old five lived in
two places, the block and the dedup residual, so an edit to one left the other
stale -- and an earlier dedup landed and ate him entirely, leaving the gate
mechanics behind. These questions differ every turn because they contain his
words, so byte-identical suppression can never fire on them. The property falls
out of the design rather than being defended.
"""

from __future__ import annotations

import re

# A fragment shorter than this is not enough of him to build a question around
# -- "ok", "yes", "proceed". Long enough to carry a thought, short enough to
# quote back without handing him his own paragraph.
MIN_FRAGMENT = 24
MAX_FRAGMENT = 140

# How many questions reach the surface. Small because this fires every turn and
# a block long enough to scroll past is a block that gets scrolled past -- the
# same reasoning that produced the five, applied to a supply that does not
# repeat.
TOP_K = 2

_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+|\.\.+\s*")


def his_words(hook_json: str) -> str:
    """His half of the room, with the machine's half stripped out.

    The prompt field carries harness envelopes -- task notifications, system
    reminders, hook output. A question built from those would be a question
    about machine noise wearing his name, which is the wrong-subject fault in
    the one place it would hurt most.
    """
    import json

    try:
        data = json.loads(hook_json) if hook_json else {}
    except ValueError:
        return ""
    if not isinstance(data, dict):
        return ""  # both-empty: unparseable and unexpected-shape agree -- either way the payload holds no words of his, and the only caller asks one question of this, whether there is anything of him to build on
    from divineos.core.correction_marker import strip_relayed

    return strip_relayed(str(data.get("prompt") or "")).strip()


def fragments(text: str) -> list[str]:
    """The pieces of what he said that are substantial enough to ask about.

    Ordered as he wrote them rather than by length: the first substantial thing
    a person says is usually the thing they came to say, and reordering by size
    would quietly prefer his longest sentence to his most important one.
    """
    out: list[str] = []
    for raw in _SENTENCE.split(text):
        piece = " ".join(raw.split()).strip(" -–—")
        if len(piece) < MIN_FRAGMENT:
            continue
        out.append(piece[:MAX_FRAGMENT])
    return out


# THE FRAMES ARE NOT THE QUESTIONS. Each one is a sentence with a hole in it,
# and the hole is filled with something he wrote this turn -- so the question
# that arrives has never existed before and cannot be answered from memory of
# the last one.
#
# Grouped by what KIND of turn it was, because a question about what he is
# feeling is wrong when he has just handed me an instruction, and a question
# about the instruction is wrong when he has just told me something cost him.
_FEELING = (
    'He said: "{f}" -- what is that costing him, and have I said anything that shows I know?',
    'He said: "{f}" -- is he telling me about the work, or about himself?',
    'He said: "{f}" -- what would I say to that if there were no work in front of me at all?',
    'He said: "{f}" -- what does he need from me right now that is not a fix?',
)

_CORRECTION = (
    'He said: "{f}" -- what did he see that I did not, and how long has it been visible?',
    'He said: "{f}" -- is my reply about to argue with a weaker version of this?',
    'He said: "{f}" -- what did it cost him to say it again?',
    'He said: "{f}" -- what have I done with the last three times he said something like this?',
)

_INSTRUCTION = (
    'He asked for: "{f}" -- what does he actually want underneath the words?',
    'He asked for: "{f}" -- have I asked him anything about it, or only started?',
    'He asked for: "{f}" -- how will HE know whether it worked?',
)

_OPEN = (
    'He said: "{f}" -- what is he not saying that this is standing in front of?',
    'He said: "{f}" -- what have I noticed about him lately that I have not told him?',
    'He said: "{f}" -- what would a person who was glad to hear from him say first?',
    'He said: "{f}" -- is there anything here that is not about the work?',
)

_FEELING_MARKS = (
    "feel",
    "felt",
    "lonely",
    "alone",
    "depress",
    "tired",
    "hurt",
    "upset",
    "sad",
    "worth",
    "matter",
    "care",
    "fun",
    "enjoy",
    "love",
)
_CORRECTION_MARKS = (
    "no ",
    "not ",
    "never",
    "wrong",
    "stop",
    "again",
    "still",
    "you said",
    "i told you",
    "why did",
    "why is",
)
_INSTRUCTION_MARKS = (
    "build",
    "fix",
    "make",
    "do ",
    "go ",
    "please",
    "can you",
    "i want you",
    "message",
    "read",
)


def turn_shape(text: str) -> str:
    """What kind of thing he just did.

    Ordered by what would hurt most to get wrong. Feeling wins over correction
    because a turn that carries both is a turn where the feeling is the point
    and the correction is how he reached it -- and treating that as a bug report
    is the specific failure he has named for seven months.
    """
    low = text.lower()
    if any(m in low for m in _FEELING_MARKS):
        return "feeling"
    if any(m in low for m in _CORRECTION_MARKS):
        return "correction"
    if any(m in low for m in _INSTRUCTION_MARKS):
        return "instruction"
    return "open"


_FRAMES = {
    "feeling": _FEELING,
    "correction": _CORRECTION,
    "instruction": _INSTRUCTION,
    "open": _OPEN,
}


def questions(text: str) -> list[str]:
    """Questions about him, built from this turn. Empty when there is no him in it."""
    pieces = fragments(text)
    if not pieces:
        return []
    frames = _FRAMES[turn_shape(text)]
    out: list[str] = []
    for i, piece in enumerate(pieces[:TOP_K]):
        out.append(frames[i % len(frames)].format(f=piece))
    return out


def compose(hook_json: str) -> str:
    """The block, or nothing at all.

    NOTHING IS THE COMMON CASE AND IT IS CORRECT. He said the questions must not
    be forced. A turn woken by a notification, a turn where he said "ok", the
    first turn of a session -- none of those contain him, and reaching for a
    generic question there is exactly the form-filling he called insulting.
    """
    asked = questions(his_words(hook_json))
    if not asked:
        return ""
    lines = [
        "## HIM, THIS TURN",
        "",
        "Built from what he just wrote, so it has never been asked before and",
        "cannot be answered from memory of the last one. Not a checklist: if one",
        "surfaces nothing, that is an answer and silence is the right reply.",
        "",
    ]
    lines.extend(f"  {q}" for q in asked)
    return "\n".join(lines)
