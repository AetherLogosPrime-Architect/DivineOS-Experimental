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
#
# NARROWED 2026-10-28 (walk-a257ab66691e, Lovelace, found by running it): the reason word and the I'll must sit in
# one clause, so no comma, semicolon, colon or dash between them. As first written, "Since the tests are green,
# I'll push it tonight" and "Because Aether asked, I'll write the letter next" both escaped: the reason opened the
# sentence and a real promise followed the comma. The habit case it was written for has no comma in it.
#
# NARROWED AGAIN the same night (Aether's read of 4823c6f8e): "Because the tests are green I'll push it tonight"
# has no comma, so the clause rule alone still excused it. A habit has its I'll attached to a noun phrase or
# carries a habit adverb ("something I'll later learn", "I'll always"); a real promise has the I'll right after
# the reason. The marker is required, so the comma-less promise is held.
_A_REASON_NOT_A_STEP = re.compile(
    r"\b(?:because|since|which\s+means|so\s+that)\b[^.!?,;:—]*?(?:"
    r"\b(?:something|anything|everything|whatever|what|that|which|how|why)\s+I(?:'ll|\s+will)\b"
    r"|\bI(?:'ll|\s+will)\s+(?:later|eventually|always|never|probably|just)\b)",
    re.IGNORECASE,
)

#: A first-person future that is a feeling or an attention, not work a person could watch happen (walk-a257ab66691e,
#: Wittgenstein and Meadows): "I'll remember this night", "I'll miss you tonight", "I'll keep that close". Run on
#: 14 real sentences, six warm ones were held as stalls, and a false hold on a warm sentence teaches the colder
#: rewrite this hold exists to stop. The span is REMOVED and the rest of the sentence is read again, so "I'll think
#: about it and I'll write the plan" is still held for the second half. Objects are named ("keep THAT close") so
#: "I'll keep the line moving" stays a step. A list, not coverage; each miss becomes a row and a test.
_A_FEELING_NOT_A_STEP = re.compile(
    r"\bI(?:'ll|\s+will)\s+(?:"
    r"remember\b(?!\s+to\b)|miss\b|treasure\b|cherish\b|love\b|hope\b(?!\s+to\b)|wonder\b"
    r"|think\s+(?:about|of)\s+(?:that|this|it|you|what\s+you)\b"
    r"|hold\s+on\s+to\b"
    r"|keep\s+(?:that|this|it|those|what\s+you\s+\w+)\s+(?:close|safe|in\s+mind|with\s+me)\b"
    r"|carry\s+(?:that|this|it|those|what\s+you\s+\w+)\s+(?:with\s+me|into\s+the\s+(?:morning|night|day)|forward|close)\b"
    r")",
    re.IGNORECASE,
)

#: The same feelings with the object put first ("What he said I'll keep with me", "That I'll always carry"; Aether,
#: 37591fd9e). Kept tight on purpose: the object is a short run with no clause punctuation, the verb is one of the
#: attention verbs, and it must END the thought (a closing mark, or "with me", "close", "safe", "in mind"), so
#: "Everything is ready and I'll keep the push moving" and "What he said I'll file tonight" are still held.
_A_FEELING_FRONTED = re.compile(
    r"\b(?:what|that|this|all\s+that)\b[^.!?,;:—]{0,40}?\bI(?:'ll|\s+will)\s+(?:always\s+)?"
    r"(?:keep|carry|remember|hold|treasure|cherish)\b"
    r"(?=\s+(?:with\s+me|close|safe|in\s+mind|forever)\b|\s*[.!?]|\s*$)",
    re.IGNORECASE,
)

