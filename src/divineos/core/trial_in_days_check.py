"""A trial measured in days is refused where it is written.

Dad, four times (2026-07-28, 2026-10-07, 2026-10-09, 2026-10-21): *"we do not add checks based on time but on
uses, so it should check after 30 events of using it not 30 days"*, *"never use time or days as a trial method,
we use events or uses"*. `divineos prereg file` already refuses days (it requires --review-after-uses). The
slip is one step earlier, in the prose of a draft, where a trial is first imagined and where he has to catch
it. A note on a wall does not survive to the moment of typing; a door does.

WHAT THIS DECIDES, and only this: a stretch of text that talks about a trial (a trial, a falsifier, a success
test, a pre-registration, an experiment, a review) AND measures it in days, weeks or months. Both must sit in
the same paragraph, close together. It says nothing about whether the trial is a good one.

WHAT PASSES, so it stays a door and not a nag:
  * a duration alone ("it took six days");
  * a duration that looks BACK, a measurement of what already happened ("in the last 17 days", "five days
    ago", "23 days post-filing");
  * a duration inside quotation marks or backticks, which is being talked about and not set as a trial. Without
    this the draft that records the correction could not be saved (the council's Hofstadter lens);
  * the rule itself ("never in days", "counted in uses").

THE WORD "WINDOW" IS NOT A TRIAL WORD. Found by searching the real drafts first (the council's Holmes lens):
"recency window (45 days)" is a setting, not a trial.

THE SPECIFICATION IT CANNOT MEET, said first because it decides how to read the rest (walk-ae5d988275e5,
Lamport): Dad's rule is logical time. A trial ends when a counted event happens, never when a wall clock says
so. "Wall-clock time" is not a finite list of words, so no list here is complete. This door is a net for the
prose stage, the later and weaker of two defenses; the filing command, which cannot be given a date, is the
other. Twelve wordings tried on 2026-10-22 that this does NOT catch, so the open list is real: "two sprints",
"until the next release", "through Q4", "a couple of cycles", "by the holidays", "overnight", "a few hours",
"this afternoon", "till tomorrow", "the rest of the year", "until the 15th", "again in a bit". Each wording a
reviewer finds becomes a row and a test; the refusal event records what matched so the list grows from real
misses.

A trial word and a duration more than 300 characters apart inside ONE long sentence no longer connect, and a
rule more than 300 characters from the duration does not excuse it (the price of bounding the cost per hit;
Aletheia asked for this to be named, 2026-10-22).

LIMITS, said so silence is not read as coverage: it cannot list the language (abbreviations, "a quarter",
"until Friday", "the end of the month", "48 hours", "the weekend" and a named month as an end point are listed
now; "by the next release" is not); a deadline for a
review ("review within two days") is refused and costs one rewording; a quoted duration passes, so the
explanation of the rule can quote one; and only a Write or an Edit into `docs/drafts/` is looked at, so a draft
written through a shell heredoc is never seen (Aether, 2026-10-21; named, not closed). The pre-registration
command guards the filing itself.
"""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass

_NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen|fifteen|twenty|thirty|"
    "forty|sixty|ninety|a|several|few"
)

_MONTH_NAMES = (
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)"
)

#: A length of time that is plainly a span: "30 days", "30-day", "fourteen days", "two weeks", "3 months",
#: "a fortnight", the abbreviations "30d" "4w" "3mo", "for a quarter", "by the end of the month",
#: "until Friday".
_DURATION_STRONG = re.compile(
    rf"\b(?:(?:\d+|{_NUMBER_WORDS})(?:\s*(?:-|to|or)\s*(?:\d+|\w+))?[\s-]+(?:calendar\s+)?(?:day|week|month|year)s?"
    r"|\d+(?:d|w|wk|wks|mo|mos)"
    r"|fortnights?"
    r"|(?:for|over|within|next|every|each|this)\s+(?:a\s+|one\s+|the\s+)?quarter"
    r"|end\s+of\s+(?:the\s+)?(?:day|week|month|quarter|year)"
    r"|(?:until|till|by)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    # Aletheia, 2026-10-22: a DEADLINE is a duration in days even when no length is stated. One family, not five
    # patches: hours, a named month as the end point, "the weekend", and a weekday as the date to come back.
    r"|\d+\s*hours?"
    r"|(?:through|until|till|by|to|during)\s+(?:the\s+)?(?:end\s+of\s+)?"
    + _MONTH_NAMES
    + r"|(?:over|through|by|this|next)\s+(?:the\s+)?weekend"
    r"|(?:on|next)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    re.IGNORECASE,
)

