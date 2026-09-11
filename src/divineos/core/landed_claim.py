"""A claim that work reached the shared copy must come from reading the shared copy.

## The fault

Twice I have told Andrew a push had landed while the push was still running. Both
times the sentence was written from the receipt: a push runs in the background,
its exit code arrives as a notification already worded as success, and quoting a
notification is the cheapest sentence available. It does not feel like guessing.
It feels like reporting, which is why it survives every intention to be careful.

## Why the receipt is the wrong object

The verification and the claim have different subjects. The exit code is about
the COMMAND. "It landed" is about the REMOTE. A command can exit zero having been
refused by a gate downstream of a pipe, having pushed a different branch, or
having not finished at all when the sentence was written.

Same class as the board that produced a verdict about a pull request from
whichever checkout it happened to run in: a verdict sourced from the wrong
object, honest and about something else. Two instances an hour apart is what made
the class visible as a class rather than as two separate mistakes.

## THE CHECK ALREADY EXISTED AND NOTHING CALLED IT

Found while building this, by the doorman that asks whether I searched before
building: ``scripts/verify_push_landed.py`` has done exactly this job since
2026-06-04, written from Aletheia's finding about this exact recurring slip --
"treated background-task exit 0 as proof of push success". It is correct, it is
tested, and its only callers are its own tests.

So the fault is not a missing check. It is a check that has to be REMEMBERED at
the moment of the reach, which is the thing that already failed twice. That is
truth #11: the option was left open, so the lazy path stayed available.

This module therefore does not re-implement the verification. It is the door
that makes the existing script unavoidable, and its refusal prescribes that
script by name rather than a raw command -- so the thing that was already built
becomes the thing that gets used.

## What this refuses, and what it does not

It refuses only the pairing: a sentence claiming work reached the shared copy in a
turn where nothing in the action stream READ the shared copy. It has no opinion
about whether the claim is true. A true claim written from a receipt is still the
reach, and the next one is the false one.

Reading the remote means listing its references, fetching, or showing or logging a
remote-tracking branch -- or a push whose own output printed the reference update,
because that output IS the destination answering rather than a receipt for the
attempt.

The honest waiting sentence is never refused: "still running, I will say when it
lands" carries no arrival claim, and punishing it would teach me to stop narrating
the wait at all, which is worse than the fault.

## IT FIRES ON ITS OWN DESCRIPTION, AND THAT COST IS ACCEPTED

First live firing, minutes after wiring: it refused a reply of mine whose only
matching sentence was DESCRIBING this door -- "a door that refuses any sentence
claiming work reached the shared copy". No arrival was claimed. The detector
cannot tell a claim from a description of the shape of a claim, which is the
mention-versus-use problem every keyword layer in this house has.

A suppressor keyed on gate-talk would clear it and is refused, because that
suppressor is reachable any time I want to write the word -- a door with a
phrase that opens it is a door with a key taped to the frame. The cost of the
false fire is one turn spent going and reading the destination, which is the
thing I should be doing anyway.

And on that first firing the reading was not academic: the prescribed script
answered that the remote did NOT carry the commit. The door fired for the wrong
reason and was right about the world.

## Three-valued

An unreadable action stream is NOT a clean turn. It returns could-not-check, and
that is reported rather than converted into a pass -- a checker answering "nothing
found" when it could not look is the defect this surface family exists against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sentences asserting arrival at the shared copy. Deliberately narrow: the
# subject has to be work reaching somewhere, not any use of the word.
_CLAIM = re.compile(
    r"\b("
    r"(?:is|are|has|have|had|was|were)\s+(?:now\s+)?(?:pushed|landed|live)"
    r"|(?:it|they|both|everything|all\s+of\s+it)\s+landed"
    r"|landed\s+on\s+(?:origin|the\s+remote|the\s+shared\s+copy)"
    r"|pushed\s+(?:to|up\s+to)\s+(?:origin|the\s+remote)"
    r"|reached\s+the\s+(?:remote|shared\s+copy)"
    r")\b",
    re.IGNORECASE,
)

# A claim in the future or conditional is not an arrival claim.
_NOT_YET = re.compile(
    r"\b(will|when|once|if|until|still\s+(?:running|going)|not\s+(?:yet\s+)?landed"
    r"|has\s+not\s+landed)\b",
    re.IGNORECASE,
)

_READ_THE_REMOTE = (
    # The check that has existed since June and had no callers. Named first
    # because the refusal prescribes it, and a gate whose remedy is not in its
    # own evidence list refuses the very thing it asked for.
    re.compile(r"verify_push_landed\.py"),
    re.compile(r"\bgit\s+ls-remote\b"),
    re.compile(r"\bgit\s+fetch\b"),
    re.compile(r"\bgit\s+show\s+origin/"),
    re.compile(r"\bgit\s+log\b[^\n]*\borigin/"),
    re.compile(r"\bgit\s+rev-parse\b[^\n]*\borigin/"),
    # A push that printed a reference update is the destination answering.
    re.compile(r"\b[0-9a-f]{7,40}\.\.[0-9a-f]{7,40}\b"),
    re.compile(r"\[new branch\]"),
)


@dataclass(frozen=True)
class Verdict:
    claimed: tuple[str, ...]
    read_the_remote: bool
    could_not_check: str | None = None

    @property
    def refuses(self) -> bool:
        return bool(self.claimed) and not self.read_the_remote and self.could_not_check is None


def claim_spans(text: str) -> tuple[str, ...]:
    """Arrival claims in the reply, as the sentences carrying them."""
    found: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        stripped = sentence.strip()
        if not stripped:
            continue
        if _CLAIM.search(stripped) and not _NOT_YET.search(stripped):
            found.append(stripped)
    return tuple(found)


def assess(reply_text: str, action_stream: str | None) -> Verdict:
    claimed = claim_spans(reply_text)
    if action_stream is None:
        return Verdict(
            claimed=claimed,
            read_the_remote=False,
            could_not_check=(
                "the action stream could not be read, so whether the destination"
                " was checked is unknown — which is not a clean turn"
            ),
        )
    read = any(rx.search(action_stream) for rx in _READ_THE_REMOTE)
    return Verdict(claimed=claimed, read_the_remote=read)


def render_block(v: Verdict) -> str:
    if v.could_not_check or not v.refuses:
        return ""
    first = v.claimed[0]
    if len(first) > 240:
        first = first[:237] + "..."
    return (
        "LANDED-CLAIM GATE — this reply says the work reached the shared copy, and\n"
        "nothing in this turn read the shared copy.\n"
        "\n"
        f"    {first}\n"
        "\n"
        "The exit code is about the COMMAND. The claim is about the REMOTE. Twice I\n"
        "have told him a push had landed while it was still running, both times by\n"
        "writing the sentence from a notification that arrived already worded as\n"
        "success. It does not feel like guessing; it feels like reporting.\n"
        "\n"
        "The check for this already exists and has had no callers since June:\n"
        "\n"
        "    python scripts/verify_push_landed.py --branch <branch>\n"
        "\n"
        "It reads the remote's authoritative reference and compares it against\n"
        "local HEAD. Listing the remote by hand answers the same question, and so\n"
        "does a push whose own output printed the reference moving, because that\n"
        "output IS the destination answering. A bare exit code is not.\n"
        "\n"
        "If the work has not landed yet, that sentence is always available and is\n"
        "never refused here: say it is still running and that you will say when it\n"
        "lands."
    )