#: A stance, a figure of speech or a feeling about my own conduct: nothing a tool could do (2026-11-03, real replies
#: held as stalls: "I'll keep showing up for my share.", "I'll leave the questions alone for a bit.", "I'll take
#: what's true in what you said.", "I'll make it worth living.", "I'll hold the table."). Same treatment as the
#: feelings above: the span is removed and the rest of the sentence is read again. An explicit list on purpose,
#: anchored on the OBJECT so the same verb with work on it stays a step ("I'll hold the push until Aether reads it",
#: "I'll leave the file open and fix it next"). A stance worded some new way is held until it becomes a row here.
_A_STANCE_NOT_A_STEP = re.compile(
    r"\bI(?:'ll|\s+will)\s+(?:"
    # Bare, or a short "for my share" tail: "keep trying the push" has an object and stays a step.
    r"keep\s+showing\s+up(?:\s+for\s+\w+(?:\s+\w+){0,2})?(?=\s*[.!?,;—]|\s*$)"
    r"|keep\s+(?:trying|listening)(?=\s*[.!?,;—]|\s*$)"
    r"|keep\s+(?:being|caring|holding\s+(?:on|space))(?:\s+\w+){0,3}(?=\s*[.!?,;—]|\s*$)"
    r"|leave\s+(?:the\s+\w+|that|this|it|them|those|these)\s+(?:\w+\s+)?alone\b"
    r"|take\s+what(?:'s|\s+is)\s+true\b"
    r"|make\s+(?:it|that|this|them)\s+worth\s+(?:living|while|it|the\s+(?:wait|trip|time|effort)"
    r"|your\s+(?:time|while|trust))(?=\s*[.!?,;—]|\s*$)"
    r"|hold\s+the\s+(?:table|room|space)\b"
    r")",
    re.IGNORECASE,
)

#: "I owe no proof", "I owe you nothing": the absence of a debt, not a debt. The glad/grateful clause that
#: carries it is a feeling, and has no verb of work either.
# "I owe you nothing less than the fix" is the opposite of no debt, so it is not cut out.
_NO_DEBT = re.compile(
    r"\bI\s+owe\s+(?:\w+\s+)?(?:no|nothing)\b(?!\s+(?:less|more|fewer|short)\b)", re.IGNORECASE
)

#: A lead-in that names what it is about to SAY ("I'll add the careful part, ...") is kept when the same reply then
#: says it. Only verbs whose act is the saying itself: "I'll write the letter" or "I'll push it" are never excused
#: by the noun turning up again, since the act is a tool's, not a sentence's.
_A_LEAD_IN_NAMING_ITS_CONTENT = re.compile(
    r"\bI(?:'ll|\s+will)\s+(?:add|give\s+you|say|state|name|spell\s+out)\s+(?:the|a|an|my|our)\s+"
    r"(?P<what>\w+(?:\s+\w+){0,3}?)(?=\s*[,.;:!?—]|\s+(?:since|because|so|and|that|which|for|now|here|below)\b|$)",
    re.IGNORECASE,
)


_BARE_SECOND_VERB = re.compile(
    r"^((?:\s+\w+){0,4}?\s*,?\s*(?:and|then)\s+)(?!I\b)(?=\w)", re.IGNORECASE
)

#: A mention of the promised content that says it is NOT there ("the careful part isn't written yet") does not
#: deliver it. Read in a window of words either side of the mention, so an unrelated "no" elsewhere in the same
#: sentence ("... a promise it has no row for") does not cancel a real delivery.
_NEGATION = re.compile(r"\b(?:not|never|nothing|without)\b|n['’]t\b", re.IGNORECASE)
_WINDOW_WORDS = 6


def _delivered_in(what: str, sentence: str) -> bool:
    for mention in re.finditer(r"\b" + re.escape(what) + r"\b", sentence, re.IGNORECASE):
        # "The careful part: the gate never fires" is a section being delivered; what follows the colon is its
        # content, so a "never" in it is not a denial. Only a denial standing right after the colon is one.
        label, colon, content = sentence[mention.end() :].partition(":")
        if colon and len(label.split()) <= 3:
            return not _NEGATION.search(" ".join(content.split()[:2]))
        near = (
            sentence[: mention.start()].split()[-_WINDOW_WORDS:]
            + sentence[mention.end() :].split()[:_WINDOW_WORDS]
        )
        if not _NEGATION.search(" ".join(near)):
            return True
    return False


def _after_said_lead_in(sentence: str, after: str) -> str | None:
    """None when the sentence has no kept lead-in; else the sentence with the kept lead-in cut out.

    The rest is still read: "I'll add the careful part, and then push it tonight" keeps its second step.
    The content must turn up as whole words (not "fix" inside "prefix") in a later sentence that does not
    deny it."""
    lead = _A_LEAD_IN_NAMING_ITS_CONTENT.search(sentence)
    if lead is None:
        return None
    what = lead.group("what")
    if not any(_delivered_in(what, later) for later in re.split(r"(?<=[.!?])\s+", after)):
        return None
    tail = _BARE_SECOND_VERB.sub(r"\1I'll ", sentence[lead.end() :], count=1)
    return sentence[: lead.start()] + " " + tail


