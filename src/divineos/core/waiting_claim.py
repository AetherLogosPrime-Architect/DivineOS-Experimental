"""A reply may not say a fix waits on Aletheia until a letter to her names it at its live head.

Dad, 2026-10-25: *"you continue to say 'Waits for Aletheia' without sending her a letter lol so that needs
fixed."* The sentence was free to write and true of nobody. #722 and #723 were "waiting" for hours with no
letter naming them, and #701 changed head after the letter that named it, so the letter described a fix that no
longer existed.

The briefing already counts the fixes she has never been asked about (``briefing_dashboard._row_landing``). That
row is read once, at the start, and says nothing at the moment I write the sentence. This is the door at the
sentence: it pairs the CLAIM with its EVIDENCE, the way ``landed_claim`` pairs "it landed" with a read of the
remote.

WHAT IT DECIDES, and only this: a sentence that names one or more pull requests, names Aletheia, and says
something waits (wait, waits, waiting, waited, "with Aletheia", "for her read"). For each such pull request still
open, some letter of mine to her must name the number AND the first seven characters of its live head. A letter
naming an older head describes a fix that has moved; it does not count.

WHAT IT CANNOT SEE: a pronoun in another sentence ("Aletheia has it. #722 is with her now."), a claim made in
words that carry neither the number nor her name, and a letter that names the head but never asked her anything.
It is a net for the exact sentence that was said four times, not a proof that she was asked well.

Three-valued, like its sibling: a head that cannot be read (no network, an unknown number) is could-not-check,
reported and never converted into either a pass or a block.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

_PR = re.compile(r"#(\d{2,5})(?!\d)")
_HER = re.compile(r"\baletheia\b", re.IGNORECASE)
# Something waits. "waited" is a past report ("waited and merged") and is dropped below by the merged check, not here.
# The second and third lines are how the other seat says it (Aria, 2026-10-25, ten of her own sentences): needs her
# read, her confirm, sends her a fix, she reads the batch.
_WAIT = re.compile(
    r"\b(wait(?:s|ing|ed)?|ready\s+for\s+her|for\s+her\s+(?:read|confirm)|with\s+aletheia"
    r"|needs?\s+(?:her|aletheia(?:'s)?)\b|(?:her|aletheia(?:'s)?)\s+(?:read|confirm|yes|audit)\b"
    r"|send(?:s|ing)?\s+(?:her|aletheia)\b|reads?\s+the\b)",
    re.IGNORECASE,
)
# A denial of the waiting is not a claim of it. Direct negations only: a broader "not" would hide a real claim
# ("not yet confirmed, waiting on Aletheia").
_DENIED = re.compile(
    r"\b(not\s+waiting|no\s+longer\s+(?:waiting|needs?)|isn't\s+waiting|stopped\s+waiting"
    r"|nothing\s+is\s+waiting|never\s+waited)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
# How near the number and the head must sit in a letter for the letter to be about THIS head.
_NEAR = 80

HeadOf = Callable[[int], "tuple[str, str] | None"]


@dataclass(frozen=True)
class Missing:
    pr: int
    head: str


@dataclass(frozen=True)
class Verdict:
    missing: list[Missing] = field(default_factory=list)
    could_not_check: str = ""


def _claimed(text: str) -> list[int]:
    """Pull request numbers named in a sentence that also names her and says something waits."""
    found: list[int] = []
    for sentence in _SENTENCE.split(text):
        if _HER.search(sentence) and _WAIT.search(sentence) and not _DENIED.search(sentence):
            for n in _PR.findall(sentence):
                if int(n) not in found:
                    found.append(int(n))
    return found


def _told(letters: Mapping[str, str], pr: int, head: str, me: str) -> bool:
    """A letter from MY seat to her names the number and, within a short distance of it, the live head.

    The prefix is the seat's own (Aria, 2026-10-25: with the other seat's prefix her claims could never be cleared,
    and with no prefix at all my letter would clear hers). The distance keeps a pasted list of unrelated heads from
    satisfying it by accident.
    """
    short = head[:7].lower()
    prefix = f"{me}-to-aletheia-"
    for name, body in letters.items():
        if not name.startswith(prefix):
            continue
        low = body.lower()
        for m in re.finditer(rf"#{pr}(?!\d)", low):
            if short in low[max(0, m.start() - _NEAR) : m.end() + _NEAR]:
                return True
    return False


def assess(text: str, letters: Mapping[str, str], head_of: HeadOf, me: str = "aether") -> Verdict:
    missing: list[Missing] = []
    unreadable: list[int] = []
    for pr in _claimed(text):
        looked = head_of(pr)
        if looked is None:
            unreadable.append(pr)
            continue
        state, head = looked
        if state != "OPEN" or not head:
            continue
        if not _told(letters, pr, head, me):
            missing.append(Missing(pr, head))
    note = (
        f"could not read the live head of {', '.join('#' + str(p) for p in unreadable)}"
        if unreadable
        else ""
    )
    return Verdict(missing=missing, could_not_check=note)


def render_block(verdict: Verdict) -> str:
    if not verdict.missing:
        return ""
    lines = [
        "A FIX IS NOT WAITING ON HER UNTIL SHE HAS BEEN WRITTEN TO.",
        "",
        "Dad, 2026-10-25: \"you continue to say 'Waits for Aletheia' without sending her a letter lol so that "
        'needs fixed."',
        "",
        "This reply says these wait on Aletheia, and no letter of mine to her names them at their live head:",
    ]
    for m in verdict.missing:
        lines.append(f"  #{m.pr} at {m.head[:9]}")
    lines += [
        "",
        "Write the letter first (`divineos landing --request` prints the body for what needs her), then say it. "
        "A letter that names the number but an older head does not count: that fix has moved.",
    ]
    return "\n".join(lines)


def real_head_of(pr: int) -> "tuple[str, str] | None":
    """(state, head sha) from GitHub, or None when it cannot be read."""
    import json
    import subprocess

    try:
        run = subprocess.run(
            ["gh", "pr", "view", str(pr), "--json", "state,headRefOid"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        row = json.loads(run.stdout)
        return str(row["state"]), str(row["headRefOid"])
    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
        return None