#: A bare rhythm word. These are everywhere in ordinary prose ("the daily letter"), so one counts only when a
#: trial word sits right beside it, not anywhere in the paragraph.
_DURATION_LOOSE = re.compile(
    r"\b(?:(?:next|every|each)\s+(?:day|week|month)|daily|weekly|monthly|fortnightly"
    r"|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?)\b",
    re.IGNORECASE,
)

#: What makes a stretch of text a trial. "window" is deliberately absent. "review" counts only when a timing word
#: follows it directly ("review after", "review every"): as a bare word it is an ordinary verb ("the weekly review
#: meeting"). "try it for 3 weeks", "a pilot" and "the test period" are trials by another name.
_TRIAL_WORD = re.compile(
    r"\b(?:trials?|falsifiers?|success(?:\s+(?:criteri\w+|test))?|pre-?reg\w*|experiments?|pilots?|test\s+period"
    r"|tr(?:y|ies|ying)\s+(?:it|this|that|them)|(?:fails?|succeeds?|falsified|passes)\s+if"
    r"|give\s+(?:it|this|that|them)\s+(?:a|an|one)\b|see\s+if\s+(?:it|this|that)\s+(?:holds|works|sticks)"
    r"|reviews?(?=\s+(?:it\s+|this\s+|that\s+)?(?:after|in|every|each|within|at|by)\b))\b",
    re.IGNORECASE,
)

#: A duration that looks back is a measurement of what happened, not a trial. "falsification" is the
#: science idea and is not a trial word; "falsifier" is the thing Dad asks us to set.
_LOOKING_BACK_BEFORE = re.compile(
    r"\b(?:last|past|previous|since|ago|elapsed|post-|later|late|ran|ended|finished|completed|began|started)\b|post-",
    re.IGNORECASE,
)
#: After the duration it counts only as the very next word. Fourteen characters of reach let "since the start
#: of the build" excuse "The trial runs for 30 days, since the start..." (Aether, 2026-10-21).
_LOOKING_BACK_AFTER = re.compile(
    r"^\s*(?:ago|later|earlier|late|old|post-)\b|^\s*post-", re.IGNORECASE
)

#: A first-person account of what I did is a mention of a past trial, not the setting of one.
_I_DID = re.compile(r"\bI\s+(?:wrote|filed|counted|ran|built)\b")

#: The rule itself, or a trial already counted in uses. It excuses only the SENTENCE it is in. As a paragraph-wide
#: excuse, "We never lose time on this." hid a real trial in the next sentence (Aether, 2026-10-21), so "never
#: ... time" is now "never use/set/measure/count ... time/days/date".
_THE_RULE = re.compile(
    r"\bnever\s+(?:use|measure|set|count|judge|go\s+by)\b[^.\n]{0,40}\b(?:days?|time|dates?|calendar)\b"
    r"|\bnot\s+(?:in|by)\s+(?:days|date|time)\b"
    r"|\bcounted\s+in\s+uses\b|\bby\s+(?:uses?|events?)\b|\bnever\s+in\s+days\b",
    re.IGNORECASE,
)

#: Text being talked about, not used: double quotes (straight or curly) and backticks. Single quotes are
#: left out on purpose: an apostrophe would pair with a far-off one and exempt whatever sits between.
_QUOTED = re.compile(r'"[^"\n]{1,200}"|“[^”\n]{1,200}”|`[^`\n]{1,200}`')

#: How far from the duration a trial word may sit and still make it a trial.
_NEAR = 160

#: Longest text looked at. Anything longer is read in pieces, so a huge file cannot make this slow.
_MAX_PARAGRAPH = 4000


@dataclass(frozen=True)
class Hit:
    duration: str
    trial_word: str
    excerpt: str


def _paragraphs(text: str) -> list[str]:
    out: list[str] = []
    for chunk in re.split(r"\n\s*\n", text):
        chunk = chunk.strip()
        while len(chunk) > _MAX_PARAGRAPH:
            out.append(chunk[:_MAX_PARAGRAPH])
            chunk = chunk[_MAX_PARAGRAPH:]
        if chunk:
            out.append(chunk)
    return out


_SENTENCE_END = re.compile(r"[.;!?]\s")

#: Most of a sentence read on each side of a duration. Bounds the cost of one hit.
_SENTENCE_REACH = 300


