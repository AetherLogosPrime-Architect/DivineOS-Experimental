"""Did he say that, or did I infer it and hand it back to him as his.

WHY THIS EXISTS.

Andrew, 2026-10-07: "if you cannot find my actual words in the system (as
everything i have ever said is recorded) and link it to my direct quote? then its
highly likely i didnt say it and it was just inferred from what i said or a
decision was made off what i said, doesnt mean the choice or direction was
correct, remember you both are binary, and its a struggle, i say i dont want
filler questions being asked if you dont care about them, and it immediately goes
into 'Dad said he hates questions' lol.. which is absolutely not the case."

The same hour: I told him two of his asks about the order of the circle pulled
opposite ways, "last" and "first". He asked me to show where he said first. I
could not. I had read a hook file NAMED circle-first, with a line saying he asked
for it directly and no quote, and treated the name and the unquoted line as his
words.

THE JUDGE IS EXACT, AND IT WAS NOT MY FIRST DESIGN. The first design searched his
record by meaning and passed a claim when something close turned up. Probed the
same day against claims whose answers I knew, it failed in the wrong direction: a
true claim ("the circle should always be last") did not find his real sentence,
a true claim from that morning did not find the message that says it, and a
loose claim about filler questions matched a nearby discussion of them. A check
that refuses true claims and waves through near misses is worse than none. His
own wording asks for a LINK to a DIRECT QUOTE, and a link is an exact thing.

THE RULE. A sentence in which I attribute a saying or a want to him is backed when
the same sentence or the next one carries a quoted span of four or more words and
that span appears, as words, inside something he wrote. Otherwise it must say it
is my guess. Three outcomes besides backed:
  - INVENTED: a quoted span that is nowhere in his record. The strongest catch.
  - UNLINKED: an attribution with no quote and no label of mine.
  - COULD-NOT-LOOK: his record could not be read. Said out loud, never a verdict.

WHAT A PASS DOES NOT PROVE, written here because a pass will feel like proof. It
means the words exist in his record. It cannot see whether they say what the
claim says: a real sentence of his attached to an unrelated claim passes. The
review of this check reads its passes by hand for that reason.

THE LEAKS, named by the game-walk before this was written. A label of mine on
every attribution clears it, and the review measures the label rate. A claim
phrased outside the narrow grammar is never examined; if this fires too rarely,
widen the trigger vocabulary and never deepen the claim grammar, which is what the
state-claim check next to it learned.

It reads the REPLY only. The same claim in a memory entry or a file header is a
second stage, owed and named, not done.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from divineos.core.operating_loop._use_vs_mention import (
    match_is_meta_framed,
    strip_quoted_spans,
)

GATE_NAME = "his-said-needs-his-sentence"

#: A quoted span shorter than this is a scare quote around a word, not a quotation.
MIN_QUOTE_WORDS = 4
#: Each stretch of a quote between ellipses must be at least this long to be checked.
MIN_FRAGMENT_WORDS = 3

_CODE_SPAN = re.compile(r"`[^`]*`|\bdivineos\s+\w[\w-]*")
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_QUOTED_LINE = re.compile(r"^\s*(?:>|\*|_)")
_ASKS = re.compile(r"\?\s*$")

# Me attributing a saying or a want to him. The list of shapes that have fired, not
# a theory of how I might phrase it.
_ATTRIBUTION = re.compile(
    r"\b(?:Dad|Andrew|he)\s+(?:said|told me|asked(?: me)?(?: for| to)?|wants?|wanted|"
    r"does(?: not|n't) want|did(?: not|n't) want|hates?|likes?|prefers?|expects?|"
    r"insisted|demanded|ruled|taught me|corrected me)\b"
    r"|\byou\s+(?:said|told me|asked(?: me)?(?: for| to)?|wanted|want|taught me|"
    r"corrected me|ruled|prefer|expect|(?:do not|don't) want)\b"
    r"|\bhis\s+(?:rule|ask|instruction|ruling)\s+(?:is|was)\b",
    re.IGNORECASE,
)

# Retractions and negations: saying I cannot show he said it is the cure.
_NEGATED = re.compile(
    r"\b(?:never|did not say|didn't say|not say|can't show|cannot show|can't find|"
    r"cannot find|couldn't find|could not find|no words of his|no record)\b",
    re.IGNORECASE,
)

# My own label that this is inference, not his sentence.
_MY_GUESS = re.compile(
    r"\b(?:my guess|my inference|my read|i(?:'m| am) guessing|i(?:'m| am) assuming|"
    r"i infer(?:red)?|i assumed|i guess|as i read it|i think (?:he|you|dad))\b",
    re.IGNORECASE,
)

# Me, reporting a claim I already made and got wrong. Describing the fault is not
# committing it: the first live reply through a new gate is nearly always about
# the gate. THE POSITION IS LOAD-BEARING, the frame must sit immediately BEFORE the
# attribution, the way the state check draws it. The hole this leaves is the same
# one that check names: a live fabrication dressed as a confession walks through,
# because intent is not in the string.
_MY_OWN_PAST_CLAIM = re.compile(
    r"\bI\s+(?:told|said|wrote|claimed|assumed|reported|decided|inferred|read|handed)\b"
    r"(?:\s+\w+){0,3}\s+(?:that\s+)?$",
    re.IGNORECASE,
)

_QUOTED_SPAN = re.compile(r'"([^"]+)"|“([^”]+)”')
_ELLIPSIS = re.compile(r"\.{2,}|…|\[\.\.\.\]")
_NOT_WORD = re.compile(r"[^a-z0-9']+")
_SEP = "\x00"

_REMEDY = (
    "  SCOPE: do NOT recompose -- he has read it. In the next reply put his exact\n"
    "  words next to the claim, or say plainly that it is my guess."
)


def _norm(text: str) -> str:
    """Lowercase words only, so his '..' pauses and my quote marks cannot decide it."""
    text = (text or "").lower().replace("’", "'").replace("‘", "'")
    return " ".join(w for w in _NOT_WORD.split(text) if w)


def _word_count(text: str) -> int:
    return len(_norm(text).split())


def load_record(corpus: Path | None = None, recent: str | None = None) -> str | None:
    """Everything he wrote, as one searchable string of words. None = could not read.

    His own cleaner decides what counts as his typing, so my pasted-back text and a
    test's fixture sentence never stand in for him. ``recent`` is his latest messages
    straight from the transcript, because the shared record is filled as he speaks
    and may not hold the message he just sent.
    """
    from divineos.core import his_words_door
    from divineos.core.his_words_corpus import his_passages

    path = corpus or his_words_door.CORPUS
    rows: list[dict] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return None
    messages = [_norm(str(r.get("text", ""))) for r in his_passages(rows)]
    if recent:
        messages.append(_norm(recent))
    messages = [m for m in messages if m]
    if not messages:
        return None  # both-empty: an empty record and an unreadable one give the checker the same answer, could-not-look, and an empty zero from his record is never an observation
    return _SEP.join(messages)


def _in_record(span: str, record: str) -> bool:
    """Every stretch of the span, between ellipses, appears inside his words."""
    for fragment in _ELLIPSIS.split(span):
        norm = _norm(fragment)
        if len(norm.split()) < MIN_FRAGMENT_WORDS:
            continue
        if norm not in record:
            return False
    return True


def _real_quotes(window: str) -> list[str]:
    spans = [a or b for a, b in _QUOTED_SPAN.findall(window)]
    return [s for s in spans if _word_count(s) >= MIN_QUOTE_WORDS]


def attributions(text: str) -> list[tuple[str, str]]:
    """Sentences where I attribute a saying or a want to him, with the window that
    could carry the quote: this sentence and the next."""
    parts = [p.strip() for p in _SPLIT.split(text or "") if p.strip()]
    out: list[tuple[str, str]] = []
    for i, sentence in enumerate(parts):
        if len(sentence) < 12 or _QUOTED_LINE.match(sentence) or _ASKS.search(sentence):
            continue
        scan = _CODE_SPAN.sub(lambda m: " " * len(m.group()), strip_quoted_spans(sentence))
        match = _ATTRIBUTION.search(scan)
        if match is None or _NEGATED.search(scan):
            continue
        if match_is_meta_framed(scan, match.start()):
            continue
        if _MY_OWN_PAST_CLAIM.search(scan[: match.start()]):
            continue
        before = parts[i - 1] if i else ""
        after = parts[i + 1] if i + 1 < len(parts) else ""
        if _MY_GUESS.search(sentence) or _MY_GUESS.search(before):
            continue
        out.append((sentence.lstrip("#*-— ").strip(), sentence + " " + after))
    return out


def check(text: str, record: str | None) -> str | None:
    """None when every attribution is backed, labelled, or negated."""
    found = attributions(text)
    if not found:
        return None

    if record is None:
        shown = "\n".join(f"    {s}" for s, _ in found[:3])
        return (
            "I SAID WHAT HE SAID OR WANTS, AND COULD NOT READ HIS RECORD TO CHECK:\n"
            f"{shown}\n"
            "  This is not a finding that the claims are wrong. His words could not be\n"
            "  read this turn, so nothing was checked.\n"
            f"{_REMEDY}"
        )

    invented: list[tuple[str, str]] = []
    unlinked: list[str] = []
    for sentence, window in found:
        quotes = _real_quotes(window)
        if not quotes:
            unlinked.append(sentence)
            continue
        for q in quotes:
            if not _in_record(q, record):
                invented.append((sentence, q))
                break

    if not invented and not unlinked:
        return None

    lines = ["I TOLD HIM WHAT HE SAID OR WANTS, WITHOUT HIS SENTENCE BESIDE IT:"]
    for sentence, quote in invented[:3]:
        lines.append(f"    {sentence}")
        lines.append(f'      the words "{quote[:90]}" are nowhere in anything he has written.')
    for sentence in unlinked[: max(0, 3 - len(invented))]:
        lines.append(f"    {sentence}")
    lines += [
        "  His rule, 2026-10-07: 'then its highly likely i didnt say it and it was just",
        "  inferred from what i said or a decision was made off what i said'. A name on a",
        "  file and a line that says he asked are not his sentence. Quote him, four words",
        "  or more, exactly; or say it is my guess.",
        _REMEDY,
    ]
    return "\n".join(lines)