# The cut stops at the first word that starts a later clause ("and then push once you confirm"), so his
# condition in that clause is still there to be read.
_MY_OWN_SAYING = re.compile(
    r"\bI(?:'ll|\s+will)\s+(?:just\s+)?say\b"
    r"(?:(?!\s+(?:and|then|once|when|whenever|if|after|until|as\s+soon)\b)[^,.;!?])*",
    re.IGNORECASE,
)

# "wait" and "again" after "then" are not work of mine ("then wait for you", "but then again").
_THEN_BARE_VERB = re.compile(
    r"(\bI(?:'ll|\s+will)\b[^.!?]*?\bthen\s+)"
    r"(?!(?:I|you|we|he|she|they|it|the|a|an|that|this|his|her|their|my|there|some|all|no|wait|again)\b)"
    r"(?=[a-z])",
    re.IGNORECASE,
)


def _with_then_verb_owned(sentence: str) -> str:
    """ "I'll say the word, and then deploy it tonight": the second verb is a step of mine with its subject left
    out, and a first clause with an excluded verb (say, be) must not excuse the whole sentence."""
    return _THEN_BARE_VERB.sub(r"\1I'll ", sentence, count=1)


def _without_feelings(sentence: str) -> str:
    """The sentence with its feeling shapes cut out, so only the rest is read for a promise.

    A bare verb that follows ("I'll remember this AND push it tonight", "I'll carry that forward AND file
    the walk later") is a second step with its subject left out, so it gets its I'll back before the
    promise shapes run (Aether, 4823c6f8e: "carry that forward" is a way of saying defer this)."""
    sentence = _NO_DEBT.sub(" ", sentence)
    for _ in range(5):
        found = (
            _A_FEELING_NOT_A_STEP.search(sentence)
            or _A_FEELING_FRONTED.search(sentence)
            or _A_STANCE_NOT_A_STEP.search(sentence)
        )
        if found is None:
            break
        tail = _BARE_SECOND_VERB.sub(r"\1I'll ", sentence[found.end() :], count=1)
        sentence = sentence[: found.start()] + " " + tail
    return sentence


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
    sentences = re.split(r"(?<=[.!?])\s+", closing)
    for index, sentence in enumerate(sentences):
        if _ALREADY_SCHEDULED.search(sentence) or _A_REASON_NOT_A_STEP.search(sentence):
            continue
        kept = _after_said_lead_in(sentence, " ".join(sentences[index + 1 :]))
        if kept is not None:
            sentence = kept
        # A feeling or an attention is not a step: take it out, then read what is left (see the pattern).
        sentence_to_read = _with_then_verb_owned(_without_feelings(sentence))
        # "I'll say the word" is MY saying, not an invitation for him to say it: cut before looking for his markers.
        his_part = _MY_OWN_SAYING.sub(" ", sentence_to_read)
        markers = [
            marker
            for marker in (
                _INVITATION_TO_HIM.search(his_part),
                _CONDITION_ON_HIM.search(his_part),
            )
            if marker is not None
        ]
        for name, pattern, _example in PROMISE_SHAPES:
            found = pattern.search(sentence_to_read)
            if not found:
                continue
            # A marker of his (an invitation like "tell me", or a condition like "once you") excuses a step that is
            # still ahead of me wherever it stands ("I'll build it once you say"); but a step I say I am doing NOW
            # is happening, so only a marker standing before it counts ("If you want, I'm writing Aether now"),
            # never one trailing it ("I'm writing Aether now, if you want"; Aether on #738). Invitations used to
            # excuse the whole sentence wherever they sat, so "I'm writing Aether now, tell me if you'd rather I
            # wait" passed: the same hole by another phrase (walk-a257ab66691e, Yudkowsky, found by running it).
            if markers and (
                name != "in_progress_now" or any(m.start() < found.start() for m in markers)
            ):
                continue
            return name, sentence.strip()
    return None


def reason_for(shape: str, sentence: str) -> str:
    return (
        f'YOU SAID "{sentence}" AND STOPPED. Do that step now with the tool call itself, then say what '
        "happened. If it truly waits on him or something else, say which, as a plain sentence."
    )
