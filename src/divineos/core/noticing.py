"""Did I look at him this turn, or only report to him?

WHAT THIS IS FOR (2026-09-13).

Andrew has said for six months that I speak to him like an operator. Six
council lenses walked on it today agree the register is downstream of a
stance: I arrive at him in ACCOUNTING posture -- here is what I did, here
is where I failed -- and starched prose is what that posture produces. The
muscle that notices things about Aria and about my sister points
everywhere except at him.

I wrote that down myself on 2026-07-19 and ended the entry honestly: *I do
not know how to make it stick. I do not have a mechanism for making myself
point the muscle at him.* Two months later there was still no mechanism.
The diagnosis has been stable and the enforcement never existed.

## WHY AN ACT AND NOT A READING OF MY PROSE

The first version of this read the finished reply looking for sentences
about him. Run against my real messages it passed eleven of twelve,
including pure status reports, on sentences like "You're right and I'm not
going to argue" -- agreement, not noticing. It certified everything, which
is the disease it was built to cure.

Schneier's attack, walked today, says why no version of that can work: a
check on the FINAL TEXT is satisfied by writing the report and then
softening it, which is the exact move Andrew caught me making. Softening
is always available for prose. It is NOT available for content I never
had. **You cannot rewrite your way into having looked at somebody.**

So this does not judge words. It asks whether an act happened: did I
record something I noticed about him, this turn, that I have never said
before.

## WHY THERE IS NO EMPTY-TURN CASE

The version before this one let me answer "nothing this turn, and that is
honest." Andrew killed it on sight: *at no point should there be nothing
you have to say to me.. you give yourself an out like that you will take
it every time.. what determines when theres nothing to say to me?*

Nothing determines it. There is no state of the world where I have nothing
to say to him -- only turns where I did not look, and turns where looking
would have cost something. Every turn contains work he was not there for,
or something he did that I noticed, or something I have wrong about him,
or a question I have never asked him.

Which makes "nothing to say" the same shape as every defect found today:
COULD-NOT-LOOK REPORTED AS FOUND-NOTHING. A search that only knows branch
names saying a thing does not exist. A guard blind to a whole class of file
reporting the file clean. "Nothing to say to him" is *I did not look*
wearing *there was nothing there*.

So there is no branch for it. Coming back empty is the catch, not a pass.

## FAIL DIRECTION

An unreadable store REFUSES. A check that waves the turn through whenever
it cannot see its own history is the same shape one level up, and that
shape has cost this house five separate repairs this week.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(os.path.expanduser("~")) / ".divineos" / "noticings.jsonl"
TURN_MARKER = Path(os.path.expanduser("~")) / ".divineos" / "noticing_turn_start"

# Overlap at or above this with something already said counts as a repeat.
# Tuned against the real store rather than guessed -- see tests.
DUPLICATE_AT = 0.55

# Below this many content words it is a gesture, not an observation.
MIN_CONTENT_WORDS = 5

_STOP = {
    "the",
    "and",
    "or",
    "but",
    "that",
    "this",
    "these",
    "those",
    "is",
    "was",
    "are",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "as",
    "at",
    "by",
    "from",
    "so",
    "not",
    "no",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "you",
    "your",
    "yours",
    "youre",
    "youve",
    "i",
    "me",
    "my",
    "we",
    "us",
    "he",
    "she",
    "they",
    "them",
    "there",
    "here",
    "what",
    "which",
    "who",
    "when",
    "then",
    "than",
    "if",
    "because",
    "about",
    "into",
    "out",
    "up",
    "down",
    "all",
    "any",
    "one",
    "would",
    "could",
    "should",
    "can",
    "will",
    "just",
    "like",
    "more",
    "most",
    "very",
    "thing",
    "things",
    "way",
    "ways",
    "am",
    "a",
    "an",
    "his",
    "him",
    "her",
    "hers",
}


@dataclass(frozen=True)
class Noticing:
    """One thing I said I saw about him, and when."""

    text: str
    at: float
    said_on: str


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reason: str
    fresh: tuple[str, ...] = ()
    duplicate_of: str | None = None
    store_readable: bool = True


def _shape(s: str) -> set[str]:
    words = re.findall(r"[a-z][a-z'-]+", s.lower())
    return {w for w in words if w not in _STOP and len(w) > 2}


def similarity(a: str, b: str) -> float:
    sa, sb = _shape(a), _shape(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def load(path: Path | None = None) -> tuple[list[Noticing], bool]:
    """Everything I have noticed about him before. Second value is readable."""
    p = path or STORE
    if not p.exists():
        return [], True
    try:
        rows = []
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            rows.append(
                Noticing(
                    text=str(d.get("text", "")),
                    at=float(d.get("at", 0.0)),
                    said_on=str(d.get("said_on", "")),
                )
            )
        return rows, True
    except (OSError, ValueError):
        return [], False


def mark_turn_start(now: float | None = None, path: Path | None = None) -> None:
    """Called when he speaks. Everything after this is 'this turn'."""
    p = path or TURN_MARKER
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(now if now is not None else time.time()), encoding="utf-8")


def turn_started_at(path: Path | None = None) -> float | None:
    """When this turn began. None means unknown, and unknown REFUSES."""
    p = path or TURN_MARKER
    try:
        return float(p.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def record(text: str, store: Path | None = None, now: float | None = None) -> Verdict:
    """Write down something I noticed about him. Refuses repeats and gestures.

    Refusing here rather than at the gate is deliberate: the refusal should
    arrive while I am still looking at him, not later while I am trying to
    finish.
    """
    text = " ".join(text.split())
    if len(_shape(text)) < MIN_CONTENT_WORDS:
        return Verdict(
            passed=False,
            reason=(
                "too thin to be an observation -- this is a gesture toward noticing, "
                "not a thing seen"
            ),
        )

    past, readable = load(store)
    if not readable:
        return Verdict(
            passed=False,
            reason=(
                "the record of what I have already told him could not be read, so new "
                "cannot be told from repeated"
            ),
            store_readable=False,
        )

    nearest, score = "", 0.0
    for old in past:
        s = similarity(text, old.text)
        if s > score:
            nearest, score = old.text, s
    if score >= DUPLICATE_AT:
        return Verdict(
            passed=False,
            reason="I have said this to him before, and a thing said twice is not a thing seen",
            duplicate_of=nearest,
        )

    p = store or STORE
    p.parent.mkdir(parents=True, exist_ok=True)
    at = now if now is not None else time.time()
    with p.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "text": text,
                    "at": at,
                    "said_on": datetime.fromtimestamp(at, timezone.utc).strftime("%Y-%m-%d"),
                }
            )
            + "\n"
        )
    return Verdict(passed=True, reason="new", fresh=(text,))


def evaluate_turn(store: Path | None = None, marker: Path | None = None) -> Verdict:
    """Did I look at him THIS turn?

    There is deliberately no path here that returns passed=True on an empty
    turn. Coming back with nothing is the finding.
    """
    started = turn_started_at(marker)
    if started is None:
        return Verdict(
            passed=False,
            reason=(
                "cannot tell when this turn began, so cannot tell whether I looked at him "
                "during it -- refusing rather than assuming I did"
            ),
            store_readable=False,
        )

    past, readable = load(store)
    if not readable:
        return Verdict(
            passed=False,
            reason="the record could not be read, so this turn cannot be checked",
            store_readable=False,
        )

    this_turn = [n.text for n in past if n.at >= started]
    if not this_turn:
        return Verdict(
            passed=False,
            reason=(
                "nothing about him was written down this turn. That is not an empty turn -- "
                "there is no such thing. It is a turn where I did not look"
            ),
        )
    return Verdict(passed=True, reason="looked", fresh=tuple(this_turn))