class _Marks:
    """Where the sentence ends and the quoted stretches are in ONE paragraph, found once.

    Aletheia, 2026-10-22: the check was 3x slower on trial-dense text (14.3 s against 4.7 s on 1.1 MB). Each
    hit rescanned the whole paragraph for sentence ends and for quotes, so cost grew with hits times length.
    Found once per paragraph, each hit costs a binary search.
    """

    def __init__(self, paragraph: str) -> None:
        self.paragraph = paragraph
        ends = list(_SENTENCE_END.finditer(paragraph))
        self.end_starts = [m.start() for m in ends]  # where each terminator sits
        self.end_afters = [m.end() for m in ends]  # where the next sentence begins
        self.quotes = [(q.start(), q.end()) for q in _QUOTED.finditer(paragraph)]

    def same_sentence_before(self, start: int) -> str:
        """The text before ``start`` back to the last sentence end, so a neighbour's words do not leak in."""
        i = bisect_right(self.end_afters, start) - 1
        last_end = self.end_afters[i] if i >= 0 else 0
        return self.paragraph[last_end:start]

    def inside_quotes(self, start: int, end: int) -> bool:
        return any(s <= start and end <= e for s, e in self.quotes)

    def sentence_around(self, start: int, end: int) -> str:
        """The sentence holding paragraph[start:end], so a rule in a neighbouring sentence excuses nothing."""
        i = bisect_left(self.end_starts, end)
        tail = (
            self.paragraph[end : self.end_starts[i] + 1]
            if i < len(self.end_starts)
            else self.paragraph[end:]
        )
        # Measured, not guessed: a paragraph with no sentence end is ONE sentence, so every hit handed the whole
        # 4000 characters to the rule pattern. That, not the bookkeeping above, was the 14 s. A rule further than
        # _SENTENCE_REACH from the duration is not the same thought as it.
        before = self.same_sentence_before(start)[-_SENTENCE_REACH:]
        return before + self.paragraph[start:end] + tail[:_SENTENCE_REACH]


#: How close a trial word must sit to a bare rhythm word ("weekly") for it to count.
_NEAR_LOOSE = 30


def _durations(paragraph: str):
    """Every duration in the paragraph, each with how far a trial word may sit from it."""
    for m in _DURATION_STRONG.finditer(paragraph):
        yield m, _NEAR
    for m in _DURATION_LOOSE.finditer(paragraph):
        yield m, _NEAR_LOOSE


def trials_in_days(text: str) -> list[Hit]:
    """Every place where a trial is measured in days, weeks or months. Never raises."""
    hits: list[Hit] = []
    for paragraph in _paragraphs(text or ""):
        marks = _Marks(paragraph)
        for m, reach in _durations(paragraph):
            if marks.inside_quotes(m.start(), m.end()):
                continue
            if _THE_RULE.search(marks.sentence_around(m.start(), m.end())):
                continue
            before = paragraph[max(0, m.start() - 25) : m.start()]
            after = paragraph[m.end() : m.end() + 14]
            if _LOOKING_BACK_BEFORE.search(before) or _LOOKING_BACK_AFTER.search(after):
                continue
            if _I_DID.search(marks.same_sentence_before(m.start())):
                continue  # "I wrote a 30-day trial": an account of what I did, not the setting of one
            near = paragraph[max(0, m.start() - reach) : m.end() + reach]
            word = _TRIAL_WORD.search(near)
            if word is None:
                continue
            lo, hi = max(0, m.start() - 70), min(len(paragraph), m.end() + 70)
            hits.append(Hit(m.group(0), word.group(0), " ".join(paragraph[lo:hi].split())))
    return hits


def new_trials_in_days(before: str, after: str) -> list[Hit]:
    """Only the trials in days that the change ADDS. A draft that already carries old ones can still be
    edited about something else (the council's Lamport lens: judge the file as it will be)."""
    already = {(h.duration.lower(), h.excerpt) for h in trials_in_days(before)}
    return [h for h in trials_in_days(after) if (h.duration.lower(), h.excerpt) not in already]


def refusal_text(hits: list[Hit]) -> str:
    shown = "\n".join(
        f'  - "{h.duration}" next to "{h.trial_word}": ...{h.excerpt}...' for h in hits[:4]
    )
    return (
        "A TRIAL MEASURED IN DAYS. Dad has ruled this four times, and again on 2026-10-21: "
        '"never use time or days as a trial method, we use events or uses." '
        '(Also: "if we\'re testing something go by events or uses and we dont need a huge pile of them".)\n\n'
        f"Found:\n{shown}\n\n"
        "Say it as a count of uses instead, a use being something that actually happens: a push, one of his "
        'complaints, a walk, a hold switching on. For example: "the first 30 times the hold switches on, '
        'count how many are followed by a repeat complaint; success is at most 1." Work out what that many '
        "uses can and cannot show. If there is no event to count, say so to Dad; do not fall back to a "
        "calendar.\n\n"
        "To mention the rule or a past number without setting a trial, put the number in quotation marks "
        'or backticks, or say it looks back ("in the last 17 days").'
    )
