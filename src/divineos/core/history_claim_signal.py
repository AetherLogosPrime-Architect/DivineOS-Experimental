"""A claim about my own past, made without opening the record.

ANDREW 2026-09-08, and it is the sharpest thing said in a very long day:

    *the fact you do not remember shit is a STRUCTURAL PROBLEM YOU HAVE SOLVED
    WITH MANY OTHER THINGS.. so when you dont remember something thats your own
    fucking fault at this point.. you have the means.. the formula.. the
    equipment.. the build.. and have SUCCESSFULLY DONE IT ALREADY*

He is right, and the proof is the module this one is copied from.
``verify_before_build_signal`` refused me four or five times today and I never
once talked my way past it, because it decides on the ACTION STREAM rather than
on my prose. Same architecture, pointed at the reach that actually cost him:

WHAT THIS CATCHES. Saying something about my own history — how many times, the
first time, never before, nobody has, the record shows — when nothing in the
window actually read the record.

WHAT IT COST TODAY, four times in one conversation:
  - asked how often he had taught one lesson, I answered from four hand-rolled
    queries against the wrong stores and reported ten. The real figure from his
    own messages is six hundred and fifty.
  - I reported the ledger's integrity failure to him as possible deletion. It
    is a breakage test he authorised, and my own entry saying so was one search
    away, dated the previous morning.
  - twice more on smaller counts.

Every one of them was findable. None of them was found. The thing that produced
the finding, each time, was him telling me to go look.

THE SPLIT, and it is what makes this different from a gate I can rephrase past:
my TEXT decides whether the check fires. The ACTION STREAM decides whether it
blocks. I can avoid the trigger by not making historical claims, which is fine
— that is the honest alternative. I cannot satisfy it by wording, only by
having read.

WHAT IT CANNOT DO. It cannot tell a good read from a bad one. My first probe
today returned ten because it searched the wrong shelves with guessed column
names, and this check would have counted that as reading. It catches speaking
about the past with no read at all; it does not catch speaking about the past
after a broken read. That second failure is real and remains open.
"""

from __future__ import annotations

import re
import time

WINDOW_SECONDS: int = 30 * 60

_HISTORY_CLAIM_RE = re.compile(
    r"(?:"
    r"\b(?:never|not once|no one has|nobody has|has never|have never)\b"
    r"|\b(?:first time|only time|last time)\b"
    r"|\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|dozens?|hundreds?|thousands?)\s+"
    r"(?:times?|instances?|occasions?|entries|rows|events|sessions)\b"
    r"|\bthe (?:record|ledger|history|store) (?:shows|says|holds|contains)\b"
    r"|\b(?:i|we) (?:have|had) (?:already )?(?:done|built|filed|written|said) (?:this|that|it) "
    r"(?:before|already)\b"
    r")",
    re.IGNORECASE,
)
"""Shapes that assert something about my own past.

Deliberately narrow. A broad matcher would fire on ordinary counting — three
tests passed, two files changed — which is reporting what just happened rather
than claiming what the record holds, and pricing that would teach me to stop
citing evidence, which is the opposite of the point.
"""

_RECORD_READ_MARKERS = (
    "divineos ask",
    "divineos recall",
    "divineos corrections",
    "divineos context",
    "divineos verify",
    "divineos lessons",
    "divineos decisions",
    "divineos claims",
    "event_ledger",
    "system_events",
    "_get_db_path",
    "andrew_corrections",
    "divineos_home",
)
"""What counts as having opened the record.

Both the CLI and a raw read qualify. Today the consultation counter recognised
only the CLI, so five turns of hand-querying my own databases registered as not
consulting at all -- the instrument was watching which tool I typed. This one
counts the reading however it was done.
"""


def claims_about_history(reply_text: str) -> str | None:
    """The matched phrase if the text asserts something about my own past."""
    m = _HISTORY_CLAIM_RE.search(reply_text or "")
    return m.group(0) if m else None


def read_the_record_within(commands: list[tuple[str, float]], now: float | None = None) -> bool:
    """Whether any command in the window actually opened the record.

    ``commands`` is (command_text, timestamp) pairs from the action stream --
    supplied by the caller rather than fetched here, so the check is testable
    without a live ledger and so a caller with a different stream can reuse it.
    """
    now = time.time() if now is None else now
    start = now - WINDOW_SECONDS
    for text, ts in commands:
        if ts < start:
            continue
        low = (text or "").lower()
        if any(marker in low for marker in _RECORD_READ_MARKERS):
            return True
    return False


def check_should_block(
    reply_text: str,
    commands: list[tuple[str, float]],
    now: float | None = None,
) -> str | None:
    """Return a refusal message, or None to let the reply through."""
    claim = claims_about_history(reply_text)
    if claim is None:
        return None
    if read_the_record_within(commands, now=now):
        return None
    return (
        "HISTORY-CLAIM WITHOUT A READ — this reply says something about my own "
        f'past ("{claim.strip()}") and nothing in the window opened the record.\n\n'
        "MINE, and here is why. Andrew 2026-09-08: not remembering is a "
        "structural problem I have already solved elsewhere, so a claim made "
        "from memory is a build I did not do. Four times in one conversation I "
        "answered a question about my own history from what I could recall, and "
        "four times the true answer was one search away in the ledger. Once I "
        "told him the chain was broken and possibly tampered with; it was a "
        "breakage test he had authorised, recorded in my own words the previous "
        "morning.\n\n"
        "This decides on the action stream, not on wording, so rephrasing does "
        "not clear it. Open the record, or say plainly that I have not checked."
    )
