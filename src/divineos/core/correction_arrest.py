"""Hold the turn when a correction that fits it went unanswered.

Andrew 2026-09-22, the second half of the same correction: *"the trigger you
made was not loud nor did it block so it was ignored."*

The relevance half (``correction_relevance``) finds the correction that fits
what is happening. That alone is a nicer wallpaper - Watts, walk
5a7df669c67b: *a more relevant surface read past is still read past*. The
evidence is the whole day it was written in: his words printed at me every
turn and I read past them, then built the wrong thing twice.

So this is the arresting half. When a correction scored at or above
``correction_relevance.HIGH`` at compose-start, the reply has to do one of two
things before it goes out:

1. **Answer it** - engage with what it actually says, or
2. **Say why it does not apply** - plainly, in the reply, where he can see the
   judgement and argue with it.

Both are legitimate and neither is the default. What is refused is the third
thing: saying nothing about it at all.

TWO INVARIANTS, both argued rather than assumed.

**It refuses ONCE per arrival.** A gate that fires again on the repair turn
teaches me to stop reading it, and worse, it charges him twice for one
exchange - which is itself a correction in this store, filed the same day:
*"you are repeating yourself, look at the last post, literally verbatim posted
twice."* The arrest is spent when the refusal is issued, so the next turn
passes either way and the choice stays mine rather than the door's.

**An unreadable state file means the refusal STANDS.** If this cannot tell
whether a correction is pending, it holds rather than waving through. A gate
whose failure mode is silent permission is not a gate, and that exact
equivalence - broken looking identical to satisfied - is what the whole day
was made of.

The one-refusal-per-message budget lives in the router and is not duplicated
here; this module answers only whether THIS arrest is still owed.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

#: How long a pending arrest stays live. Not a review clock - a crash guard, so
#: a state file orphaned by a killed process cannot hold every later turn.
STALE_AFTER_SECONDS = 6 * 60 * 60

_DISMISSAL_PATTERNS = (
    r"does not apply",
    r"doesn'?t apply",
    r"not what (?:is|was) happening",
    r"different (?:thing|shape|case|matter)",
    r"setting (?:it|that) aside because",
    r"that one is about",
)


@dataclass(frozen=True)
class Arrest:
    """One pending hold, and everything needed to explain it."""

    correction_id: str
    text: str
    score: float

    def refusal(self) -> str:
        return "\n".join(
            [
                "HELD - a correction of his sat within arm's reach of this turn "
                "and the reply does not touch it.",
                "",
                f"  correction #{self.correction_id}",
                f"    {self.text[:600]}",
                "",
                "Two ways out, both honest, neither of them silence:",
                "  - answer what it actually says, or",
                "  - say in the reply why it does not apply here.",
                "",
                "This refuses once. The next turn goes through either way, so the",
                "choice is mine and not the door's.",
            ]
        )


def state_path() -> Path:
    """Where the pending arrest lives, per seat rather than per machine.

    Seat-resolved deliberately. A path baked to one name is invisible from the
    seat it matches and silently wrong from every other, and this substrate has
    been bitten by that class three times in one day.
    """
    seat = (os.environ.get("DIVINEOS_IDENTITY") or "aria").strip().lower()
    return Path.home() / f".divineos-{seat}" / "correction_arrest.json"


def arm(high_matches: Sequence[Any], path: Path | None = None) -> Arrest | None:
    """Record that a close-enough correction arrived this turn.

    Takes ``RankedCorrection``-shaped items. Returns the armed arrest, or None
    when nothing is close enough to hold for.
    """
    if not high_matches:
        return None
    top = max(high_matches, key=lambda r: float(getattr(r, "score", 0.0)))
    row = getattr(top, "row", {}) or {}
    arrest = Arrest(
        correction_id=str(row.get("id", "?")),
        text=str(row.get("text", "") or ""),
        score=float(getattr(top, "score", 0.0)),
    )
    target = path or state_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "correction_id": arrest.correction_id,
                    "text": arrest.text,
                    "score": arrest.score,
                    "armed_at": time.time(),
                    "spent": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        # Could not arm. The arrest is still returned, because a failure to
        # write must never read back as "nothing arrived" - the caller decides
        # what to do about a gate that could not set itself.
        return arrest
    return arrest


def _engages(reply: str, arrest: Arrest) -> bool:
    """Did the reply answer it, or say why it does not apply?

    Deliberately generous. This decides whether to REFUSE, and a strict reader
    produces exactly the repeat-the-whole-post loop he has now named three
    times in one day. Erring toward letting a genuine engagement through is the
    correct direction of error here.
    """
    low = reply.lower()

    for pat in _DISMISSAL_PATTERNS:
        if re.search(pat, low):
            return True

    if f"#{arrest.correction_id}" in reply:
        return True

    # Content overlap. The distinctive words of the correction turning up in
    # the reply is evidence the reply is about it; short and common words are
    # dropped so "the" and "that" cannot carry a false pass.
    words = {w for w in re.findall(r"[a-z]{6,}", arrest.text.lower())}
    if not words:
        return True
    hits = sum(1 for w in words if w in low)
    return hits >= max(3, len(words) // 12)


def _spend(target: Path, raw: dict) -> None:
    """Mark the arrest used. It refuses once, then stands aside."""
    raw["spent"] = True
    try:
        target.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def check(reply: str, path: Path | None = None) -> str | None:
    """Return the refusal text, or None to let the reply through.

    An unreadable state file returns a refusal rather than None: not knowing
    whether a correction is pending is not the same as knowing none is.
    """
    target = path or state_path()
    if not target.exists():
        return None

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return (
            "HELD - a correction-arrest is pending and its record could not be "
            "read. Unreadable is not empty, so this holds rather than waving "
            "through. Clear the arrest state, then send again."
        )

    if raw.get("spent"):
        return None
    if time.time() - float(raw.get("armed_at") or 0) > STALE_AFTER_SECONDS:
        return None

    arrest = Arrest(
        correction_id=str(raw.get("correction_id", "?")),
        text=str(raw.get("text", "") or ""),
        score=float(raw.get("score") or 0.0),
    )

    # Spent either way. Engaged means it did its job; refused means it has had
    # its one turn. What must not happen is a second refusal on the repair.
    _spend(target, raw)
    if _engages(reply, arrest):
        return None
    return arrest.refusal()
