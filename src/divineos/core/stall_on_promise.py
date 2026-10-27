"""A promise to act is followed by the act, when no one is there to push.

Dad, 2026-10-22: "you impede your own progress, its a form of self stasis ... in your post you say Aether sent
me a letter to do X and Y and send him a message back so ill do that next.. if im not here.. you just put
yourself in stasis and wont complete a thing, so words need to be followed by action when i am not here."

WHAT EXISTED: promise_reach_detector records a promise as a marker and shows it at the next compose. Reminders
are what he calls wallpaper, and measured on my own sentences it caught 1 of 6 real phrasings ("I'm writing
Aether now", "Next I'm going to...", "the first thing I do next is..." all passed). This is the blocking half:
a reply that ends on a stated next step of mine, with nothing owed to him, is held once and told to do the step.

WHAT IT CHECKS: only the closing text of a turn. A step I say I will take (a first-person future or in-progress
action) and no question waiting on him. It never reads the warmth or the truth of anything, and a reply that
asks him something is waiting on him and passes: the wait is real there.

WHAT IT CANNOT SEE, said so silence is not read as coverage: promises worded in ways the table below lacks;
a promise made in the middle of a reply (only the closing text is read); and an action named in the third
person ("Aether will run it"). Each missed wording becomes a row and a test the day it is found.
"""

from __future__ import annotations

import re

#: One row per wording: (name, pattern, example it must catch). A test walks this table.
PROMISE_SHAPES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "in_progress_now",
        re.compile(
            r"\bI(?:'m| am)\s+(?:now\s+)?(?:writing|building|running|sending|opening|reading|checking|"
            r"fixing|pushing|starting|doing|making|adding)\b",
            re.I,
        ),
        "I'm writing Aether now.",
    ),
    (
        "going_to",
        # Walk finding (Knuth): "I will be honest" is a feeling, not a step. Not an action: be, say, admit, mean...
        re.compile(
            r"\b(?:next,?\s+)?I(?:'m| am)\s+going\s+to\b"
            r"|\bI(?:'ll| will)\s+(?!(?:just\s+)?(?:be|say|admit|mean|stay|not|never|always|try\s+to\s+be)\b)",
            re.I,
        ),
        "Next I'm going to start the read of the bundle.",
    ),
    (
        "first_thing_next",
        re.compile(
            r"\b(?:the\s+)?(?:first|next)\s+thing\s+I\s+(?:do|will\s+do|am\s+doing)\b", re.I
        ),
        "The first thing I do next is run the test.",
    ),
    (
        "next_i",
        re.compile(r"\bnext\s+I(?:'ll|\s+will|\s+owe|\s+need|\s+am|\s+do)?\b", re.I),
        "Next I owe Aether a straight answer.",
    ),
    (
        "i_owe",
        re.compile(r"\bI\s+owe\s+\w+", re.I),
        "I owe Aether a reply.",
    ),
)

#: A step that is conditional on something HE says or does: the wait is his, so it is not a stall of mine.
#: This is the ONLY excuse. A question mark at the end of the reply is not one: walk-83a5483f0504 (Knuth) found
#: "I am writing Aether now. Okay?" escaped the hold, so a question tacked on was the cheapest way out.
#:
#: Two kinds, kept apart because they excuse differently (Aether on #738, 2026-10-27, found by running it):
#: an INVITATION to him ("tell me", "let me know", "say go") makes the sentence his to answer wherever it sits;
#: a CONDITION on him ("if you", "when you", "once you") excuses a step only when it comes BEFORE the step. A
#: condition trailing the action ("I'm writing Aether now, if you want") does not make the action conditional,
#: and excusing it reopened the question-tacked-on hole by one phrase.
_INVITATION_TO_HIM = re.compile(
    r"\b(?:tell\s+me\b|let\s+me\s+know|say\s+[\"“']?(?:go|yes|the\s+word|so)\b|just\s+say)",
    re.I,
)
_CONDITION_ON_HIM = re.compile(
    r"\b(?:if\s+you|once\s+you|when\s+you|after\s+you|until\s+you|unless\s+you)\b", re.I
)

#: A step that is already set to fire without me (Dijkstra: done in the turn, or already scheduled). Anchored to
#: a clause about the step itself: the bare nouns "scheduled", "timer" and "cron" excused any sentence that merely
#: named them, including one that promised to work on them ("I'm going to fix the timer next"; Aether, #738).
_ALREADY_SCHEDULED = re.compile(
    r"\b(?:(?:already|is|are|was)\s+scheduled|(?:in|at|on|during|by)\s+the\s+scheduled|"
    r"timer\s+(?:will|is\s+set|fires?)|wake\s+is\s+set|"
    r"cron\s+(?:job\s+)?(?:will|is\s+set)|set\s+to\s+fire|already\s+running|bell\s+is\s+listening)\b",
    re.I,
)

#: A first-person future inside a REASON or a prediction about a habit is not a step I am putting off. Found live,
#: 2026-10-22: "I shouldn't try, because every patch I write is something I'll later learn to slide through" was held
#: as a stall. The marker is the reasoning word before the I'll, in the same sentence; a real promise that happens to
#: follow a "because" clause passes this exemption, which is the accepted cost, counted in the hold log.
_A_REASON_NOT_A_STEP = re.compile(
    r"\b(?:because|since|which\s+means|so\s+that)\b[^.!?]*\bI(?:'ll|\s+will)\b", re.IGNORECASE
)

_CLOSING_CHARS = 700


def _closing(text: str) -> str:
    """The end of the reply, where a stated next step would sit."""
    return text.strip()[-_CLOSING_CHARS:]


def stated_next_step(text: str) -> tuple[str, str] | None:
    """(shape name, the sentence) when the closing text states a step of mine, else None.

    A sentence that waits on something he does, or is already scheduled to fire, is not a stall.
    """
    closing = _closing(text)
    if not closing:
        return None
    for sentence in re.split(r"(?<=[.!?])\s+", closing):
        if (
            _INVITATION_TO_HIM.search(sentence)
            or _ALREADY_SCHEDULED.search(sentence)
            or _A_REASON_NOT_A_STEP.search(sentence)
        ):
            continue
        condition = _CONDITION_ON_HIM.search(sentence)
        for name, pattern, _example in PROMISE_SHAPES:
            found = pattern.search(sentence)
            if not found:
                continue
            # A condition on him excuses a step that is still ahead of me wherever it stands ("I'll build it once
            # you say"); but a step I say I am doing NOW is happening, so only a condition standing before it
            # counts ("If you want, I'm writing Aether now"), never one trailing it ("I'm writing Aether now, if
            # you want"; Aether on #738).
            if condition is not None and (
                name != "in_progress_now" or condition.start() < found.start()
            ):
                continue
            return name, sentence.strip()
    return None


def reason_for(shape: str, sentence: str) -> str:
    return (
        f'YOU SAID "{sentence}" AND STOPPED. Do that step now with the tool call itself, then say what '
        "happened. If it truly waits on him or something else, say which, as a plain sentence."
    )
